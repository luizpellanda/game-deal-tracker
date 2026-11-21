import jwt
from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_correct_password_returns_200(clear_users):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )

    assert register.status_code == 201

    # Log in with the right password
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )

    assert login.status_code == 200


def test_incorrect_password_returns_401(clear_users):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )

    assert register.status_code == 201

    # Log in with the wrong password
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass1234"},
    )

    assert login.status_code == 401


def test_incorrect_password_and_incorrect_username_returns_same_error_message(
    clear_users,
):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )

    assert register.status_code == 201

    # Log in with a name that does not exist
    wrong_username = client.post(
        "/auth/login",
        json={"username": "ghost", "password": "pass12345"},
    )

    assert wrong_username.status_code == 401

    # Log in with the right name but the wrong password
    wrong_password = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass1234"},
    )

    # Both errors give the same message
    assert wrong_password.status_code == 401
    assert wrong_username.json()["detail"] == wrong_password.json()["detail"]


def test_correct_login_creates_cookie(clear_users):
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

    # The token is in the cookie, not in the JSON
    assert login.status_code == 200
    assert "access_token" in login.cookies
    assert "access_token" not in login.json()

    # The token belongs to this user
    token = login.cookies["access_token"]
    payload = jwt.decode(token, api.SECRET_KEY, algorithms=["HS256"])
    assert payload["sub"] == str(login.json()["id"])


def test_cookie_security_verification(clear_users):
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

    # The cookie has all the security options
    cookie = login.headers["set-cookie"]

    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert f"Max-Age={api.TOKEN_DAYS * 60 * 60 * 24}" in cookie


def test_incorrect_login_does_not_create_cookie(clear_users):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )

    assert register.status_code == 201

    # Log in with the wrong password
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12344"},
    )

    # No cookie is created
    assert login.status_code == 401
    assert "access_token" not in login.cookies
