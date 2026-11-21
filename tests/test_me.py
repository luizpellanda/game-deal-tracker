import os
from datetime import datetime, timedelta, timezone

import jwt
import psycopg

import api


def test_me_after_login_returns_user_returns_200(clear_users, client):

    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert login.status_code == 200

    me = client.get("/auth/me")

    assert me.status_code == 200
    assert me.json() == {"id": register.json()["id"], "username": "luiz"}


def test_me_without_cookie_returns_401(clear_users, client):

    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert register.status_code == 201

    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_fake_token_returns_401(clear_users, client):

    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert register.status_code == 201

    client.cookies.set("access_token", "abc")  # sets fake token in cookie
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_expired_token_returns_401(clear_users, client):

    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert register.status_code == 201

    expired = jwt.encode(
        {
            "sub": str(register.json()["id"]),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        api.SECRET_KEY,
        algorithm="HS256",
    )
    client.cookies.set("access_token", expired)  # sets expired token in cookie
    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."


def test_me_with_user_deleted_after_registration_returns_401(clear_users, client):

    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"username": "luiz", "password": "pass12345"},
    )
    assert login.status_code == 200

    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        conn.execute("DELETE FROM users")

    me = client.get("/auth/me")

    assert me.status_code == 401
    assert me.json()["detail"] == "Not logged in."
