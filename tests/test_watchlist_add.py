import os

import psycopg
import pytest

import watchlist
from conftest import CHEAPSHARK_DOWN_GAME_ID, UNKNOWN_GAME_ID


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


def add_known_games(*game_ids):  # * allows me to add as many games as needed - tupla
    """Put games straight into the games table, so adding them never calls CheapShark."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for game_id in game_ids:
            conn.execute(
                "INSERT INTO games (id, title) VALUES (%s, %s)",
                (game_id, f"Known game {game_id}"),
            )


def query(sql, params=()):
    """Run a SELECT on the test database and return all rows."""
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        return conn.execute(sql, params).fetchall()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_add_without_login_returns_401(clear_watchlist, client, fake_cheapshark):
    # Try to add a game without logging in: refused
    response = client.post("/watchlist", json={"game_id": 1})
    assert response.status_code == 401
    assert response.json()["detail"] == "Not logged in."

    # Nothing was saved, and CheapShark was never asked
    assert query("SELECT * FROM watchlist") == []
    assert fake_cheapshark == []


# ---------------------------------------------------------------------------
# Known game (already in the games table)
# ---------------------------------------------------------------------------


def test_add_known_game_returns_201(clear_watchlist, client, fake_cheapshark):
    # A game the database already knows
    add_known_games(10)
    user_id = log_in(client, "test1")

    # Add it with a target price
    response = client.post("/watchlist", json={"game_id": 10, "target_price": 19.99})
    assert response.status_code == 201
    assert response.json() == {
        "game_id": 10,
        "title": "Known game 10",
        "target_price": 19.99,
    }

    # It is in this person's list, and CheapShark was never asked
    rows = query("SELECT user_id, game_id, target_price FROM watchlist")
    assert len(rows) == 1
    assert rows[0][0] == user_id
    assert rows[0][1] == 10
    assert str(rows[0][2]) == "19.99"
    assert fake_cheapshark == []


def test_add_without_target_price_saves_null(clear_watchlist, client, fake_cheapshark):
    # A known game, added with no target price (just follow it)
    add_known_games(10)
    log_in(client, "test1")

    response = client.post("/watchlist", json={"game_id": 10})
    assert response.status_code == 201
    assert response.json()["target_price"] is None

    # Saved as NULL in the database
    assert query("SELECT target_price FROM watchlist") == [(None,)]


def test_same_game_twice_returns_409(clear_watchlist, client, fake_cheapshark):
    # Add a known game once: works
    add_known_games(10)
    log_in(client, "test1")
    first = client.post("/watchlist", json={"game_id": 10})
    assert first.status_code == 201

    # Add the same game again: refused
    second = client.post("/watchlist", json={"game_id": 10})
    assert second.status_code == 409
    assert second.json()["detail"] == "This game is already in your watchlist."

    # Still only one row
    assert len(query("SELECT * FROM watchlist")) == 1


# ---------------------------------------------------------------------------
# New game (asks CheapShark)
# ---------------------------------------------------------------------------


def test_add_new_game_asks_cheapshark_and_saves_it(
    clear_watchlist, client, fake_cheapshark
):
    # A game the database has never seen
    log_in(client, "test1")

    response = client.post("/watchlist", json={"game_id": 77})
    assert response.status_code == 201
    assert response.json()["title"] == "Game 77"

    # CheapShark was asked exactly once, for this game
    assert fake_cheapshark == [77]

    # The game was saved in games, and in the list
    assert query("SELECT id, title FROM games") == [(77, "Game 77")]
    assert query("SELECT game_id FROM watchlist") == [(77,)]


def test_add_game_unknown_to_cheapshark_returns_404(
    clear_watchlist, client, fake_cheapshark
):
    # A game id CheapShark does not have
    log_in(client, "test1")

    response = client.post("/watchlist", json={"game_id": UNKNOWN_GAME_ID})
    assert response.status_code == 404
    assert response.json()["detail"] == "Game not found on CheapShark."

    # Nothing was saved
    assert query("SELECT * FROM games") == []
    assert query("SELECT * FROM watchlist") == []


def test_cheapshark_down_returns_502(clear_watchlist, client, fake_cheapshark):
    # CheapShark does not answer
    log_in(client, "test1")

    response = client.post("/watchlist", json={"game_id": CHEAPSHARK_DOWN_GAME_ID})
    assert response.status_code == 502

    # Nothing was saved
    assert query("SELECT * FROM games") == []
    assert query("SELECT * FROM watchlist") == []


# ---------------------------------------------------------------------------
# Target price rules (checked by Pydantic before the function runs)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("target_price", [0, -5, 1000.01, 19.999])
def test_invalid_target_price_returns_422(
    clear_watchlist, client, fake_cheapshark, target_price
):
    # Zero, negative, above 1000, or 3 decimal places: refused
    add_known_games(10)
    log_in(client, "test1")

    response = client.post(
        "/watchlist", json={"game_id": 10, "target_price": target_price}
    )
    assert response.status_code == 422
    assert query("SELECT * FROM watchlist") == []


def test_target_price_of_exactly_1000_is_accepted(
    clear_watchlist, client, fake_cheapshark
):
    # The top limit itself is allowed
    add_known_games(10)
    log_in(client, "test1")

    response = client.post("/watchlist", json={"game_id": 10, "target_price": 1000})
    assert response.status_code == 201


# ---------------------------------------------------------------------------
# Limits: 10 per person, 100 in the whole tracker
# ---------------------------------------------------------------------------


def test_eleventh_game_returns_409(clear_watchlist, client, fake_cheapshark):
    limit = watchlist.WATCHLIST_MAX_GAMES  # 10

    # One known game more than the limit (games 1 to 11)
    add_known_games(*range(1, limit + 2))
    log_in(client, "test1")

    # The first 10 work
    for game_id in range(1, limit + 1):
        response = client.post("/watchlist", json={"game_id": game_id})
        assert response.status_code == 201

    # The 11th is refused, and not saved
    response = client.post("/watchlist", json={"game_id": limit + 1})
    assert response.status_code == 409
    assert response.json()["detail"].startswith(f"Your watchlist is full ({limit} games).")
    assert len(query("SELECT * FROM watchlist")) == limit


def fill_the_tracker():
    """Put 100 different games in the watchlist of 10 other people, straight in the database."""
    add_known_games(
        *range(1, watchlist.SYSTEM_MAX_GAMES + 1)
    )  # * opens the range as a tupla, if not, reads range(1,x)
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        for person in range(10):
            user_id = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, 'x') RETURNING id",
                (f"filler{person}",),
            ).fetchone()[0]
            first_game = person * 10 + 1  # person 0 starts at game 1, person 1 at 11, ...
            for game_id in range(first_game, first_game + 10):
                conn.execute(
                    "INSERT INTO watchlist (user_id, game_id) VALUES (%s, %s)",
                    (user_id, game_id),
                )


def test_new_game_when_tracker_is_full_returns_409(
    clear_watchlist, client, fake_cheapshark
):
    # 100 different games are already followed
    fill_the_tracker()
    log_in(client, "test1")

    # A game nobody follows: refused, before asking CheapShark
    response = client.post("/watchlist", json={"game_id": 500})
    assert response.status_code == 409
    assert response.json()["detail"].startswith(
        "The tracker is full right now (100 games)."
    )
    assert fake_cheapshark == []


def test_followed_game_when_tracker_is_full_returns_201(
    clear_watchlist, client, fake_cheapshark
):
    # 100 different games are already followed
    fill_the_tracker()
    log_in(client, "test1")

    # Game 1 is already followed by someone: it does not raise the count, so it is allowed
    response = client.post("/watchlist", json={"game_id": 1})
    assert response.status_code == 201
    assert fake_cheapshark == []


# ---------------------------------------------------------------------------
# Two people (step 6 of the plan: one account never touches another's list)
# ---------------------------------------------------------------------------


def test_two_people_can_add_the_same_game(clear_watchlist, client, fake_cheapshark):
    # Person A adds a new game: CheapShark is asked once
    log_in(client, "test1")
    first = client.post("/watchlist", json={"game_id": 77})
    assert first.status_code == 201

    # Person B adds the same game: works, and CheapShark is not asked again
    log_in(client, "test2")
    second = client.post("/watchlist", json={"game_id": 77})
    assert second.status_code == 201
    assert fake_cheapshark == [77]

    # One game, two list rows (one per person)
    assert len(query("SELECT * FROM games")) == 1
    assert len(query("SELECT * FROM watchlist")) == 2


def test_user_id_in_the_body_is_ignored(clear_watchlist, client, fake_cheapshark):
    # Person A exists; person B is logged in
    add_known_games(10)
    person_a = log_in(client, "test1")
    person_b = log_in(client, "test2")

    # B sends A's id in the body, trying to add to A's list
    response = client.post("/watchlist", json={"game_id": 10, "user_id": person_a})
    assert response.status_code == 201

    # The game went to B's list: the id always comes from the login cookie
    assert query("SELECT user_id FROM watchlist") == [(person_b,)]
