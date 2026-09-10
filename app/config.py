import os

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./debts.db")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "30"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
API_PATH_PREFIX = os.getenv("API_PATH_PREFIX", "").strip("/")
VK_CLIENT_ID = os.getenv("VK_CLIENT_ID", "").strip()
_ENABLE_DOCS = os.getenv("ENABLE_DOCS", "").strip()
if not _ENABLE_DOCS:
    _ENABLE_DOCS = "true" if ENVIRONMENT != "production" else "false"
ENABLE_DOCS = _ENABLE_DOCS.lower() == "true"

DEFAULT_JWT_SECRET = "dev-secret-change-me"


def api_path_prefix() -> str:
    return f"/{API_PATH_PREFIX}" if API_PATH_PREFIX else ""


def validate_production_config() -> None:
    if ENVIRONMENT != "production":
        return

    errors: list[str] = []
    if not JWT_SECRET or JWT_SECRET == DEFAULT_JWT_SECRET or len(JWT_SECRET) < 32:
        errors.append(
            "JWT_SECRET must be set to a strong random value (>= 32 chars). "
            "Generate with: openssl rand -hex 32"
        )
    if not API_PATH_PREFIX or len(API_PATH_PREFIX) < 32:
        errors.append(
            "API_PATH_PREFIX must be set to a long random string (>= 32 chars). "
            "Generate with: openssl rand -base64 32"
        )
    if errors:
        raise RuntimeError("Production configuration error:\n- " + "\n- ".join(errors))


validate_production_config()
