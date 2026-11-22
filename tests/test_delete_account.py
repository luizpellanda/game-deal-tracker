import api
import seed_recruiter


def test_delete_function_deletes_account(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Log in
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 200

    # Check that we are logged in
    me = client.get("/auth/me")
    assert me.status_code == 200

    # Delete the account with the right password
    delete_account = client.post("/auth/delete-account", json={"password": "pass12345"})
    assert delete_account.status_code == 200
    assert "Max-Age=0" in delete_account.headers["set-cookie"]
    assert delete_account.json()["detail"] == "Account deleted."

    # Log in again: fails, the account is gone from the database
    login_after_delete = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login_after_delete.status_code == 401

    # Check that we are no longer logged in
    me_after_delete = client.get("/auth/me")
    assert me_after_delete.status_code == 401


def test_delete_function_with_no_login(clear_users, client):
    # Create the account, but do NOT log in
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Try to delete: refused, nobody is logged in
    delete_account = client.post("/auth/delete-account", json={"password": "pass12345"})
    assert delete_account.status_code == 401
    assert delete_account.json()["detail"] == "Not logged in."


def test_delete_function_with_incorrect_password(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Log in
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 200

    # Try to delete with the wrong password: refused
    delete_account = client.post("/auth/delete-account", json={"password": "pass12346"})
    assert delete_account.status_code == 401
    assert delete_account.json()["detail"] == "Wrong password."

    # Log in again: works, the account still exists
    login_after_wrong_password = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login_after_wrong_password.status_code == 200


def test_impossible_of_deleting_recruiter_account(clear_users, client):
    # Create the recruiter account with the script (the register endpoint refuses this name)
    seed_recruiter.ensure_recruiter()

    # Log in as the recruiter
    login = client.post(
        "/auth/login",
        json={
            "username": api.RECRUITER_USERNAME,
            "password": seed_recruiter.RECRUITER_PASSWORD,
        },
    )
    assert login.status_code == 200

    # Try to delete with the right password: forbidden
    delete_account = client.post(
        "/auth/delete-account",
        json={"password": seed_recruiter.RECRUITER_PASSWORD},
    )

    assert delete_account.status_code == 403
    assert (
        delete_account.json()["detail"]
        == "No. Not cool. Please leave the recruiter account alone."
    )

    # Log in again: works, the recruiter account still exists
    login_after_403 = client.post(
        "/auth/login",
        json={
            "username": api.RECRUITER_USERNAME,
            "password": seed_recruiter.RECRUITER_PASSWORD,
        },
    )
    assert login_after_403.status_code == 200


def test_one_user_cant_delete_other_account(clear_users, client):
    # Create account A (test1)
    register_a = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass123456"},
    )
    assert register_a.status_code == 201

    # Create account B (test2)
    register_b = client.post(
        "/auth/register",
        json={"username": "test2", "password": "pass123456"},
    )
    assert register_b.status_code == 201

    # Log in as A
    login_a = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass123456"},
    )
    assert login_a.status_code == 200

    # Check that A is logged in
    me = client.get("/auth/me")
    assert me.status_code == 200

    # A deletes its own account
    delete_account = client.post(
        "/auth/delete-account", json={"password": "pass123456"}
    )
    assert delete_account.status_code == 200
    assert "Max-Age=0" in delete_account.headers["set-cookie"]
    assert delete_account.json()["detail"] == "Account deleted."

    # Log in as A again: fails, A is gone
    login_a_after_delete = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass123456"},
    )
    assert login_a_after_delete.status_code == 401

    # Log in as B: works, B was not touched
    login_b = client.post(
        "/auth/login",
        json={"username": "test2", "password": "pass123456"},
    )
    assert login_b.status_code == 200
