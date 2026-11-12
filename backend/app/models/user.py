import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.otp_challenge import OTPChallenge
    from app.models.user_resume import UserResume

JSONBType = JSON().with_variant(JSONB(), "postgresql")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("phone", name="uq_users_phone"),
        Index("ix_users_email", "email"),
        Index("ix_users_phone", "phone"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)

    skills: Mapped[List[str]] = mapped_column(JSONBType, nullable=False, default=list)
    experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    qualification: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    totp_secret_encrypted: Mapped[Optional[str]] = mapped_column(
        String(512), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_whatsapp_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_totp_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    resumes: Mapped[List["UserResume"]] = relationship(
        "UserResume",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    otp_challenges: Mapped[List["OTPChallenge"]] = relationship(
        "OTPChallenge",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
