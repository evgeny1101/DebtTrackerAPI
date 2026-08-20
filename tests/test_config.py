import pytest

from app import config


@pytest.fixture(autouse=True)
def restore_config():
    yield
    config.ENVIRONMENT = "development"


def test_production_requires_strong_jwt_secret():
    config.ENVIRONMENT = "production"
    config.JWT_SECRET = "dev-secret-change-me"
    config.API_PATH_PREFIX = "a" * 40
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        config.validate_production_config()


def test_production_requires_api_path_prefix():
    config.ENVIRONMENT = "production"
    config.JWT_SECRET = "x" * 40
    config.API_PATH_PREFIX = ""
    with pytest.raises(RuntimeError, match="API_PATH_PREFIX"):
        config.validate_production_config()


def test_production_rejects_short_prefix():
    config.ENVIRONMENT = "production"
    config.JWT_SECRET = "x" * 40
    config.API_PATH_PREFIX = "short"
    with pytest.raises(RuntimeError, match="API_PATH_PREFIX"):
        config.validate_production_config()


def test_production_accepts_valid_config():
    config.ENVIRONMENT = "production"
    config.JWT_SECRET = "x" * 40
    config.API_PATH_PREFIX = "y" * 40
    config.validate_production_config()


def test_development_skips_validation():
    config.ENVIRONMENT = "development"
    config.JWT_SECRET = "dev-secret-change-me"
    config.API_PATH_PREFIX = ""
    config.validate_production_config()


def test_api_path_prefix_helper():
    config.API_PATH_PREFIX = "s3cr3t"
    assert config.api_path_prefix() == "/s3cr3t"
    config.API_PATH_PREFIX = ""
    assert config.api_path_prefix() == ""
