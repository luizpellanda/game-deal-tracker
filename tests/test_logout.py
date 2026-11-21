def test_logout_ends_the_session(clear_users, client):
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

    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    me_after_logout = client.get("/auth/me")
    assert me_after_logout.status_code == 401
    assert me_after_logout.json()["detail"] == "Not logged in."


def test_logout_sends_a_delete_cookie_order(client):
    logout = client.post("/auth/logout")
    assert logout.status_code == 200

    cookie = logout.headers["set-cookie"]

    assert cookie.startswith('access_token=""')
    assert "Max-Age=0" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie


def test_logout_without_login_returns_200(client):
    logout = client.post("/auth/logout")

    assert logout.status_code == 200
    assert logout.json() == {"detail": "Logged out."}
