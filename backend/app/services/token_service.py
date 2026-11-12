from datetime import timedelta
from typing import Any, Dict, Optional, Set

import jwt
from fastapi import Response

from app.core.config import get_settings
from app.core.security import create_access_token, decode_access_token
from app.models.user import User


class TokenAuthError(Exception):
    def __init__(self, message: str, status_code: int = 401, error_code: str = "UNAUTHORIZED"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class TokenService:
    """Manages JWT lifecycle, revocation on logout, and secure HttpOnly cookies."""

    def __init__(self) -> None:
        self._revoked_jtis: Set[str] = set()

    def issue_token_for_user(
        self,
        user: User,
        expires_delta: Optional[timedelta] = None,
    ) -> str:
        extra_claims = {
            "email": user.email,
            "is_active": user.is_active,
        }
        return create_access_token(
            subject=user.id,
            extra_claims=extra_claims,
            expires_delta=expires_delta,
        )

    def verify_and_decode_token(self, token: str) -> Dict[str, Any]:
        try:
            payload = decode_access_token(token)
        except jwt.ExpiredSignatureError:
            raise TokenAuthError(
                "Authentication session has expired. Please log in again.",
                status_code=401,
                error_code="TOKEN_EXPIRED",
            )
        except jwt.InvalidTokenError:
            raise TokenAuthError(
                "Invalid authentication token.",
                status_code=401,
                error_code="INVALID_TOKEN",
            )

        jti = payload.get("jti")
        if jti and jti in self._revoked_jtis:
            raise TokenAuthError(
                "Authentication token has been revoked. Please log in again.",
                status_code=401,
                error_code="TOKEN_REVOKED",
            )

        sub = payload.get("sub")
        if not sub:
            raise TokenAuthError(
                "Token is missing subject identifier.",
                status_code=401,
                error_code="INVALID_TOKEN_PAYLOAD",
            )
        return payload

    def revoke_token(self, token: str) -> None:
        try:
            payload = decode_access_token(token)
            jti = payload.get("jti")
            if jti:
                self._revoked_jtis.add(jti)
        except Exception:
            pass

    def set_auth_cookie(self, response: Response, token: str) -> None:
        settings = get_settings()
        max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        response.set_cookie(
            key=settings.COOKIE_NAME,
            value=token,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
            max_age=max_age,
            path="/",
        )

    def clear_auth_cookie(self, response: Response) -> None:
        settings = get_settings()
        response.delete_cookie(
            key=settings.COOKIE_NAME,
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,  # type: ignore[arg-type]
            path="/",
        )


token_service = TokenService()
