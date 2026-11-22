"""Accounts: register, log in, who am I, log out, delete account, and the per-IP limits."""

import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
import psycopg
from fastapi import APIRouter, Cookie, HTTPException, Request, Response
from pwdlib import PasswordHash
from pydantic import BaseModel, Field

from config import DATABASE_URL, SECRET_KEY

router = APIRouter()
password_hasher = PasswordHash.recommended()

FAILED_LOGIN_TIMES = {}
LOGIN_MAX_FAILURES = 5
LOGIN_WINDOW_SECONDS = 15 * 60  # 15 MINUTES

REGISTER_MAX_ACCOUNTS = 5
REGISTER_TIMES = {}
REGISTER_WINDOW_SECONDS = 60 * 60  # 1 HOUR

RECRUITER_USERNAME = "recruiter"

TOKEN_DAYS = 7


class NewUser(BaseModel):
    username: str = Field(min_length=3, max_length=20, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginUser(BaseModel):
    username: str
    password: str = Field(max_length=128)


class DeleteUser(BaseModel):
    password: str = Field(max_length=128)


def recent_times(times_by_ip, ip, window_seconds):
    """Drop the old times of this ip and return the ones still inside the window."""
    now = time.time()
    recent = [t for t in times_by_ip.get(ip, []) if now - t < window_seconds]
    times_by_ip[ip] = recent
    return recent


@router.post("/auth/register", status_code=201)
def create_user(user: NewUser, request: Request):
    ip = request.client.host

    if (
        len(recent_times(REGISTER_TIMES, ip, REGISTER_WINDOW_SECONDS))
        >= REGISTER_MAX_ACCOUNTS
    ):
        raise HTTPException(
            status_code=429, detail="Too many accounts created. Try again later."
        )

    username_lower = user.username.lower()

    if username_lower == RECRUITER_USERNAME:
        raise HTTPException(status_code=409, detail="Username already taken.")

    hashed = password_hasher.hash(user.password)

    with psycopg.connect(DATABASE_URL) as conn:
        try:
            row = conn.execute(
                """
                INSERT INTO users (username, password_hash)
                VALUES (%s, %s)
                RETURNING id, username
                """,
                (username_lower, hashed),
            ).fetchone()
        except psycopg.errors.UniqueViolation:
            raise HTTPException(status_code=409, detail="Username already taken.")

    REGISTER_TIMES[ip].append(time.time())

    return {"id": row[0], "username": row[1]}


@router.post("/auth/login")
def login(user: LoginUser, response: Response, request: Request):
    username_lower = user.username.lower()
    ip = request.client.host

    if (
        len(recent_times(FAILED_LOGIN_TIMES, ip, LOGIN_WINDOW_SECONDS))
        >= LOGIN_MAX_FAILURES
    ):
        raise HTTPException(
            status_code=429, detail="Too many login attempts. Try again later."
        )

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            SELECT id, username, password_hash
            FROM users
            WHERE username = %s
            """,
            (username_lower,),
        ).fetchone()

    if row is None:
        FAILED_LOGIN_TIMES[ip].append(time.time())
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    user_id = row[0]
    user_name = row[1]
    saved_hash = row[2]
    if not password_hasher.verify(user.password, saved_hash):
        FAILED_LOGIN_TIMES[ip].append(time.time())
        raise HTTPException(status_code=401, detail="Wrong username or password.")

    payload = {
        "sub": str(user_id),
        "exp": datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS),
    }

    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    response.set_cookie(
        key="access_token",
        value=token,
        max_age=TOKEN_DAYS * 60 * 60 * 24,
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"id": user_id, "username": user_name}


def get_current_user(access_token):
    """Return the logged-in user as {"id", "username"}, or raise 401."""
    if access_token is None:
        raise HTTPException(status_code=401, detail="Not logged in.")

    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Not logged in.")

    user_id = int(payload["sub"])
    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
            SELECT id, username
            FROM users
            WHERE id = %s
            """,
            (user_id,),
        ).fetchone()

    if row is None:
        raise HTTPException(status_code=401, detail="Not logged in.")

    return {"id": row[0], "username": row[1]}


@router.get("/auth/me")
def get_me(access_token: Annotated[str | None, Cookie()] = None):
    return get_current_user(access_token)


@router.post("/auth/logout")
def logout(response: Response):
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"detail": "Logged out."}


@router.post("/auth/delete-account")
def delete_user(
    body: DeleteUser,
    response: Response,
    access_token: Annotated[str | None, Cookie()] = None,
):
    user = get_current_user(access_token)
    user_id = user["id"]
    username = user["username"]

    if username == RECRUITER_USERNAME:
        raise HTTPException(
            status_code=403,
            detail="No. Not cool. Please leave the recruiter account alone.",
        )

    with psycopg.connect(DATABASE_URL) as conn:
        row = conn.execute(
            """
                SELECT password_hash
                FROM users
                WHERE id = %s
                """,
            (user_id,),
        ).fetchone()

    saved_hash = row[0]

    if not password_hasher.verify(body.password, saved_hash):
        raise HTTPException(status_code=401, detail="Wrong password.")

    with psycopg.connect(DATABASE_URL) as conn:
        conn.execute(
            """
                DELETE FROM users
                WHERE id = %s
                """,
            (user_id,),
        )

    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=True,
        samesite="lax",
    )

    return {"detail": "Account deleted."}
