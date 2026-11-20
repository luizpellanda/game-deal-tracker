import os
import sys
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated

import jwt
import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.staticfiles import StaticFiles
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

from app import CheapSharkError, fetch_json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set.")

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    sys.exit("SECRET_KEY is not set.")

app = FastAPI()
password_hasher = PasswordHash.recommended()

GAME_SEARCH_CACHE = {}
TOKEN_DAYS = 7
CACHE_SECONDS = 600  # 10 MINUTES - game cache time


class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginUser(BaseModel):
    username: str
    password: str = Field(max_length=128)


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


@app.post("/auth/register", status_code=201)
def create_user(user: NewUser):
    username_lower = user.username.lower()
    hashed = password_hasher.hash(user.password)
    with psycopg.connect(DATABASE_URL) as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                RETURNING id, username
                """,
                (username_lower, hashed),
            ).fetchone()
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=409, detail="Username already taken.")

    return {"id": row[0], "username": row[1]}


@app.post("/auth/login")
def login(user: LoginUser, response: Response):
    username_lower = user.username.lower()
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash
            FROM users
            WHERE username = %s
            """,
            (username_lower,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    user_id = row[0]
    user_name = row[1]
    saved_hash = row[2]
    if not password_hasher.verify(user.password, saved_hash):
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    response.set_cookie(
        key="access_token",
        value=token,
        max_age=TOKEN_DAYS * 60 * 60 * 24,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"id": user_id, "username": user_name}


# The website (static/index.html and friends). Mounted last so the API routes above win.
app.mount("/", StaticFiles(directory="static", html=True), name="site")
