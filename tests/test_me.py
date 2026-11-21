import os
from datetime import datetime, timedelta, timezone

import jwt
import psycopg

import api


def test_me_after_login_returns_user_returns_200(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Log in (the client keeps the cookie)
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 200

    # Ask who is logged in: the same user
    me = client.get("/auth/me")

    assert me.status_code == 200
    assert me.json() == {"id": register.json()["id"], "username": "test1"}


def test_me_without_cookie_returns_401(clear_users, client):
    # Create the account, but do NOT log in
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Ask who is logged in: nobody
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_fake_token_returns_401(clear_users, client):
    # Create the account, but do NOT log in
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Put a fake token in the cookie
    client.cookies.set("access_token", "abc")

    # Ask who is logged in: the fake token is refused
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_expired_token_returns_401(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Build a real token for this user that expired 1 minute ago
    expired = jwt.encode(
        {
            "sub": str(register.json()["id"]),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        api.SECRET_KEY,
        algorithm="HS256",
    )
    client.cookies.set("access_token", expired)

    # Ask who is logged in: the expired token is refused
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_user_deleted_after_registration_returns_401(clear_users, client):
    # Create the account
    register = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )
    assert register.status_code == 201

    # Log in (the client keeps a valid token)
    login = client.post(
        "/auth/login",
        json={"username": "test1", "password": "pass12345"},
    )
    assert login.status_code == 200

    # Delete the user straight from the database
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")

    # Ask who is logged in: the token is valid, but the user is gone
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."
