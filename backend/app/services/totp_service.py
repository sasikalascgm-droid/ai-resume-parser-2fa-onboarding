import base64
import io
from datetime import datetime, timedelta, timezone

import pyotp
import qrcode
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    hash_otp,
    verify_otp_hash,
)
from app.models.otp_challenge import OTPChallenge
from app.models.user import User


class TOTPVerificationError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "INVALID_TOTP"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class TOTPService:
    """Service managing Browser/Authenticator App TOTP enrollment and verification."""

    async def setup_totp_for_user(self, db: AsyncSession, user: User) -> dict:
        settings = get_settings()

        # Always generate a fresh base32 secret so any previously exposed secret is invalidated
        secret = pyotp.random_base32()
        user.totp_secret_encrypted = encrypt_totp_secret(secret)
        user.is_totp_enabled = False

        await db.commit()
        await db.refresh(user)

        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=user.email,
            issuer_name=settings.TOTP_ISSUER_NAME,
        )
        qr_data_url = self._generate_qr_data_url(provisioning_uri)

        return {
            "qr_code_data_url": qr_data_url,
            "is_totp_enabled": user.is_totp_enabled,
        }

    async def verify_totp_code(self, db: AsyncSession, user: User, otp_code: str) -> bool:
        settings = get_settings()
        if not user.totp_secret_encrypted:
            raise TOTPVerificationError(
                "TOTP authenticator has not been set up for this account yet.",
                status_code=400,
                error_code="TOTP_NOT_SETUP",
            )

        try:
            secret = decrypt_totp_secret(user.totp_secret_encrypted)
        except Exception:
            raise TOTPVerificationError(
                "Stored TOTP secret could not be decrypted. Please re-run TOTP setup.",
                status_code=400,
                error_code="TOTP_SECRET_ERROR",
            )

        # Prevent replay of the exact same TOTP code within the validity window
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=90)
        stmt = select(OTPChallenge).where(
            OTPChallenge.user_id == user.id,
            OTPChallenge.channel == "totp",
            OTPChallenge.verified.is_(True),
            OTPChallenge.created_at >= window_start,
        )
        recent_challenges = (await db.execute(stmt)).scalars().all()
        for ch in recent_challenges:
            if verify_otp_hash(otp_code, ch.otp_hash, salt=f"{user.id}:totp"):
                raise TOTPVerificationError(
                    "This authenticator code has already been used. Please wait for the next code.",
                    status_code=400,
                    error_code="OTP_REPLAY_DETECTED",
                )

        totp = pyotp.TOTP(secret)
        is_valid = totp.verify(otp_code, valid_window=settings.TOTP_VALID_WINDOW)
        if not is_valid:
            raise TOTPVerificationError(
                "Invalid or expired authenticator code. Please check your authenticator app and try again.",
                status_code=400,
                error_code="INVALID_TOTP",
            )

        # Record used TOTP code to prevent replay
        used_record = OTPChallenge(
            user_id=user.id,
            channel="totp",
            otp_hash=hash_otp(otp_code, salt=f"{user.id}:totp"),
            expires_at=now + timedelta(seconds=90),
            attempts=1,
            verified=True,
        )
        db.add(used_record)
        user.is_totp_enabled = True
        return True

    def _generate_qr_data_url(self, provisioning_uri: str) -> str:
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return f"data:image/png;base64,{encoded}"


totp_service = TOTPService()
