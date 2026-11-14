import base64
import hashlib
import io
import socket
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple

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

_NTP_HOSTS: Tuple[str, ...] = (
    "time.google.com",
    "pool.ntp.org",
    "time.cloudflare.com",
    "time.windows.com",
)
_NTP_CACHE_TTL_SECONDS = 300.0
_cached_ntp_offset_seconds: Optional[float] = None
_cached_ntp_monotonic: float = 0.0


def _query_ntp_offset_seconds(timeout: float = 1.5) -> Optional[float]:
    """
    Query standard NTP servers (UDP port 123) and return (ntp_epoch - local_epoch) in seconds.
    Cached for 5 minutes so TOTP verification remains fast even when the host OS clock is skewed.
    """
    global _cached_ntp_offset_seconds, _cached_ntp_monotonic
    now_mono = time.monotonic()
    if (
        _cached_ntp_offset_seconds is not None
        and (now_mono - _cached_ntp_monotonic) < _NTP_CACHE_TTL_SECONDS
    ):
        return _cached_ntp_offset_seconds

    ntp_packet = b"\x1b" + 47 * b"\0"
    for host in _NTP_HOSTS:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(timeout)
                t_send = time.time()
                sock.sendto(ntp_packet, (host, 123))
                data, _ = sock.recvfrom(1024)
                t_recv = time.time()
            if data and len(data) >= 48:
                ntp_transmit_sec = struct.unpack("!12I", data[:48])[10] - 2208988800
                ntp_transmit_frac = struct.unpack("!12I", data[:48])[11] / float(2**32)
                ntp_epoch = ntp_transmit_sec + ntp_transmit_frac
                local_midpoint = (t_send + t_recv) / 2.0
                offset = ntp_epoch - local_midpoint
                _cached_ntp_offset_seconds = offset
                _cached_ntp_monotonic = now_mono
                return offset
        except Exception:
            continue
    return _cached_ntp_offset_seconds


def _get_verification_reference_times() -> List[datetime]:
    """
    Return reference UTC datetimes for RFC 6238 TOTP verification:
    1. Authoritative NTP-synchronized UTC time (matches Google Authenticator on mobile devices
       even when the local Windows host clock is skewed by hours or AM/PM).
    2. Local system UTC time (matches local clock / unit test generators).
    """
    sys_now = datetime.now(timezone.utc)
    ref_times: List[datetime] = []

    offset = _query_ntp_offset_seconds()
    if offset is not None:
        ntp_now = datetime.fromtimestamp(time.time() + offset, tz=timezone.utc)
        ref_times.append(ntp_now)

    ref_times.append(sys_now)
    return ref_times


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

        totp = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1)
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
        cleaned_code = (otp_code or "").strip()

        if not user.totp_secret_encrypted:
            raise TOTPVerificationError(
                "TOTP authenticator has not been set up for this account yet.",
                status_code=400,
                error_code="TOTP_NOT_SETUP",
            )

        try:
            secret = decrypt_totp_secret(user.totp_secret_encrypted).strip()
        except Exception:
            raise TOTPVerificationError(
                "Stored TOTP secret could not be decrypted. Please re-run TOTP setup.",
                status_code=400,
                error_code="TOTP_SECRET_ERROR",
            )

        # Prevent replay of the exact same TOTP code within the active 90-second validity window
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(seconds=90)
        stmt = select(OTPChallenge).where(
            OTPChallenge.user_id == user.id,
            OTPChallenge.channel == "totp",
            OTPChallenge.verified.is_(True),
            OTPChallenge.created_at >= window_start,
            OTPChallenge.expires_at >= now,
        )
        recent_challenges = (await db.execute(stmt)).scalars().all()
        for ch in recent_challenges:
            if verify_otp_hash(cleaned_code, ch.otp_hash, salt=f"{user.id}:totp"):
                raise TOTPVerificationError(
                    "This authenticator code has already been used. Please wait for the next code.",
                    status_code=400,
                    error_code="OTP_REPLAY_DETECTED",
                )

        totp = pyotp.TOTP(secret, digits=6, interval=30, digest=hashlib.sha1)
        valid_window = max(1, int(settings.TOTP_VALID_WINDOW))
        is_valid = any(
            totp.verify(cleaned_code, for_time=ref_time, valid_window=valid_window)
            for ref_time in _get_verification_reference_times()
        )
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
            otp_hash=hash_otp(cleaned_code, salt=f"{user.id}:totp"),
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
