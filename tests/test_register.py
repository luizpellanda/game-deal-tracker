from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_register_returns_201_and_username(clear_users):
    response = client.post(
        "/auth/register",
        json={"username": "luiz", "password": "pass12345"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "luiz"


def test_register_returns_lowercase(clear_users):
    response = client.post(
        "/auth/register",
        json={"username": "Luiz", "password": "pass12345"},
    )

    assert response.status_code == 201
    assert response.json()["username"] == "luiz"


def test_register_user_two_char_name_returns_422(clear_users):
    response = client.post(
        "/auth/register",
        json={"username": "lu", "password": "pass12345"},
    )

    assert response.status_code == 422


def test_register_forbidden_char_returns_422(clear_users):
    response = client.post(
        "/auth/register",
        json={"username": "Luiz!", "password": "pass12345"},
    )

    assert response.status_code == 422


def test_register_password_7_char_returns_422(clear_users):
    response = client.post(
        "/auth/register",
        json={"username": "Luiz", "password": "pass123"},
    )

    assert response.status_code == 422


def test_register_password_129_char_returns_422(clear_users):
    response = client.post(
        "/auth/register",
        json={
            "username": "Luiz",
            "password": "314159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460",
        },
    )

    assert response.status_code == 422


def test_register_existing_username_returns_409(clear_users):
    response_first_register = client.post(
        "/auth/register",
        json={
            "username": "Luiz",
            "password": "pass12345",
        },
    )

    assert response_first_register.status_code == 201
    assert response_first_register.json()["username"] == "luiz"

    response = client.post(
        "/auth/register",
        json={
            "username": "Luiz",
            "password": "pass12345",
        },
    )

    assert response.status_code == 409


def test_register_password_and_hash_not_in_response(clear_users):
    response = client.post(
        "/auth/register",
        json={
            "username": "Luiz",
            "password": "pass12345",
        },
    )

    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert "password" not in response.json()
