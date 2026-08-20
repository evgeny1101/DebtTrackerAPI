import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text

from app.config import CORS_ORIGINS
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


app = FastAPI(title="DebtTracker API", lifespan=lifespan)
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
