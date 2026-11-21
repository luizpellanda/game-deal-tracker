def test_logout_ends_the_session(clear_users, client):
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
    assert me.json() == {"id": register.json()["id"], "username": "test1"}

    # Log out
    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    # Check that we are no longer logged in
    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 401
    assert me_after_logout.json()["detail"] == "Not logged in."


def test_logout_sends_a_delete_cookie_order(client):
    # Log out
    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    # The cookie is replaced by an empty one that expires now,
    # with the same options it was created with
    cookie = logout.headers["set-cookie"]

    assert cookie.startswith('access_token=""')
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie


def test_logout_without_login_returns_200(client):
    # Log out without being logged in: still works
    logout = client.post("/auth/logout")

    assert logout.status_code == 200
    assert logout.json() == {"detail": "Logged out."}
