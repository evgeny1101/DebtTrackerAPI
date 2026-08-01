import os

TEST_DB_PATH = "/tmp/debts_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH}"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing"

import pytest
from fastapi.testclient import TestClient
from app.database import Base, engine
from app.main import app
from app.limiter import limiter

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
    try:
        os.unlink(TEST_DB_PATH)
    except OSError:
        pass


@pytest.fixture
def client():
    return TestClient(app)
