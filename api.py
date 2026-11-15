import os
import sys

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI

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
