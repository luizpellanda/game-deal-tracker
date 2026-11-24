import os
from datetime import date

import psycopg

# Dates used for the prices. Fixed dates, so the tests never depend on the real "today".
YESTERDAY = date(2026, 11, 22)
TODAY = date(2026, 11, 23)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def log_in(client, username):
    """Create an account and log in with it. Returns the user id."""
    register = client.post(
        "/auth/register",
        json={"username": username, "password": "pass12345"},
    )
    assert register.status_code == 201
    login = client.post(
        "/auth/login",
        json={"username": username, "password": "pass12345"},
    )
    assert login.status_code == 200
    return register.json()["id"]


def run(sql, params=()):
    """Run one SQL command on the test database."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute(sql, params)


def add_game(game_id, title):
    run(
        "INSERT INTO games (id, title, thumb_url) VALUES (%s, %s, %s)",
        (game_id, title, f"https://example.com/{game_id}.jpg"),
    )


def add_price(game_id, store_id, sale_price, normal_price, day):
    run(
        """
        INSERT INTO price_history (game_id, store_id, sale_price, normal_price, recorded_on)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (game_id, store_id, sale_price, normal_price, day),
    )


def follow(user_id, game_id, target_price=None):
    """Put a game straight in someone's watchlist."""
    run(
        "INSERT INTO watchlist (user_id, game_id, target_price) VALUES (%s, %s, %s)",
        (user_id, game_id, target_price),
    )


def get_list(client):
    response = client.get("/watchlist")
    assert response.status_code == 200
    return response.json()


# ---------------------------------------------------------------------------
# Who can see the list
# ---------------------------------------------------------------------------


def test_list_without_login_returns_401(clear_watchlist, client):
    response = client.get("/watchlist")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not logged in."


def test_empty_list_returns_200_and_an_empty_list(clear_watchlist, client):
    # Logged in, but nothing in the list yet: not an error
    log_in(client, "test1")
    assert get_list(client) == []


def test_each_person_sees_only_their_own_list(clear_watchlist, client):
    # A follows game 1; B follows game 2
    add_game(1, "Game of A")
    add_game(2, "Game of B")
    person_a = log_in(client, "test1")
    follow(person_a, 1)
    person_b = log_in(client, "test2")  # B is the one logged in now
    follow(person_b, 2)

    # B sees only game 2
    items = get_list(client)
    assert [item["game_id"] for item in items] == [2]


def test_user_id_in_the_address_is_ignored(clear_watchlist, client):
    # A follows game 1; B is logged in and follows game 2
    add_game(1, "Game of A")
    add_game(2, "Game of B")
    person_a = log_in(client, "test1")
    follow(person_a, 1)
    person_b = log_in(client, "test2")
    follow(person_b, 2)

    # B asks for A's list through the address: still gets B's own list
    response = client.get(f"/watchlist?user_id={person_a}")
    assert response.status_code == 200
    assert [item["game_id"] for item in response.json()] == [2]


# ---------------------------------------------------------------------------
# What each item shows
# ---------------------------------------------------------------------------


def test_item_shows_all_fields(clear_watchlist, client):
    # One game with a price in one store today
    add_game(1, "ELDEN RING")
    add_price(1, 7, "20.45", "59.99", TODAY)
    user_id = log_in(client, "test1")
    follow(user_id, 1, "25.00")

    assert get_list(client) == [
        {
            "game_id": 1,
            "title": "ELDEN RING",
            "thumb_url": "https://example.com/1.jpg",
            "target_price": 25.0,
            "lowest_price": 20.45,
            "normal_price": 59.99,
            "store_id": 7,
            "recorded_on": "2026-11-23",
            "discount_percent": 66,
            "below_target": True,
        }
    ]


def test_game_without_price_shows_nulls(clear_watchlist, client):
    # A game nobody collected a price for yet
    add_game(1, "Brand new game")
    user_id = log_in(client, "test1")
    follow(user_id, 1, "10.00")

    item = get_list(client)[0]
    assert item["lowest_price"] is None
    assert item["normal_price"] is None
    assert item["store_id"] is None
    assert item["recorded_on"] is None
    assert item["discount_percent"] is None
    assert item["below_target"] is False


def test_shows_the_cheapest_store(clear_watchlist, client):
    # Same game in three stores today: store 20 is the cheapest
    add_game(1, "Dune")
    add_price(1, 10, "9.00", "20.00", TODAY)
    add_price(1, 20, "8.50", "20.00", TODAY)
    add_price(1, 30, "11.00", "20.00", TODAY)
    user_id = log_in(client, "test1")
    follow(user_id, 1)

    item = get_list(client)[0]
    assert item["store_id"] == 20
    assert item["lowest_price"] == 8.5


def test_shows_the_latest_day_of_that_game(clear_watchlist, client):
    # Cheaper yesterday, more expensive today: today's price wins
    add_game(1, "Dune")
    add_price(1, 10, "5.00", "20.00", YESTERDAY)
    add_price(1, 10, "12.00", "20.00", TODAY)
    user_id = log_in(client, "test1")
    follow(user_id, 1)

    item = get_list(client)[0]
    assert item["lowest_price"] == 12.0
    assert item["recorded_on"] == "2026-11-23"


def test_each_game_uses_its_own_latest_day(clear_watchlist, client):
    # Game 1 was collected today; game 2 only yesterday (say, the collector missed it)
    add_game(1, "Collected today")
    add_game(2, "Collected yesterday")
    add_price(1, 10, "10.00", "20.00", TODAY)
    add_price(2, 10, "15.00", "20.00", YESTERDAY)
    user_id = log_in(client, "test1")
    follow(user_id, 1)
    follow(user_id, 2)

    # Game 2 still shows yesterday's price instead of "no price"
    items = {item["game_id"]: item for item in get_list(client)}
    assert items[2]["lowest_price"] == 15.0
    assert items[2]["recorded_on"] == "2026-11-22"


# ---------------------------------------------------------------------------
# The "below your target" badge
# ---------------------------------------------------------------------------


def badge_for(client, target_price, sale_price="20.00"):
    """Follow one game with this target and this price today; return its below_target."""
    add_game(1, "Dune")
    add_price(1, 10, sale_price, "40.00", TODAY)
    user_id = log_in(client, "test1")
    follow(user_id, 1, target_price)
    return get_list(client)[0]["below_target"]


def test_badge_when_price_is_below_target(clear_watchlist, client):
    assert badge_for(client, target_price="25.00") is True


def test_badge_when_price_equals_target(clear_watchlist, client):
    assert badge_for(client, target_price="20.00") is True


def test_no_badge_when_price_is_above_target(clear_watchlist, client):
    assert badge_for(client, target_price="19.99") is False


def test_no_badge_without_target(clear_watchlist, client):
    assert badge_for(client, target_price=None) is False


# ---------------------------------------------------------------------------
# Order
# ---------------------------------------------------------------------------


def test_biggest_discount_first_and_no_price_last(clear_watchlist, client):
    # Game 1: -25%; game 2: -75%; game 3: no price; game 4: -50%
    for game_id in (1, 2, 3, 4):
        add_game(game_id, f"Game {game_id}")
    add_price(1, 10, "30.00", "40.00", TODAY)
    add_price(2, 10, "10.00", "40.00", TODAY)
    add_price(4, 10, "20.00", "40.00", TODAY)
    user_id = log_in(client, "test1")
    for game_id in (1, 2, 3, 4):
        follow(user_id, game_id)

    assert [item["game_id"] for item in get_list(client)] == [2, 4, 1, 3]
