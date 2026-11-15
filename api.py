import os
import sys
import time
from decimal import Decimal
from typing import Annotated

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles

from app import CheapSharkError, fetch_json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set.")

app = FastAPI()

GAME_SEARCH_CACHE = {}
CACHE_SECONDS = 600  # 10 MINUTES


@app.get("/games")
def get_games():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            """
            SELECT g.id,
                   g.title,
                   g.thumb_url,
                   MIN(p.sale_price) AS lowest_price,
                   MAX(p.normal_price) AS normal_price
            FROM games g
            LEFT JOIN price_history p
                   ON p.game_id = g.id
                  AND p.recorded_on = (SELECT MAX(recorded_on) FROM price_history)
            GROUP BY g.id, g.title, g.thumb_url
            ORDER BY g.title
            """
        ).fetchall()

    results = []
    for row in rows:
        if row[4]:
            discount_percent = round(100 - (row[3] / row[4] * 100))
        else:
            discount_percent = None

        results.append(
            {
                "id": row[0],
                "title": row[1],
                "thumb_url": row[2],
                "lowest_price": row[3],
                "normal_price": row[4],
                "discount_percent": discount_percent,
            }
        )

    return results


@app.get("/stats")
def get_stats():
    with psycopg.connect(DATABASE_URL) as conn:
        games_row = conn.execute(
            """
            SELECT COUNT(*) FROM games
            """
        ).fetchone()
        history_row = conn.execute(
            """
            SELECT COUNT(DISTINCT recorded_on), MIN(recorded_on), MAX(recorded_on)
            FROM price_history
            """
        ).fetchone()

    results = {
        "games_tracked": games_row[0],
        "days_collected": history_row[0],
        "first_day": history_row[1],
        "last_day": history_row[2],
    }
    return results


@app.get("/games/{game_id}/history")
def get_game_history(game_id: int):
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute(
            "SELECT recorded_on, store_id, sale_price, normal_price FROM price_history "
            "WHERE game_id = %s "
            "ORDER BY recorded_on, store_id",
            (game_id,),
        ).fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail="No deals for this game.")

    history = []
    for row in rows:
        history.append(
            {
                "recorded_on": row[0],
                "store_id": row[1],
                "sale_price": row[2],
                "normal_price": row[3],
            }
        )
    return history


@app.get("/games/search")
def search_games(title: Annotated[str, Query(min_length=2)]):
    key = title.strip().lower()
    saved = GAME_SEARCH_CACHE.get(key)
    if saved and time.monotonic() - saved[0] < CACHE_SECONDS:
        return saved[1]  # still fresh: answer from memory

    try:
        games = fetch_json("games", {"title": key, "limit": 10})
    except CheapSharkError as e:
        raise HTTPException(status_code=502, detail=str(e))

    games_list = []
    for game in games:
        games_list.append(
            {
                "id": int(game["gameID"]),
                "title": game["external"],
                "cheapest_price": Decimal(game["cheapest"]),
                "thumb_url": game["thumb"],
            }
        )
    GAME_SEARCH_CACHE[key] = (time.monotonic(), games_list)

    return games_list


# The website (static/index.html and friends). Mounted last so the API routes above win.
app.mount("/", StaticFiles(directory="static", html=True), name="site")
