import os
import sys

import psycopg
from dotenv import load_dotenv

from app import fetch_json


def load_monitored_games(conn):
    """Return the games that are being monitored."""
    rows = conn.execute(
        'SELECT id FROM games'
    ).fetchall()

    game_ids = []
    for row in rows:
        game_ids.append(row[0])
    return game_ids


def main():
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        sys.exit('DATABASE_URL is not set.')

    with psycopg.connect(database_url) as conn:
        games_loaded = load_monitored_games(conn)
        print(f'Games to collect: {len(games_loaded)}.')

    ids_text = ','.join(str(game_id) for game_id in games_loaded)
    games = fetch_json('games', {'ids': ids_text})
    print(f'Games received: {len(games)}.')

    for game_id, game in games.items():
        for deal in game['deals']:
            print(
                f"Game {game_id} / store {deal['storeID']} / "
                f"price {deal['price']} / normal {deal['retailPrice']}"
            )


if __name__ == '__main__':
    main()
