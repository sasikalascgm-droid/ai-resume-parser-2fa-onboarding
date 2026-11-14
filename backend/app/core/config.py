import os
import re
from functools import lru_cache
from pathlib import Path
from typing import List, Optional
from urllib.parse import unquote

from cryptography.fernet import Fernet
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL, make_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent

PLACEHOLDER_PASSWORDS = {
    "",
    "PASSWORD",
    "YOUR_PASSWORD",
    "YOUR_POSTGRES_PASSWORD",
    "<PASSWORD>",
    "CHANGE_ME",
}

PLACEHOLDER_JWT_SECRETS = {
    "",
    "change-this-to-a-cryptographically-secure-256-bit-secret-key-in-prod",
    "changeme",
    "secret",
    "your-secret-key",
}

_BARE_PERCENT_RE = re.compile(r"%(?![0-9A-Fa-f]{2})")


def _decode_url_credential(component: str) -> str:
    """
    Decode a URL credential component using strict RFC 3986 unquote (never unquote_plus,
    so literal '+' characters are preserved as '+' and never turned into spaces).
    Bare '%' characters that are not part of a valid %XX hex escape are preserved as literal '%'.
    """
    escaped_bare_percent = _BARE_PERCENT_RE.sub("%25", component)
    return unquote(escaped_bare_percent)


def normalize_postgres_asyncpg_url(raw_url: str) -> str:
    """
    Normalize a postgresql+asyncpg:// URL using sqlalchemy.engine.URL.create() so that:
    1. Already percent-encoded credentials (%40, %23, %3A, %2F, %25, %2B, %20) are never double-encoded.
    2. Raw special characters (@, #, :, /, %, +, spaces) are RFC 3986 percent-encoded (spaces -> %20, '+' -> %2B).
    3. Literal '+' and spaces are never confused (quote_plus/unquote_plus are never used).
    """
    url = raw_url.strip()
    prefix = "postgresql+asyncpg://"
    if not url.startswith(prefix):
        return url

    remainder = url[len(prefix) :]
    if "@" not in remainder:
        return url

    # Split on the LAST '@' so raw '@' inside the password does not break host parsing
    userinfo, hostpart = remainder.rsplit("@", 1)
    if ":" not in userinfo:
        return url

    raw_user, raw_pass = userinfo.split(":", 1)
    decoded_user = _decode_url_credential(raw_user)
    decoded_pass = _decode_url_credential(raw_pass)

    # Parse host, port, and database from hostpart (e.g. "localhost:5432/edtech_onboarding")
    host_port, _, database = hostpart.partition("/")
    host_str, sep, port_str = host_port.partition(":")
    port_val: Optional[int] = int(port_str) if (sep and port_str.isdigit()) else None

    url_obj = URL.create(
        drivername="postgresql+asyncpg",
        username=decoded_user,
        password=decoded_pass,
        host=host_str or "localhost",
        port=port_val,
        database=database or None,
    )
    return url_obj.render_as_string(hide_password=False)


