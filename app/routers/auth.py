import logging
import time
import secrets
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app import schemas
from app.dependencies import get_db, get_current_user
from app.auth import hash_password, verify_password, create_access_token
from app.config import REFRESH_TOKEN_EXPIRE_DAYS
from app.models import User, RefreshToken
from app.limiter import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
@limiter.limit("5/minute")
def register(
    request: Request,
    data: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    now = int(time.time() * 1000)
    user = User(
        username=data.username,
        passwordHash=hash_password(data.password),
        createdAt=now,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    access_token = create_access_token(user.id)
    refresh_token_str = secrets.token_urlsafe(64)
    expires_at = now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000

    refresh_token = RefreshToken(
        token=refresh_token_str,
        userId=user.id,
        expiresAt=expires_at,
        createdAt=now,
    )
    db.add(refresh_token)
    db.commit()

    return schemas.TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token_str,
    )


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    data: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.passwordHash):
        logger.warning("Login failed: username=%s", data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    now = int(time.time() * 1000)
    access_token = create_access_token(user.id)
    refresh_token_str = secrets.token_urlsafe(64)
    expires_at = now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000

    refresh_token = RefreshToken(
        token=refresh_token_str,
        userId=user.id,
        expiresAt=expires_at,
        createdAt=now,
    )
    db.add(refresh_token)
    db.commit()

    return schemas.TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token_str,
    )


@router.post("/refresh", response_model=schemas.TokenResponse)
def refresh(
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db),
):
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == data.refreshToken)
        .first()
    )
    if not stored:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    now = int(time.time() * 1000)
    if stored.expiresAt < now:
        db.delete(stored)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token expired",
        )

    db.delete(stored)

    access_token = create_access_token(stored.userId)
    refresh_token_str = secrets.token_urlsafe(64)
    expires_at = now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000

    new_refresh = RefreshToken(
        token=refresh_token_str,
        userId=stored.userId,
        expiresAt=expires_at,
        createdAt=now,
    )
    db.add(new_refresh)
    db.commit()

    return schemas.TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token_str,
    )


@router.post("/logout", status_code=204)
def logout(
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    stored = (
        db.query(RefreshToken)
        .filter(RefreshToken.token == data.refreshToken)
        .first()
    )
    if stored:
        db.delete(stored)
        db.commit()
    return None
