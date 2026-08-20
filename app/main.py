import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import CORS_ORIGINS, ENABLE_DOCS
from app.database import Base, engine
from app.limiter import limiter
from app.logging import setup_logging
from app.routers import auth, debts, payments


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    Base.metadata.create_all(bind=engine)

    now = int(time.time() * 1000)
    with engine.begin() as conn:
        conn.execute(
            text('DELETE FROM refresh_tokens WHERE "expiresAt" < :now'),
            {"now": now},
        )

    yield


app = FastAPI(
    title="DebtTracker API",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

MAX_BODY_BYTES = 1_048_576


@app.middleware("http")
async def limit_body_size(request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            size = int(content_length)
        except ValueError:
            size = 0
        if size > MAX_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Payload too large"})
    return await call_next(request)


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(debts.router)
app.include_router(payments.router)


@app.get("/health")
def health():
    return {"status": "ok"}
