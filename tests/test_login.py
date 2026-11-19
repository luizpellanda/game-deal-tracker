from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_correct_password_returns_200(clear_users):
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


def test_incorrect_password_returns_401(clear_users):
    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )

    assert register.status_code == 201

    login = client.post(
        "/auth/login",
        json={"username": "luiz", "password": "pass1234"},
    )

    assert login.status_code == 401


def test_incorrect_password_and_incorrect_username_returns_same_error_message(
    clear_users,
):
    register = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )

    assert register.status_code == 201

    wrong_username = client.post(
        "/auth/login",
        json={"username": "ghost", "password": "pass12345"},
    )

    assert wrong_username.status_code == 401

    wrong_password = client.post(
        "/auth/login",
        json={"username": "luiz", "password": "pass1234"},
    )

    assert wrong_password.status_code == 401
    assert wrong_username.json()["detail"] == wrong_password.json()["detail"]
