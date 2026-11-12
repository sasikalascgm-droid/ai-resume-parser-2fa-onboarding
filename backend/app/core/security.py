import base64
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from cryptography.fernet import Fernet
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings

# Argon2id password hasher via pwdlib
password_hasher = PasswordHash((Argon2Hasher(),))


def hash_password(password: str) -> str:
    """Hash a plain-text password using Argon2id."""
    return password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against an Argon2id hash."""
    try:
        return password_hasher.verify(plain_password, hashed_password)
    except Exception:
        return False


def generate_secure_otp(length: int = 6) -> str:
    """Generate a cryptographically secure numeric OTP."""
    upper = 10**length
    number = secrets.randbelow(upper)
    return f"{number:0{length}d}"


def hash_otp(otp: str, salt: str = "") -> str:
    """Hash an OTP using HMAC-SHA256 with the application secret key."""
    settings = get_settings()
    key = f"{settings.JWT_SECRET_KEY}:{salt}".encode("utf-8")
    return hmac.new(key, otp.encode("utf-8"), hashlib.sha256).hexdigest()


def verify_otp_hash(otp: str, expected_hash: str, salt: str = "") -> bool:
    """Constant-time verification of an OTP against its stored hash."""
    computed = hash_otp(otp, salt=salt)
    return hmac.compare_digest(computed, expected_hash)


def _get_fernet() -> Fernet:
    settings = get_settings()
    raw_key = settings.TOTP_ENCRYPTION_KEY.strip()
    try:
        return Fernet(raw_key.encode("utf-8"))
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw_key.encode("utf-8")).digest())
        return Fernet(derived)


def encrypt_totp_secret(secret: str) -> str:
    """Encrypt a TOTP base32 secret at rest using Fernet (AES-128-CBC + HMAC)."""
    f = _get_fernet()
    return f.encrypt(secret.encode("utf-8")).decode("utf-8")


def decrypt_totp_secret(encrypted_secret: str) -> str:
    """Decrypt an encrypted TOTP base32 secret."""
    f = _get_fernet()
    return f.decrypt(encrypted_secret.encode("utf-8")).decode("utf-8")


def create_access_token(
    subject: str,
    extra_claims: Optional[Dict[str, Any]] = None,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: Dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": secrets.token_hex(16),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT access token."""
    settings = get_settings()
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
