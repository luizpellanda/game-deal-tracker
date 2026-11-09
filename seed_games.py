import os
import sys

import psycopg
from dotenv import load_dotenv

from app import fetch_json

GAME_IDS = [
    126,     # Sid Meier's Civilization IV
    163295,  # Quern - Undying Thoughts
    117,     # Company of Heroes
    88304,   # Borderlands 2
    204144,  # Overpass
    279127,  # Cross Blitz
    158317,  # Owlboy
    166740,  # For The King
    279822,  # War Hospital
    218578,  # Werewolf: the Apocalypse - Heart of the Forest
    290092,  # SteamWorld Heist II
    199102,  # Warhammer: Chaosbane
    208,     # Company of Heroes: Opposing Fronts
    173596,  # Frostpunk
    204666,  # WRC 8 FIA World Rally Championship
    136930,  # This War of Mine
    429,     # Hitman: Blood Money
    278103,  # Nickelodeon All-Star Brawl 2
    150371,  # We Are The Dwarves
    145148,  # Dropsy
]


def save_game(conn, game_id, info):
    conn.execute(
        'INSERT INTO games (id, title, steam_app_id, thumb_url) '
        'VALUES (%s, %s, %s, %s) ON CONFLICT (id) DO NOTHING',
        (int(game_id), info['title'], info['steamAppID'], info['thumb']),
    )


def main():
    load_dotenv()
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        sys.exit('DATABASE_URL is not set.')

    ids_text = ','.join(str(game_id) for game_id in GAME_IDS)
    games = fetch_json('games', {'ids': ids_text})
    print(f'Games received: {len(games)}')

    with psycopg.connect(database_url) as conn:
        for game_id, game in games.items():
            save_game(conn, game_id, game['info'])
        row = conn.execute('SELECT COUNT(*) FROM games').fetchone()
    print(row[0])


if __name__ == '__main__':
    main()
