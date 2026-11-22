import time

import api


def test_sixth_account_from_same_ip_returns_429(clear_users, client):
    # Create 5 accounts from the same ip: all work
    for number in range(api.REGISTER_MAX_ACCOUNTS):
        register = client.post(
            "/auth/register",
            json={"username": f"test{number}", "password": "pass12345"},
        )
        assert register.status_code == 201

    # Try a 6th account: refused
    register = client.post(
        "/auth/register",
        json={"username": "test99", "password": "pass12345"},
    )
    assert register.status_code == 429
    assert register.json()["detail"] == "Too many accounts created. Try again later."


def test_failed_registers_do_not_count(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Try the same name 5 times: refused with 409, no account created
    for _ in range(api.REGISTER_MAX_ACCOUNTS):
        register_same_name = client.post(
            "/auth/register",
            json={"username": "test1", "password": "pass12345"},
        )
        assert register_same_name.status_code == 409

    # Create a new account: works, only 1 account was created so far
    register_new = client.post(
        "/auth/register",
        json={"username": "test2", "password": "pass12345"},
    )
    assert register_new.status_code == 201


def test_old_accounts_expire_after_the_window(clear_users, client):
    # Pretend this ip created 5 accounts, 1 minute BEFORE the window started
    old_time = time.time() - api.REGISTER_WINDOW_SECONDS - 60
    api.REGISTER_TIMES["testclient"] = [old_time] * api.REGISTER_MAX_ACCOUNTS

    # Create a new account: works, the old ones no longer count
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Only the new account is in the list now
    assert len(api.REGISTER_TIMES["testclient"]) == 1
