import logging
import secrets
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import schemas, vk
from app.auth import create_access_token, hash_password, hash_token, verify_password
from app.crud import users as users_crud
from app.config import REFRESH_TOKEN_EXPIRE_DAYS, VK_CLIENT_ID, api_path_prefix
from app.dependencies import get_current_user, get_db
from app.limiter import limiter
from app.models import RefreshToken, User

logger = logging.getLogger(__name__)

router = APIRouter(prefix=f"{api_path_prefix()}/api/auth", tags=["auth"])

_VK_USERNAME_PREFIX = "vk_"


def _vk_full_name(profile: dict) -> str | None:
    first_name = profile.get("first_name") or ""
    last_name = profile.get("last_name") or ""
    full_name = " ".join(part for part in (first_name, last_name) if part).strip()
    return full_name or None


def _next_vk_username(db: Session, vk_id: str) -> str:
    username = f"{_VK_USERNAME_PREFIX}{vk_id}"
    suffix = 1
    while db.query(User).filter(User.username == username).first() is not None:
        username = f"{_VK_USERNAME_PREFIX}{vk_id}_{suffix}"
        suffix += 1
    return username


def _refresh_vk_profile(user: User, profile: dict) -> None:
    email = profile.get("email")
    if isinstance(email, str) and email:
        user.email = email
    full_name = _vk_full_name(profile)
    if full_name:
        user.fullName = full_name


def _issue_tokens(db: Session, user_id: int) -> schemas.TokenResponse:
    now = int(time.time() * 1000)
    access_token = create_access_token(user_id)
    refresh_token_str = secrets.token_urlsafe(64)
    expires_at = now + REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60 * 1000

    refresh_token = RefreshToken(
        token=hash_token(refresh_token_str),
        userId=user_id,
        expiresAt=expires_at,
        createdAt=now,
    )
    db.add(refresh_token)
    db.commit()

    return schemas.TokenResponse(
        accessToken=access_token,
        refreshToken=refresh_token_str,
    )


@router.post("/register", response_model=schemas.TokenResponse, status_code=201)
@limiter.limit("5/minute")
def register(
    request: Request,
    data: schemas.UserRegister,
    db: Session = Depends(get_db),
):
    if data.username.startswith(_VK_USERNAME_PREFIX):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username not allowed",
        )

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

    return _issue_tokens(db, user.id)


@router.post("/login", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def login(
    request: Request,
    data: schemas.UserLogin,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not user.passwordHash or not verify_password(data.password, user.passwordHash):
        logger.warning("Login failed: username=%s", data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    return _issue_tokens(db, user.id)


@router.post("/vk", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def vk_auth(
    request: Request,
    data: schemas.VKAuthRequest,
    db: Session = Depends(get_db),
):
    if not VK_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="VK sign-in not configured",
        )

    try:
        token = vk.exchange_code(
            data.code,
            data.redirectUri,
            data.codeVerifier,
            data.deviceId,
            data.state,
        )
        profile = vk.get_user_info(token["access_token"])
    except vk.VKTransientError as exc:
        logger.warning("VK service unavailable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="VK service unavailable",
        ) from exc
    except vk.VKAuthError as exc:
        logger.warning("VK auth failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="VK authentication failed",
        ) from exc

    vk_id = str(token["user_id"])
    user = db.query(User).filter(User.vkId == vk_id).first()

    if user is None:
        user = User(
            username=_next_vk_username(db, vk_id),
            passwordHash=None,
            vkId=vk_id,
            email=profile.get("email"),
            fullName=_vk_full_name(profile),
            createdAt=int(time.time() * 1000),
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            user = db.query(User).filter(User.vkId == vk_id).first()
            if user is None:
                raise
    else:
        _refresh_vk_profile(user, profile)

    return _issue_tokens(db, user.id)


@router.post("/refresh", response_model=schemas.TokenResponse)
@limiter.limit("5/minute")
def refresh(
    request: Request,
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db),
):
    stored = (
        db.query(RefreshToken).filter(RefreshToken.token == hash_token(data.refreshToken)).first()
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

    return _issue_tokens(db, stored.userId)


@router.post("/logout", status_code=204)
@limiter.limit("10/minute")
def logout(
    request: Request,
    data: schemas.RefreshRequest,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
):
    stored = (
        db.query(RefreshToken).filter(RefreshToken.token == hash_token(data.refreshToken)).first()
    )
    if stored:
        db.delete(stored)
        db.commit()
    return None


@router.delete("/me", status_code=204)
@limiter.limit("5/minute")
def delete_account(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    users_crud.delete_user(db, current_user)
    return None
