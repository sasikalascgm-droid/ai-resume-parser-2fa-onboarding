from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.models.user_resume import UserResume
from app.schemas.user import UserRegisterRequest, UserRegisterResponse


class RegistrationError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "REGISTRATION_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class RegistrationService:
    """Handles candidate registration, Argon2id hashing, and staged inactive account creation."""

    async def register_candidate(
        self, db: AsyncSession, payload: UserRegisterRequest
    ) -> UserRegisterResponse:
        settings = get_settings()

        # Check duplicate email
        email_stmt = select(User).where(func.lower(User.email) == payload.email.lower())
        existing_email = (await db.execute(email_stmt)).scalar_one_or_none()
        if existing_email is not None:
            raise RegistrationError(
                "An account with this email address is already registered.",
                status_code=409,
                error_code="DUPLICATE_EMAIL",
            )

        # Check duplicate phone
        phone_stmt = select(User).where(User.phone == payload.phone)
        existing_phone = (await db.execute(phone_stmt)).scalar_one_or_none()
        if existing_phone is not None:
            raise RegistrationError(
                "An account with this phone number is already registered.",
                status_code=409,
                error_code="DUPLICATE_PHONE",
            )

        # Hash password with Argon2id
        hashed_pw = hash_password(payload.password)

        # Create staged, inactive user account
        new_user = User(
            full_name=payload.full_name,
            email=payload.email.lower(),
            phone=payload.phone,
            hashed_password=hashed_pw,
            skills=payload.skills,
            experience=payload.experience,
            qualification=payload.qualification,
            is_active=False,
            is_email_verified=False,
            is_whatsapp_verified=False,
            is_totp_enabled=False,
        )
        db.add(new_user)
        await db.flush()

        # Associate uploaded resume if resume_id is provided
        if payload.resume_id:
            resume_stmt = select(UserResume).where(UserResume.id == payload.resume_id)
            resume_record: Optional[UserResume] = (
                await db.execute(resume_stmt)
            ).scalar_one_or_none()
            if resume_record and resume_record.user_id is None:
                resume_record.user_id = new_user.id
                meta = resume_record.extracted_metadata or {}
                if not new_user.skills and isinstance(meta.get("skills"), list) and meta["skills"]:
                    new_user.skills = meta["skills"]
                if not new_user.experience and isinstance(meta.get("experience"), str) and meta["experience"].strip():
                    new_user.experience = meta["experience"].strip()
                if not new_user.qualification and isinstance(meta.get("qualification"), str) and meta["qualification"].strip():
                    new_user.qualification = meta["qualification"].strip()

        await db.commit()
        await db.refresh(new_user)

        return UserRegisterResponse(
            success=True,
            message="Account created in staged status. Please complete Multi-Channel 2FA verification to activate your account.",
            user_id=new_user.id,
            email=new_user.email,
            phone=new_user.phone,
            is_active=new_user.is_active,
            required_2fa_channels=settings.required_channels_list,
            verification_status={
                "email": new_user.is_email_verified,
                "whatsapp": new_user.is_whatsapp_verified,
                "totp": new_user.is_totp_enabled,
            },
        )

    async def authenticate_user(
        self, db: AsyncSession, email: str, password: str
    ) -> User:
        stmt = select(User).where(func.lower(User.email) == email.strip().lower())
        user = (await db.execute(stmt)).scalar_one_or_none()
        if not user or not verify_password(password, user.hashed_password):
            raise RegistrationError(
                "Invalid email or password.",
                status_code=401,
                error_code="INVALID_CREDENTIALS",
            )
        return user


registration_service = RegistrationService()
