import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from app import vk
from app.database import SessionLocal
from app.models import User
from app.vk import VK_TOKEN_URL, VK_USER_INFO_URL, VKAuthError, VKTransientError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


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


class _FakeResponse:
    def __init__(self, status_code=200, body='{"error": "server_error"}'):
        self.status_code = status_code
        self._body = body

    def json(self):
        return json.loads(self._body)


class _BrokenJsonResponse:
    status_code = 200

    def json(self):
        raise json.JSONDecodeError("bad", "doc", 0)


def _run_alembic(db_path, *args):
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite:///{db_path}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=PROJECT_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )


def _users_columns(db_path):
    conn = sqlite3.connect(db_path)
    rows = conn.execute("PRAGMA table_info(users)").fetchall()
    conn.close()
    return {row[1]: row for row in rows}


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


def test_vk_transient_error_returns_502(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    def fail(code, redirect_uri, code_verifier, device_id, state=None):
        raise VKTransientError("VK token request failed")

    monkeypatch.setattr("app.vk.exchange_code", fail)

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 502
    assert res.json()["detail"] == "VK service unavailable"


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


def test_vk_existing_user_updates_profile(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch, first_name="Ivan", last_name="Petrov", email="ivan@example.com")

    client.post("/api/auth/vk", json=_vk_payload())

    _mock_vk(monkeypatch, first_name="Ivan", last_name="Sidorov", email="new@example.com")
    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.vkId == "12345").first()
    db.close()
    assert user.email == "new@example.com"
    assert user.fullName == "Ivan Sidorov"


def test_vk_existing_user_preserves_profile_on_empty(client, monkeypatch):
    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch, first_name="Ivan", last_name="Petrov", email="ivan@example.com")

    client.post("/api/auth/vk", json=_vk_payload())

    _mock_vk(monkeypatch, first_name="", last_name="", email=None)
    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.vkId == "12345").first()
    db.close()
    assert user.email == "ivan@example.com"
    assert user.fullName == "Ivan Petrov"


def test_vk_username_collision_uses_suffix(client, monkeypatch):
    from app.auth import hash_password

    _enable_vk(monkeypatch)
    _mock_vk(monkeypatch)

    db = SessionLocal()
    db.add(
        User(
            username="vk_12345",
            passwordHash=hash_password("secret123"),
            createdAt=int(time.time() * 1000),
        )
    )
    db.commit()
    db.close()

    res = client.post("/api/auth/vk", json=_vk_payload())
    assert res.status_code == 200

    db = SessionLocal()
    user = db.query(User).filter(User.vkId == "12345").first()
    db.close()
    assert user is not None
    assert user.username == "vk_12345_1"


def test_register_rejects_vk_username(client):
    res = client.post(
        "/api/auth/register",
        json={"username": "vk_12345", "password": "secret123"},
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Username not allowed"


def test_exchange_code_success(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        assert url == VK_TOKEN_URL
        return _FakeResponse(200, json.dumps({"access_token": "tok", "user_id": 42}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    payload = vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")
    assert payload["access_token"] == "tok"
    assert payload["user_id"] == 42


def test_exchange_code_malformed_json(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _BrokenJsonResponse()

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_exchange_code_network_error(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        raise httpx.ConnectError("boom")

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKTransientError):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_exchange_code_server_error(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(500, json.dumps({"error": "server_error"}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKTransientError):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_exchange_code_missing_access_token(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(200, json.dumps({"user_id": 42}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_exchange_code_error_with_http_200(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(
            200, json.dumps({"error": "invalid_client", "error_description": "app not found"})
        )

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError, match="invalid_client: app not found"):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_exchange_code_missing_access_token_lists_fields(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(200, json.dumps({"state": "s" * 32}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError, match="VK response fields.*state"):
        vk.exchange_code("code", "https://app.example/cb", "a" * 43, "dev1")


def test_get_user_info_success(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        assert url == VK_USER_INFO_URL
        return _FakeResponse(
            200,
            json.dumps(
                {
                    "user": {
                        "user_id": "42",
                        "first_name": "Ivan",
                        "last_name": "Petrov",
                        "email": "ivan@example.com",
                    }
                }
            ),
        )

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    user = vk.get_user_info("tok")
    assert user["first_name"] == "Ivan"
    assert user["email"] == "ivan@example.com"


def test_get_user_info_invalid_user_type(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(200, json.dumps({"user": "not-a-dict"}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError):
        vk.get_user_info("tok")


def test_get_user_info_error_response(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(400, json.dumps({"error": "invalid_token"}))

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError):
        vk.get_user_info("tok")


def test_get_user_info_error_with_http_200(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(
            200, json.dumps({"error": "invalid_token", "error_description": "expired"})
        )

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError, match="invalid_token: expired"):
        vk.get_user_info("tok")


def test_get_user_info_invalid_field_type(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(
            200,
            json.dumps(
                {"user": {"user_id": "42", "first_name": 123, "last_name": "", "email": None}}
            ),
        )

    monkeypatch.setattr("app.vk.httpx.post", fake_post)
    monkeypatch.setattr("app.vk.VK_CLIENT_ID", "test-client-id")

    with pytest.raises(VKAuthError):
        vk.get_user_info("tok")


def test_migration_003_upgrade_downgrade(tmp_path):
    db = tmp_path / "mig.db"
    result = _run_alembic(db, "upgrade", "head")
    assert result.returncode == 0, result.stderr

    cols = _users_columns(db)
    assert {"vkId", "email", "fullName"} <= set(cols)
    assert cols["passwordHash"][3] == 0  # nullable

    result = _run_alembic(db, "downgrade", "002")
    assert result.returncode == 0, result.stderr

    cols = _users_columns(db)
    assert "vkId" not in cols
    assert cols["passwordHash"][3] == 1  # NOT NULL restored


def test_migration_003_downgrade_blocks_null_password(tmp_path):
    db = tmp_path / "mig.db"
    result = _run_alembic(db, "upgrade", "head")
    assert result.returncode == 0, result.stderr

    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO users (username, passwordHash, createdAt) VALUES ('vk_1', NULL, 0)")
    conn.commit()
    conn.close()

    result = _run_alembic(db, "downgrade", "002")
    assert result.returncode != 0

    cols = _users_columns(db)
    assert "vkId" in cols
    assert cols["passwordHash"][3] == 0  # no partial rollback
