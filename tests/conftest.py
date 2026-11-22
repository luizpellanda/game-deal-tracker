import os

import psycopg
import pytest
from fastapi.testclient import TestClient

# pytest runs this file before any test. Point the API at the test database
# before api.py is imported, so tests never touch the real data.
os.environ["DATABASE_URL"] = "postgresql:///game_deals_test"

import api  # must come after the line above, so api.py uses the test database


@pytest.fixture
def clear_users():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")


@pytest.fixture
def client():
    return TestClient(api.app, base_url="https://testserver")


@pytest.fixture(autouse=True)
def clear_ip_limits():
    api.FAILED_LOGIN_TIMES.clear()
    api.REGISTER_TIMES.clear()
