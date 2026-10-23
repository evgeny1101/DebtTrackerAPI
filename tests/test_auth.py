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

    from app.auth import hash_token
    from app.database import SessionLocal
    from app.models import RefreshToken

    db = SessionLocal()
    stored = db.query(RefreshToken).filter(RefreshToken.token == hash_token(token)).first()
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


def test_docs_enabled_in_development(client):
    assert client.get("/docs").status_code == 200
    assert client.get("/openapi.json").status_code == 200


def test_body_size_limited(client):
    big = {"name": "x" * (1024 * 1024 + 512), "debtType": "I_OWE", "initialAmount": 1}
    res = client.post("/api/debts", json=big)
    assert res.status_code == 413


def test_refresh_token_stored_hashed(client):
    reg = client.post("/api/auth/register", json={"username": "hsh", "password": "secret123"})
    refresh = reg.json()["refreshToken"]

    from app.auth import hash_token
    from app.database import SessionLocal
    from app.models import RefreshToken

    db = SessionLocal()
    stored = db.query(RefreshToken).filter(RefreshToken.userId == 1).first()
    db.close()

    assert stored is not None
    assert stored.token != refresh
    assert stored.token == hash_token(refresh)


def test_invalid_sub_returns_401(client):
    from datetime import UTC, datetime, timedelta

    from jose import jwt

    from app.config import JWT_ALGORITHM, JWT_SECRET

    bad = jwt.encode(
        {"sub": "not-an-int", "exp": datetime.now(UTC) + timedelta(minutes=5)},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    res = client.get("/api/debts", headers={"Authorization": f"Bearer {bad}"})
    assert res.status_code == 401


def test_rate_limit_key_uses_x_forwarded_for():
    from starlette.requests import Request

    from app.limiter import _client_key

    scope = {
        "type": "http",
        "headers": [(b"x-forwarded-for", b"203.0.113.7, 10.0.0.1")],
        "client": ("1.2.3.4", 1234),
    }
    assert _client_key(Request(scope)) == "203.0.113.7"


def test_rate_limit_key_falls_back_to_client_host():
    from starlette.requests import Request

    from app.limiter import _client_key

    scope = {"type": "http", "headers": [], "client": ("1.2.3.4", 1234)}
    assert _client_key(Request(scope)) == "1.2.3.4"


def test_delete_account_cascades_all_data(client):
    reg = client.post("/api/auth/register", json={"username": "casc", "password": "secret123"})
    token = reg.json()["accessToken"]

    debt = client.post(
        "/api/debts",
        json={"name": "Book", "debtType": "I_OWE", "initialAmount": 500},
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    client.post(
        f"/api/debts/{debt['id']}/payments",
        json={"amount": 100},
        headers={"Authorization": f"Bearer {token}"},
    )

    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    user_id = db.query(User).filter(User.username == "casc").first().id
    db.close()

    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204

    from app.models import Debt, Payment, RefreshToken

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.username == "casc").first() is None
        assert db.query(Debt).filter(Debt.id == debt["id"]).first() is None
        assert db.query(Payment).filter(Payment.debtId == debt["id"]).first() is None
        assert db.query(RefreshToken).filter(RefreshToken.userId == user_id).first() is None
    finally:
        db.close()


def test_delete_account_invalidates_credentials(client):
    reg = client.post("/api/auth/register", json={"username": "gone", "password": "secret123"})
    token = reg.json()["accessToken"]
    refresh = reg.json()["refreshToken"]

    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204

    res = client.get("/api/debts", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401

    res = client.post("/api/auth/refresh", json={"refreshToken": refresh})
    assert res.status_code == 401

    res = client.post("/api/auth/login", json={"username": "gone", "password": "secret123"})
    assert res.status_code == 401

    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 401


def test_delete_account_without_token(client):
    res = client.delete("/api/auth/me")
    assert res.status_code == 401


def test_delete_account_isolation(client):
    reg_a = client.post("/api/auth/register", json={"username": "user_a", "password": "secret123"})
    token_a = reg_a.json()["accessToken"]
    reg_b = client.post("/api/auth/register", json={"username": "user_b", "password": "secret123"})
    token_b = reg_b.json()["accessToken"]

    debt_b = client.post(
        "/api/debts",
        json={"name": "Bob debt", "debtType": "I_OWE", "initialAmount": 300},
        headers={"Authorization": f"Bearer {token_b}"},
    ).json()

    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 204

    res = client.get("/api/debts", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 200
    assert any(d["id"] == debt_b["id"] for d in res.json())


def test_delete_account_frees_username(client):
    reg = client.post("/api/auth/register", json={"username": "reuse", "password": "secret123"})
    token = reg.json()["accessToken"]

    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204

    res = client.post("/api/auth/register", json={"username": "reuse", "password": "secret123"})
    assert res.status_code == 201


def test_delete_account_vk_user(client):
    import time

    from app.auth import create_access_token
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    user = User(
        username="vk_123",
        passwordHash=None,
        vkId="123",
        createdAt=int(time.time() * 1000),
    )
    db.add(user)
    db.commit()
    user_id = user.id
    db.close()

    token = create_access_token(user_id)
    res = client.delete("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 204

    db = SessionLocal()
    try:
        assert db.query(User).filter(User.vkId == "123").first() is None
    finally:
        db.close()
