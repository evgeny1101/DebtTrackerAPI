def test_register(client):
    res = client.post("/api/auth/register", json={"username": "alice", "password": "secret123"})
    assert res.status_code == 201
    data = res.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"


def test_register_duplicate(client):
    client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})
    res = client.post("/api/auth/register", json={"username": "bob", "password": "secret123"})
    assert res.status_code == 409
    assert res.json()["detail"] == "Username already taken"


def test_login_success(client):
    client.post("/api/auth/register", json={"username": "eve", "password": "secret123"})
    res = client.post("/api/auth/login", json={"username": "eve", "password": "secret123"})
    assert res.status_code == 200
    data = res.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"


def test_login_wrong_password(client):
    client.post("/api/auth/register", json={"username": "mallory", "password": "correct"})
    res = client.post("/api/auth/login", json={"username": "mallory", "password": "wrong"})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid credentials"


def test_login_nonexistent_user(client):
    res = client.post("/api/auth/login", json={"username": "ghost", "password": "secret"})
    assert res.status_code == 401


def test_refresh_success(client):
    reg = client.post("/api/auth/register", json={"username": "dave", "password": "secret123"})
    old_refresh = reg.json()["refreshToken"]

    res = client.post("/api/auth/refresh", json={"refreshToken": old_refresh})
    assert res.status_code == 200
    data = res.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["refreshToken"] != old_refresh


def test_refresh_used_token_fails(client):
    reg = client.post("/api/auth/register", json={"username": "frank", "password": "secret123"})
    old_refresh = reg.json()["refreshToken"]

    client.post("/api/auth/refresh", json={"refreshToken": old_refresh})
    res = client.post("/api/auth/refresh", json={"refreshToken": old_refresh})
    assert res.status_code == 401
    assert res.json()["detail"] == "Invalid refresh token"


def test_refresh_invalid_token(client):
    res = client.post("/api/auth/refresh", json={"refreshToken": "not-a-real-token"})
    assert res.status_code == 401


def test_refresh_expired_token(client):
    reg = client.post("/api/auth/register", json={"username": "grace", "password": "secret123"})
    token = reg.json()["refreshToken"]

    from app.database import SessionLocal
    from app.models import RefreshToken

    db = SessionLocal()
    stored = db.query(RefreshToken).filter(RefreshToken.token == token).first()
    stored.expiresAt = 0
    db.commit()
    db.close()

    res = client.post("/api/auth/refresh", json={"refreshToken": token})
    assert res.status_code == 401
    assert res.json()["detail"] == "Refresh token expired"


def test_logout(client):
    reg = client.post("/api/auth/register", json={"username": "heidi", "password": "secret123"})
    token = reg.json()["accessToken"]
    refresh = reg.json()["refreshToken"]

    res = client.post(
        "/api/auth/logout",
        json={"refreshToken": refresh},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204

    res = client.post("/api/auth/refresh", json={"refreshToken": refresh})
    assert res.status_code == 401


def test_logout_invalid_refresh_token(client):
    reg = client.post("/api/auth/register", json={"username": "ivan", "password": "secret123"})
    token = reg.json()["accessToken"]

    res = client.post(
        "/api/auth/logout",
        json={"refreshToken": "not-real"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 204


def test_protected_route_without_token(client):
    res = client.get("/api/debts")
    assert res.status_code == 401


def test_protected_route_with_valid_token(client):
    reg = client.post("/api/auth/register", json={"username": "judy", "password": "secret123"})
    token = reg.json()["accessToken"]
    res = client.get("/api/debts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
