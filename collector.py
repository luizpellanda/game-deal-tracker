import os
import sys
from datetime import datetime, timezone
from decimal import Decimal

import psycopg
from dotenv import load_dotenv

from app import CheapSharkError, fetch_json


def load_monitored_games(conn):
    """Return the games that are being monitored."""
    rows = conn.execute("SELECT id FROM games").fetchall()

    game_ids = []
    for row in rows:
        game_ids.append(row[0])
    return game_ids


def save_price(conn, game_id, deal, today):
    return conn.execute(
        """
        INSERT INTO price_history (game_id, store_id, sale_price, normal_price, recorded_on)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (game_id, store_id, recorded_on) DO NOTHING
        """,
        (
            int(game_id),
            int(deal["storeID"]),
            Decimal(deal["price"]),
            Decimal(deal["retailPrice"]),
            today,
        ),
    ).rowcount


def main():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        sys.exit("DATABASE_URL is not set.")

    today = datetime.now(timezone.utc).date()

    with psycopg.connect(database_url) as conn:
        games_loaded = load_monitored_games(conn)
        print(f"Games to collect: {len(games_loaded)}.")

    ids_text = ",".join(str(game_id) for game_id in games_loaded)

    try:
        games = fetch_json("games", {"ids": ids_text})
    except CheapSharkError as e:
        sys.exit(f"Collector stopped, no prices saved: {e}")
    print(f"Games received: {len(games)}.")

    saved = 0
    skipped = 0
    with psycopg.connect(database_url) as conn:
        for game_id, game in games.items():
            for deal in game["deals"]:
                inserted = save_price(conn, game_id, deal, today)
                if inserted == 1:
                    saved = saved + 1
                else:
                    skipped = skipped + 1
        row = conn.execute("SELECT COUNT(*) FROM price_history").fetchone()

    print(f"Saved: {saved}, skipped: {skipped}.")
    print(f"Rows in price_history: {row[0]}.")


if __name__ == "__main__":
    main()
