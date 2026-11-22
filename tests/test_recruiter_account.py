import os

import psycopg
import pytest

import api
import seed_recruiter


def count_recruiter_accounts():
    with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
        row = conn.execute(
            "SELECT COUNT(*) FROM users WHERE username = %s",
            (api.RECRUITER_USERNAME,),
        ).fetchone()
    return row[0]


def test_script_twice_keeps_one_recruiter_account(clear_users):
    # Run the script twice, like two days of cron
    seed_recruiter.ensure_recruiter()
    seed_recruiter.ensure_recruiter()

    # Still only one recruiter account
    assert count_recruiter_accounts() == 1


def test_recruiter_can_log_in_with_the_env_password(clear_users, client):
    # Create the recruiter account with the script
    seed_recruiter.ensure_recruiter()

    # Log in with the password from .env: the hash was saved correctly
    login = client.post(
        "/auth/login",
        json={
            "username": api.RECRUITER_USERNAME,
            "password": seed_recruiter.RECRUITER_PASSWORD,
        },
    )
    assert login.status_code == 200


@pytest.mark.parametrize("name", ["recruiter", "Recruiter", "RECRUITER"])
def test_register_refuses_the_recruiter_name(clear_users, client, name):
    # Try to register the reserved name (any upper/lower case): refused
    register = client.post(
        "/auth/register",
        json={"username": name, "password": "pass12345"},
    )
    assert register.status_code == 409
    assert register.json()["detail"] == "Username already taken."

    # No account was created
    assert count_recruiter_accounts() == 0
