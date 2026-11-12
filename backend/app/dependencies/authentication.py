from typing import Optional
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.models.user import User
from app.services.token_service import TokenAuthError, token_service

bearer_scheme = HTTPBearer(auto_error=False)


def extract_token_from_request(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = None,
) -> str:
    """Extract JWT from Authorization Bearer header or HttpOnly cookie."""
    if credentials and credentials.scheme.lower() == "bearer" and credentials.credentials:
        return credentials.credentials

    settings = get_settings()
    cookie_token = request.cookies.get(settings.COOKIE_NAME)
    if cookie_token:
        return cookie_token

    raise TokenAuthError(
        "Authentication credentials were not provided.",
        status_code=401,
        error_code="NOT_AUTHENTICATED",
    )


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT and retrieve the authenticated User record."""
    token = extract_token_from_request(request, credentials)
    payload = token_service.verify_and_decode_token(token)
    user_id = str(payload.get("sub"))

    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user is None:
        raise TokenAuthError(
            "Authenticated user no longer exists.",
            status_code=401,
            error_code="USER_NOT_FOUND",
        )
    return user


async def get_optional_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    """Retrieve the authenticated User if a valid JWT Bearer token or cookie is provided; otherwise None."""
    try:
        token = extract_token_from_request(request, credentials)
        payload = token_service.verify_and_decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            return None
        stmt = select(User).where(User.id == str(user_id))
        return (await db.execute(stmt)).scalar_one_or_none()
    except Exception:
        return None


async def get_current_verified_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Ensure the user is both active and satisfies the required 2FA verification policy."""
    settings = get_settings()
    required = settings.required_channels_list
    channel_map = {
        "email": user.is_email_verified,
        "whatsapp": user.is_whatsapp_verified,
        "totp": user.is_totp_enabled,
    }
    missing = [ch for ch in required if not channel_map.get(ch, False)]

    if not user.is_active or missing:
        raise TokenAuthError(
            "Your account is not active yet. Please complete all required 2FA verifications.",
            status_code=403,
            error_code="ACCOUNT_INACTIVE_OR_UNVERIFIED",
        )
    return user
