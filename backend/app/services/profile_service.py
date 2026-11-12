from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.user import User
from app.models.user_resume import UserResume
from app.schemas.profile import (
    ProfileResponse,
    ProfileUpdateRequest,
    ResumeMetadataSummary,
    StudentDashboardResponse,
)


class ProfileError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "PROFILE_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


class ProfileService:
    """Manages candidate profile retrieval, updates, completion scoring, and student dashboard data."""

    def calculate_profile_completion(self, user: User) -> int:
        score = 0
        if user.full_name and len(user.full_name.strip()) >= 2:
            score += 15
        if user.email and user.is_email_verified:
            score += 15
        if user.phone and user.is_whatsapp_verified:
            score += 15
        if user.is_totp_enabled:
            score += 15
        if user.skills and len(user.skills) > 0:
            score += 15
        if user.experience and len(user.experience.strip()) > 0:
            score += 15
        if user.qualification and len(user.qualification.strip()) > 0:
            score += 10
        return min(100, score)

    def sync_profile_from_resume_metadata(
        self, user: User, metadata: dict
    ) -> bool:
        """
        Synchronize full_name, skills, experience, and qualification from extracted resume metadata.
        Never overwrites existing profile values with empty extracted fields, and avoids duplicate updates.
        """
        if not metadata or not isinstance(metadata, dict):
            return False

        updated = False

        raw_name = metadata.get("full_name")
        if isinstance(raw_name, str):
            clean_name = " ".join(raw_name.strip().split())
            if len(clean_name) >= 2 and user.full_name != clean_name:
                user.full_name = clean_name
                updated = True

        raw_skills = metadata.get("skills")
        if isinstance(raw_skills, list) and len(raw_skills) > 0:
            seen = set()
            cleaned_skills = []
            for item in raw_skills:
                if isinstance(item, str):
                    s = item.strip()
                    if s and s.lower() not in seen:
                        seen.add(s.lower())
                        cleaned_skills.append(s)
            if cleaned_skills and (user.skills or []) != cleaned_skills:
                user.skills = cleaned_skills
                updated = True

        raw_exp = metadata.get("experience")
        if isinstance(raw_exp, str):
            clean_exp = raw_exp.strip()
            if clean_exp and user.experience != clean_exp:
                user.experience = clean_exp
                updated = True

        raw_qual = metadata.get("qualification")
        if isinstance(raw_qual, str):
            clean_qual = raw_qual.strip()
            if clean_qual and user.qualification != clean_qual:
                user.qualification = clean_qual
                updated = True

        return updated

    async def associate_resume_with_user(
        self, db: AsyncSession, user: User, resume_id: str
    ) -> Optional[UserResume]:
        stmt = select(UserResume).where(UserResume.id == resume_id)
        resume_record = (await db.execute(stmt)).scalar_one_or_none()
        if resume_record is None:
            return None

        if resume_record.user_id is not None and resume_record.user_id != user.id:
            raise ProfileError(
                "This resume record is already associated with another candidate account.",
                status_code=403,
                error_code="RESUME_OWNERSHIP_MISMATCH",
            )

        changed = False
        if resume_record.user_id is None:
            resume_record.user_id = user.id
            changed = True
            if self.sync_profile_from_resume_metadata(
                user, resume_record.extracted_metadata or {}
            ):
                changed = True

        if changed:
            await db.commit()
            await db.refresh(user)
            await db.refresh(resume_record)

        return resume_record

    async def _get_latest_resume_summary(
        self, db: AsyncSession, user_id: str
    ) -> Optional[ResumeMetadataSummary]:
        stmt = (
            select(UserResume)
            .where(UserResume.user_id == user_id)
            .order_by(UserResume.created_at.desc())
            .limit(1)
        )
        resume = (await db.execute(stmt)).scalar_one_or_none()
        if not resume:
            return None
        return ResumeMetadataSummary(
            id=resume.id,
            original_filename=resume.original_filename,
            extracted_metadata=resume.extracted_metadata or {},
            created_at=resume.created_at,
        )

    async def get_user_profile(
        self, db: AsyncSession, user: User
    ) -> ProfileResponse:
        latest_resume = await self._get_latest_resume_summary(db, user.id)
        completion = self.calculate_profile_completion(user)
        return ProfileResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            skills=user.skills or [],
            experience=user.experience,
            qualification=user.qualification,
            is_active=user.is_active,
            is_email_verified=user.is_email_verified,
            is_whatsapp_verified=user.is_whatsapp_verified,
            is_totp_enabled=user.is_totp_enabled,
            profile_completion=completion,
            latest_resume=latest_resume,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    async def update_user_profile(
        self,
        db: AsyncSession,
        user: User,
        payload: ProfileUpdateRequest,
    ) -> ProfileResponse:
        if payload.phone and payload.phone != user.phone:
            dup_stmt = select(User).where(
                User.phone == payload.phone,
                User.id != user.id,
            )
            existing = (await db.execute(dup_stmt)).scalar_one_or_none()
            if existing is not None:
                raise ProfileError(
                    "This phone number is already associated with another account.",
                    status_code=409,
                    error_code="DUPLICATE_PHONE",
                )
            user.phone = payload.phone

        if payload.full_name is not None:
            user.full_name = payload.full_name
        if payload.skills is not None:
            user.skills = payload.skills
        if payload.experience is not None:
            user.experience = payload.experience.strip() or None
        if payload.qualification is not None:
            user.qualification = payload.qualification.strip() or None

        await db.commit()
        await db.refresh(user)
        return await self.get_user_profile(db, user)

    async def get_student_dashboard(
        self, db: AsyncSession, user: User
    ) -> StudentDashboardResponse:
        settings = get_settings()
        latest_resume = await self._get_latest_resume_summary(db, user.id)
        completion = self.calculate_profile_completion(user)
        status_label = (
            "Complete"
            if completion == 100
            else "Almost Complete"
            if completion >= 75
            else "In Progress"
        )
        required = settings.required_channels_list
        channel_map = {
            "email": user.is_email_verified,
            "whatsapp": user.is_whatsapp_verified,
            "totp": user.is_totp_enabled,
        }
        all_required = all(channel_map.get(ch, False) for ch in required)

        return StudentDashboardResponse(
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            phone=user.phone,
            skills=user.skills or [],
            experience=user.experience,
            qualification=user.qualification,
            is_active=user.is_active,
            verification_status={
                "email": user.is_email_verified,
                "whatsapp": user.is_whatsapp_verified,
                "totp": user.is_totp_enabled,
                "all_required_verified": all_required,
            },
            profile_completion_percentage=completion,
            profile_completion_status=status_label,
            dashboard_route="/dashboard/student",
            latest_resume=latest_resume,
            created_at=user.created_at,
        )


profile_service = ProfileService()
