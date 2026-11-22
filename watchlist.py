"""Watchlist: the games each logged-in person follows, with an optional target price."""

from decimal import Decimal
from typing import Annotated

import psycopg
from fastapi import APIRouter, Cookie, HTTPException
from pydantic import BaseModel, Field

from app import CheapSharkError, fetch_json
from auth import get_current_user
from config import DATABASE_URL

router = APIRouter()

WATCHLIST_MAX_GAMES = 10  # per person
SYSTEM_MAX_GAMES = (
    100  # different games across all watchlists (keeps CheapShark calls small)
)


class NewWatchListItem(BaseModel):
    game_id: int = Field(gt=0)
    target_price: Decimal | None = Field(
        default=None,
        gt=0,
        le=1000,
        max_digits=10,
        decimal_places=2,
    )


@router.post("/watchlist", status_code=201)
def add_to_watchlist(
    body: NewWatchListItem, access_token: Annotated[str | None, Cookie()] = None
):
    user = get_current_user(access_token)
    user_id = user["id"]

    with psycopg.connect(DATABASE_URL) as conn:
        user_games = conn.execute(
            """
            SELECT COUNT(*)
            FROM watchlist
            WHERE user_id = %s
            """,
            (user_id,),
        ).fetchone()[0]

        if user_games >= WATCHLIST_MAX_GAMES:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Your watchlist is full (10 games). This is a free project that uses the CheapShark API, "
                    "so lists stay small to keep the daily price checks light. Remove a game to add another."
                ),
            )

        # Checks if game is already followed from another user
        followed = conn.execute(
            """
            SELECT 1
            FROM watchlist
            WHERE game_id = %s
            LIMIT 1
            """,
            (body.game_id,),
        ).fetchone()

        if followed is None:
            system_games = conn.execute(
                """
                SELECT COUNT(DISTINCT game_id)
                FROM watchlist
                """
            ).fetchone()[0]

            if system_games >= SYSTEM_MAX_GAMES:
                raise HTTPException(
                    status_code=409,
                    detail=(
                        "The tracker is full right now (100 games). It's a free project, so the number of games it checks every "
                        "day is capped. Try a game someone already follows."
                    ),
                )

        # Checks if the game is already known, and if we need to call CheapShark again
        game = conn.execute(
            """
            SELECT title
            FROM games
            WHERE id = %s
            """,
            (body.game_id,),
        ).fetchone()

    new_game = None
    if game is None:
        try:
            lookup = fetch_json("games", {"id": body.game_id})
        except CheapSharkError as e:
            if e.status_code == 404:
                raise HTTPException(
                    status_code=404, detail="Game not found on CheapShark."
                )
            raise HTTPException(
                status_code=502, detail="Could not reach CheapShark. Try again later."
            )
        new_game = lookup["info"]
        title = new_game["title"]
    else:
        title = game[0]

    with psycopg.connect(DATABASE_URL) as conn:
        # Saves the new game (checks if anyone added after the validations above)
        if new_game is not None:
            conn.execute(
                """
                INSERT INTO games (id, title, steam_app_id, thumb_url)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (
                    body.game_id,
                    new_game["title"],
                    new_game.get("steamAppID"),
                    new_game.get("thumb"),
                ),
            )

        # Adds it to the user's list
        try:
            conn.execute(
                """
                INSERT INTO watchlist (user_id, game_id, target_price)
                VALUES (%s, %s, %s)
                """,
                (user_id, body.game_id, body.target_price),
            )
        except psycopg.errors.UniqueViolation:
            raise HTTPException(
                status_code=409, detail="This game is already in your watchlist."
            )

    # Created
    return {
        "game_id": body.game_id,
        "title": title,
        "target_price": body.target_price,
    }
