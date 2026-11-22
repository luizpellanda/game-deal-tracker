from fastapi.testclient import TestClient

import api
import config

client = TestClient(api.app)


def test_tests_use_the_test_database():
    assert config.DATABASE_URL.endswith("/game_deals_test")


def test_stats_returns_200():
    response = client.get("/stats")

    assert response.status_code == 200