class Settings(BaseSettings):
    PROJECT_NAME: str = "SkillVerse EdTech - AI Resume Parser & 2FA Onboarding"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Database Configuration (never assumes default password 'postgres' and never falls back to SQLite)
    DATABASE_URL: str = (
        "postgresql+asyncpg://USERNAME:PASSWORD@localhost:5432/edtech_onboarding"
    )
    POSTGRES_USER: Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "edtech_onboarding"

    # JWT
    JWT_SECRET_KEY: str = "edtech-super-secret-jwt-key-minimum-32-bytes-long-2026"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    COOKIE_NAME: str = "edtech_access_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"

    # TOTP Encryption (Fernet 32-byte url-safe base64 key)
    TOTP_ENCRYPTION_KEY: str = "ZmDfcTF7_60GrrY167zsiPd67pEvs0aGOv2oasOM1Pg="
    TOTP_ISSUER_NAME: str = "SkillVerse EdTech"
    TOTP_VALID_WINDOW: int = 1

    # OTP Settings
    OTP_EXPIRE_MINUTES: int = 5
    OTP_MAX_ATTEMPTS: int = 5
    OTP_RESEND_COOLDOWN_SECONDS: int = 30
    REQUIRED_2FA_CHANNELS: str = "email,whatsapp,totp"

    # Email SMTP
    EMAIL_PROVIDER_MODE: str = "mock"  # "mock" or "smtp"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM: str = "noreply@skillverse-edtech.com"

    # WhatsApp Cloud API
    WHATSAPP_PROVIDER_MODE: str = "mock"  # "mock" or "cloud"
    WHATSAPP_ACCESS_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_API_VERSION: str = "v20.0"

    # Uploads & Frontend
    FRONTEND_URL: str = "http://localhost:5173"
    MAX_UPLOAD_SIZE_MB: int = 5
    UPLOAD_DIR: str = str(BASE_DIR / "uploads")

    # OCR Configuration & Resource Limits (Tesseract + PyMuPDF)
    TESSERACT_CMD: str = ""
    OCR_MAX_PAGES: int = 10
    OCR_RENDER_DPI: int = 200
    OCR_MAX_IMAGE_DIMENSION: int = 2500
    OCR_PAGE_TIMEOUT_SECONDS: int = 15
    OCR_TOTAL_TIMEOUT_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=(str(BASE_DIR.parent / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: str) -> str:
        cleaned = v.strip()
        if cleaned.lower() in PLACEHOLDER_JWT_SECRETS or len(cleaned) < 32:
            raise ValueError(
                "JWT_SECRET_KEY must be at least 32 characters long and must not be an unconfigured placeholder."
            )
        return cleaned

    @field_validator("TOTP_ENCRYPTION_KEY")
    @classmethod
    def validate_totp_encryption_key(cls, v: str) -> str:
        cleaned = v.strip()
        try:
            Fernet(cleaned.encode("utf-8"))
        except Exception as exc:
            raise ValueError(
                "TOTP_ENCRYPTION_KEY must be a valid 32-byte URL-safe base64-encoded Fernet key."
            ) from exc
        return cleaned

    @field_validator("EMAIL_PROVIDER_MODE")
    @classmethod
    def validate_email_provider_mode(cls, v: str) -> str:
        mode = v.strip().lower()
        if mode not in {"mock", "smtp"}:
            raise ValueError("EMAIL_PROVIDER_MODE must be either 'mock' or 'smtp'.")
        return mode

    @field_validator("WHATSAPP_PROVIDER_MODE")
    @classmethod
    def validate_whatsapp_provider_mode(cls, v: str) -> str:
        mode = v.strip().lower()
        if mode not in {"mock", "cloud"}:
            raise ValueError("WHATSAPP_PROVIDER_MODE must be either 'mock' or 'cloud'.")
        return mode

    @model_validator(mode="after")
    def build_and_normalize_database_url(self) -> "Settings":
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD is not None:
            url_obj = URL.create(
                drivername="postgresql+asyncpg",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PASSWORD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                database=self.POSTGRES_DB,
            )
            self.DATABASE_URL = url_obj.render_as_string(hide_password=False)
        else:
            self.DATABASE_URL = normalize_postgres_asyncpg_url(self.DATABASE_URL)

        if not self.DATABASE_URL.startswith("postgresql+asyncpg://"):
            raise ValueError(
                "DATABASE_URL must use the 'postgresql+asyncpg://' driver scheme. "
                "Silent fallback to SQLite is disabled."
            )
        return self

    @property
    def masked_database_url(self) -> str:
        return make_url(self.DATABASE_URL).render_as_string(hide_password=True)

    @property
    def required_channels_list(self) -> List[str]:
        return [
            ch.strip().lower()
            for ch in self.REQUIRED_2FA_CHANNELS.split(",")
            if ch.strip()
        ]

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @field_validator("COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, v: str) -> str:
        allowed = {"lax", "strict", "none"}
        low = v.lower().strip()
        return low if low in allowed else "lax"


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    return settings
