import time

import api


def test_sixth_wrong_login_returns_429(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # 5 wrong passwords: all refused with 401
    for _ in range(api.LOGIN_MAX_FAILURES):
        login = client.post(
            "/auth/login",
            json={"username": "test1", "password": "pass1234"},
        )
        assert login.status_code == 401

    # Log in attempt 6 - wrong password
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass1234"},
    )
    assert login.status_code == 429
    assert login.json()["detail"] == "Too many login attempts. Try again later."


def test_five_wrong_login_and_sixth_correct_returns_429(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # 5 wrong passwords: all refused with 401
    for _ in range(api.LOGIN_MAX_FAILURES):
        login = client.post(
            "/auth/login",
            json={"username": "test1", "password": "pass1234"},
        )
        assert login.status_code == 401

    # Log in attempt 6 - correct password
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 429
    assert login.json()["detail"] == "Too many login attempts. Try again later."


def test_six_correct_login_does_not_return_error(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # 6 correct logins in a row: all accepted with 200
    for _ in range(api.LOGIN_MAX_FAILURES + 1):
        login = client.post(
            "/auth/login",
            json={"username": "test1", "password": "pass12345"},
        )
        assert login.status_code == 200


def test_old_failures_expire_after_the_window(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Pretend this ip failed 5 times, 1 minute BEFORE the window started
    old_time = time.time() - api.LOGIN_WINDOW_SECONDS - 60
    api.FAILED_LOGIN_TIMES["testclient"] = [old_time] * api.LOGIN_MAX_FAILURES

    # Log in with the right password: works, the old failures no longer count
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 200

    # The old failures were thrown away
    assert api.FAILED_LOGIN_TIMES["testclient"] == []
