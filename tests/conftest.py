import os

import psycopg
import pytest
from fastapi.testclient import TestClient

# pytest runs this file before any test. Point the API at the test database
# before api.py is imported, so tests never touch the real data.
os.environ["DATABASE_URL"] = "postgresql:///game_deals_test"

import api  # must come after the line above, so api.py uses the test database
import auth
import watchlist
from app import CheapSharkError


@pytest.fixture
def clear_users():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")


@pytest.fixture
def client():
    return TestClient(api.app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def clear_ip_limits():
    auth.FAILED_LOGIN_TIMES.clear()
    auth.REGISTER_TIMES.clear()


@pytest.fixture
def clear_watchlist():
    """Start from empty users, watchlist and games (test database only)."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")  # the watchlist goes with them (ON DELETE CASCADE)
        conn.execute("DELETE FROM watchlist")
        conn.execute("DELETE FROM price_history")
        conn.execute("DELETE FROM games")


# Game ids the fake CheapShark treats as errors.
UNKNOWN_GAME_ID = 404404
CHEAPSHARK_DOWN_GAME_ID = 502502


@pytest.fixture
def fake_cheapshark(monkeypatch):
    """Replace the CheapShark call in watchlist.py with a fake one.

    Returns the list of game ids that were "asked" to CheapShark,
    so a test can check whether it was called or not.
    """
    calls = []

    def fake_fetch_json(endpoint, params):
        calls.append(params["id"])
        if params["id"] == UNKNOWN_GAME_ID:
            raise CheapSharkError("Not found", status_code=404)
        if params["id"] == CHEAPSHARK_DOWN_GAME_ID:
            raise CheapSharkError("Timed out", status_code=None)
        return {
            "info": {
                "title": f"Game {params['id']}",
                "steamAppID": None,
                "thumb": "https://example.com/thumb.jpg",
            }
        }

    monkeypatch.setattr(watchlist, "fetch_json", fake_fetch_json)
    return calls
