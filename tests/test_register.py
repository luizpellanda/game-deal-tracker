from fastapi.testclient import TestClient

import api

client = TestClient(api.app)


def test_register_returns_201_and_username(clear_users):
    # Register a valid new user
    response = client.post(
        "/auth/register",
        json={"username": "test1", "password": "pass12345"},
    )

    # Account created, and the response shows the username
    assert response.status_code == 201
    assert response.json()["username"] == "test1"


def test_register_returns_lowercase(clear_users):
    # Register with an uppercase letter in the name
    response = client.post(
        "/auth/register",
        json={"username": "Test1", "password": "pass12345"},
    )

    # The name is saved in lowercase
    assert response.status_code == 201
    assert response.json()["username"] == "test1"


def test_register_user_two_char_name_returns_422(clear_users):
    # Name with only 2 characters (minimum is 3)
    response = client.post(
        "/auth/register",
        json={"username": "ab", "password": "pass12345"},
    )

    assert response.status_code == 422


def test_register_forbidden_char_returns_422(clear_users):
    # Name with a forbidden character (!)
    response = client.post(
        "/auth/register",
        json={"username": "Test1!", "password": "pass12345"},
    )

    assert response.status_code == 422


def test_register_password_7_char_returns_422(clear_users):
    # Password with only 7 characters (minimum is 8)
    response = client.post(
        "/auth/register",
        json={"username": "Test1", "password": "pass123"},
    )

    assert response.status_code == 422


def test_register_password_129_char_returns_422(clear_users):
    # Password with 129 characters (maximum is 128)
    response = client.post(
        "/auth/register",
        json={
            "username": "Test1",
            "password": "314159265358979323846264338327950288419716939937510582097494459230781640628620899862803482534211706798214808651328230664709384460",
        },
    )

    assert response.status_code == 422


def test_register_existing_username_returns_409(clear_users):
    # First register: works
    response_first_register = client.post(
        "/auth/register",
        json={
            "username": "Test1",
            "password": "pass12345",
        },
    )

    assert response_first_register.status_code == 201
    assert response_first_register.json()["username"] == "test1"

    # Same name again: conflict
    response = client.post(
        "/auth/register",
        json={
            "username": "Test1",
            "password": "pass12345",
        },
    )

    assert response.status_code == 409


def test_register_password_and_hash_not_in_response(clear_users):
    # Register a valid new user
    response = client.post(
        "/auth/register",
        json={
            "username": "Test1",
            "password": "pass12345",
        },
    )

    # Neither the password nor the hash are sent back
    assert response.status_code == 201
    assert "password_hash" not in response.json()
    assert "password" not in response.json()
