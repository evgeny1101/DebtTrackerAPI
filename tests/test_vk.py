from app.database import SessionLocal
from app.models import User
from app.vk import VKAuthError


def _enable_vk(monkeypatch):
    monkeypatch.setattr("app.routers.auth.VK_CLIENT_ID", "test-client-id")


def _mock_vk(
    monkeypatch, user_id=12345, first_name="Ivan", last_name="Petrov", email="ivan@example.com"
):
    def exchange(code, redirect_uri, code_verifier, device_id, state=None):
        return {"access_token": "vk-access-token", "user_id": user_id}

    def user_info(access_token):
        return {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "email": email,
        }

    monkeypatch.setattr("app.vk.exchange_code", exchange)
    monkeypatch.setattr("app.vk.get_user_info", user_info)


def _vk_payload():
    return {
        "code": "auth-code",
        "redirectUri": "https://app.example/vk/callback",
        "codeVerifier": "a" * 43,
        "deviceId": "device-1",
    }


def test_vk_new_user(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200
    data = res.json()
    assert "accessToken" in data
    assert "refreshToken" in data
    assert data["tokenType"] == "bearer"

    db = SessionLocal()
    user = db.query(User).filter(User.vkId == "12345").first()
    db.close()

    assert user is not None
    assert user.username == "vk_12345"
    assert user.passwordHash is None
    assert user.email == "ivan@example.com"
    assert user.fullName == "Ivan Petrov"


def test_vk_existing_user_no_duplicate(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    client.post("/api/auth/vk", json=_vk_payload())
    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200

    db = SessionLocal()
    users = db.query(User).filter(User.vkId == "12345").all()
    db.close()
    assert len(users) == 1


def test_vk_full_name_handles_missing_name(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch, first_name="", last_name="", email=None)

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.vkId == "12345").first()
    db.close()
    assert user.fullName is None
    assert user.email is None


def test_vk_invalid_code(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    def fail(code, redirect_uri, code_verifier, device_id, state=None):
        raise VKAuthError("VK token exchange failed: invalid_grant")

    monkeypatch.setattr("app.vk.exchange_code", fail)

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 401
    assert res.json()["detail"] == "VK authentication failed"


def test_vk_not_configured(client, monkeypatch):
    monkeypatch.setattr("app.routers.auth.VK_CLIENT_ID", "")

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 503
    assert res.json()["detail"] == "VK sign-in not configured"


def test_vk_user_cannot_login_with_password(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    client.post("/api/auth/vk", json=_vk_payload())

    res = client.post(
        "/api/auth/login",
        json={"username": "vk_12345", "password": "whatever123"},
    )
    assert res.status_code == 401


def test_register_rejects_vk_username(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "vk_12345", "password": "secret123"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Username not allowed"
