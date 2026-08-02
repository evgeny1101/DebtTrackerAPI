import contextlib
import os

TEST_DB_PATH = "/tmp/debts_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.limiter import limiter
from app.main import app

limiter._auto_check = False
limiter.enabled = False


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session", autouse=True)
def cleanup_temp_db():
    yield
    with contextlib.suppress(OSError):
        os.unlink(TEST_DB_PATH)


@pytest.fixture
def client():
    return TestClient(app)
