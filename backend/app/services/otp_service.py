from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import generate_secure_otp, hash_otp, verify_otp_hash
from app.models.otp_challenge import OTPChallenge
from app.models.user import User
from app.schemas.auth import SendOTPResponse, VerificationStatusResponse
from app.services.email_service import email_service
from app.services.token_service import token_service
from app.services.totp_service import totp_service
from app.services.whatsapp_service import whatsapp_service


class OTPChallengeError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "OTP_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def _ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        return f"{local[0]}***@{domain}"
    return f"{local[:2]}***{local[-1]}@{domain}"


def _mask_phone(phone: str) -> str:
    if len(phone) <= 4:
        return "****"
    return f"{'*' * (len(phone) - 4)}{phone[-4:]}"


class OTPService:
    """Manages multi-channel OTP generation, cooldowns, attempt limits, and account activation."""

    async def get_target_user(
        self,
        db: AsyncSession,
        user_id: Optional[str] = None,
        email: Optional[str] = None,
    ) -> User:
        user: Optional[User] = None
        if user_id and user_id != "latest":
            stmt = select(User).where(User.id == user_id)
            user = (await db.execute(stmt)).scalar_one_or_none()

        if user is None and email:
            stmt = select(User).where(func.lower(User.email) == email.strip().lower())
            user = (await db.execute(stmt)).scalar_one_or_none()

        if user is None and (user_id == "latest" or (not user_id and not email)):
            stmt = select(User).order_by(User.created_at.desc()).limit(1)
            user = (await db.execute(stmt)).scalar_one_or_none()

        if not user:
            raise OTPChallengeError(
                "User account not found. Please register a candidate account first.",
                status_code=404,
                error_code="USER_NOT_FOUND",
            )
        return user

    def evaluate_activation_policy(self, user: User) -> bool:
        """Check whether all configured 2FA channels are verified and activate user if satisfied."""
        settings = get_settings()
        required = settings.required_channels_list
        channel_state = {
            "email": bool(user.is_email_verified),
            "whatsapp": bool(user.is_whatsapp_verified),
            "totp": bool(user.is_totp_enabled),
        }
        all_satisfied = all(channel_state.get(ch, False) for ch in required)
        if all_satisfied:
            user.is_active = True
        return all_satisfied

    async def send_otp(
        self,
        db: AsyncSession,
        user: User,
        channel: str,
        bypass_cooldown: bool = False,
    ) -> SendOTPResponse:
        settings = get_settings()
        now = datetime.now(timezone.utc)

        # Check resend cooldown on the most recent challenge for this channel
        if not bypass_cooldown and settings.OTP_RESEND_COOLDOWN_SECONDS > 0:
            latest_stmt = (
                select(OTPChallenge)
                .where(
                    OTPChallenge.user_id == user.id,
                    OTPChallenge.channel == channel,
                )
                .order_by(OTPChallenge.created_at.desc())
                .limit(1)
            )
            latest_challenge = (await db.execute(latest_stmt)).scalar_one_or_none()
            if latest_challenge is not None:
                elapsed = (now - _ensure_utc(latest_challenge.created_at)).total_seconds()
                if elapsed < settings.OTP_RESEND_COOLDOWN_SECONDS:
                    remaining = int(settings.OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
                    raise OTPChallengeError(
                        f"Please wait {remaining} seconds before requesting another OTP on {channel}.",
                        status_code=429,
                        error_code="RESEND_COOLDOWN_ACTIVE",
                    )

        otp_code = generate_secure_otp(6)
        otp_hashed = hash_otp(otp_code, salt=f"{user.id}:{channel}")
        expires_at = now + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        challenge = OTPChallenge(
            user_id=user.id,
            channel=channel,
            otp_hash=otp_hashed,
            expires_at=expires_at,
            attempts=0,
            verified=False,
        )
        db.add(challenge)
        await db.flush()

        if channel == "email":
            delivery = await email_service.send_otp_email(
                recipient_email=user.email,
                full_name=user.full_name,
                otp_code=otp_code,
            )
            masked = _mask_email(user.email)
        elif channel == "whatsapp":
            delivery = await whatsapp_service.send_otp_whatsapp(
                phone_number=user.phone,
                otp_code=otp_code,
            )
            masked = _mask_phone(user.phone)
        else:
            raise OTPChallengeError(
                f"Unsupported OTP channel: {channel}",
                status_code=400,
                error_code="INVALID_CHANNEL",
            )

        await db.commit()

        return SendOTPResponse(
            success=True,
            channel=channel,
            delivery_mode=delivery.delivery_mode,
            delivered=delivery.delivered,
            is_simulated=delivery.is_simulated,
            message=delivery.message,
            expires_in_seconds=settings.OTP_EXPIRE_MINUTES * 60,
            cooldown_seconds=settings.OTP_RESEND_COOLDOWN_SECONDS,
            recipient_masked=masked,
            dev_otp_preview=delivery.dev_otp_preview,
        )

    async def verify_channel_otp(
        self,
        db: AsyncSession,
        user: User,
        channel: str,
        otp_code: str,
    ) -> VerificationStatusResponse:
        settings = get_settings()
        now = datetime.now(timezone.utc)

        stmt = (
            select(OTPChallenge)
            .where(
                OTPChallenge.user_id == user.id,
                OTPChallenge.channel == channel,
            )
            .order_by(OTPChallenge.created_at.desc())
            .limit(1)
        )
        challenge = (await db.execute(stmt)).scalar_one_or_none()
        if challenge is None:
            raise OTPChallengeError(
                f"No OTP challenge found for {channel}. Please request an OTP first.",
                status_code=400,
                error_code="OTP_NOT_FOUND",
            )

        if challenge.verified:
            raise OTPChallengeError(
                "This OTP has already been verified and cannot be reused.",
                status_code=400,
                error_code="OTP_ALREADY_USED",
            )

        if challenge.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise OTPChallengeError(
                "Maximum verification attempts exceeded for this OTP. Please request a new code.",
                status_code=429,
                error_code="MAX_ATTEMPTS_EXCEEDED",
            )

        if now > _ensure_utc(challenge.expires_at):
            raise OTPChallengeError(
                "This OTP has expired. Please request a new verification code.",
                status_code=400,
                error_code="OTP_EXPIRED",
            )

        is_valid = verify_otp_hash(otp_code, challenge.otp_hash, salt=f"{user.id}:{channel}")
        if not is_valid:
            challenge.attempts += 1
            await db.commit()
            remaining = max(0, settings.OTP_MAX_ATTEMPTS - challenge.attempts)
            if remaining == 0:
                raise OTPChallengeError(
                    "Invalid OTP. Maximum verification attempts reached; please request a new OTP.",
                    status_code=429,
                    error_code="MAX_ATTEMPTS_EXCEEDED",
                )
            raise OTPChallengeError(
                f"Invalid OTP code. {remaining} attempt(s) remaining.",
                status_code=400,
                error_code="INVALID_OTP",
            )

        # Mark verified
        challenge.attempts += 1
        challenge.verified = True

        if channel == "email":
            user.is_email_verified = True
        elif channel == "whatsapp":
            user.is_whatsapp_verified = True

        activated = self.evaluate_activation_policy(user)
        await db.commit()
        await db.refresh(user)

        token: Optional[str] = None
        if activated and user.is_active:
            token = token_service.issue_token_for_user(user)

        return VerificationStatusResponse(
            success=True,
            message=(
                f"{channel.capitalize()} verified! All required 2FA channels are complete and your account is now active."
                if user.is_active
                else f"{channel.capitalize()} OTP verified successfully."
            ),
            user_id=user.id,
            channel_verified=channel,
            is_email_verified=user.is_email_verified,
            is_whatsapp_verified=user.is_whatsapp_verified,
            is_totp_enabled=user.is_totp_enabled,
            is_active=user.is_active,
            required_channels=settings.required_channels_list,
            access_token=token,
            token_type="bearer" if token else None,
        )

    async def verify_totp_and_update_state(
        self,
        db: AsyncSession,
        user: User,
        otp_code: str,
    ) -> VerificationStatusResponse:
        settings = get_settings()
        await totp_service.verify_totp_code(db=db, user=user, otp_code=otp_code)
        activated = self.evaluate_activation_policy(user)
        await db.commit()
        await db.refresh(user)

        token: Optional[str] = None
        if activated and user.is_active:
            token = token_service.issue_token_for_user(user)

        return VerificationStatusResponse(
            success=True,
            message=(
                "Authenticator TOTP verified! All required 2FA channels are complete and your account is now active."
                if user.is_active
                else "Authenticator TOTP verified and enabled successfully."
            ),
            user_id=user.id,
            channel_verified="totp",
            is_email_verified=user.is_email_verified,
            is_whatsapp_verified=user.is_whatsapp_verified,
            is_totp_enabled=user.is_totp_enabled,
            is_active=user.is_active,
            required_channels=settings.required_channels_list,
            access_token=token,
            token_type="bearer" if token else None,
        )


otp_service = OTPService()
