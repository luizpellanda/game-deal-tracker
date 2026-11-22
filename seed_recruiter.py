import os
import sys

import psycopg
from dotenv import load_dotenv

from api import RECRUITER_USERNAME, password_hasher

load_dotenv()

RECRUITER_PASSWORD = os.getenv("RECRUITER_PASSWORD")
if not RECRUITER_PASSWORD:
    sys.exit("RECRUITER_PASSWORD is not set.")


DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is not set.")


def ensure_recruiter():
    hashed = password_hasher.hash(RECRUITER_PASSWORD)

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
            ON CONFLICT (username) DO NOTHING
            RETURNING id
            """,
            (RECRUITER_USERNAME, hashed),
        ).fetchone()

    if row is None:
        message = "Recruiter account already exists."
    else:
        message = f"Recruiter account created. Id: {row[0]}."

    print(message)


def main():
    ensure_recruiter()


if __name__ == "__main__":
    main()
