import os
import sys
from decimal import Decimal
from typing import Annotated

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query

from app import CheapSharkError, fetch_json

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set.")

app = FastAPI()


@app.get("/games")
def get_games():
    with psycopg.connect(DATABASE_URL) as conn:
        rows = conn.execute("SELECT id, title FROM games ORDER BY title").fetchall()

    results = []
    for row in rows:
        results.append({"id": row[0], "title": row[1]})

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
    try:
        games = fetch_json("games", {"title": title, "limit": 10})
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

    return games_list
