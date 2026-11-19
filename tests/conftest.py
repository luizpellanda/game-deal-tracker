import os
import pytest
import psycopg

# pytest runs this file before any test. Point the API at the test database
# before api.py is imported, so tests never touch the real data.
os.environ["DATABASE_URL"] = "postgresql:///game_deals_test"


@pytest.fixture
def clear_users():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")
