from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.user import normalize_phone_number


class ResumeMetadataSummary(BaseModel):
    id: str
    original_filename: str
    extracted_metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class ProfileResponse(BaseModel):
    id: str
    full_name: str
    email: str
    phone: str
    skills: List[str]
    experience: Optional[str] = None
    qualification: Optional[str] = None
    is_active: bool
    is_email_verified: bool
    is_whatsapp_verified: bool
    is_totp_enabled: bool
    profile_completion: int
    latest_resume: Optional[ResumeMetadataSummary] = None
    created_at: datetime
    updated_at: datetime


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    phone: Optional[str] = Field(default=None, min_length=10, max_length=20)
    skills: Optional[List[str]] = None
    experience: Optional[str] = Field(default=None, max_length=2000)
    qualification: Optional[str] = Field(default=None, max_length=255)

    @field_validator("full_name")
    @classmethod
    def clean_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        cleaned = " ".join(v.strip().split())
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        return normalize_phone_number(v)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        seen = set()
        cleaned = []
        for s in v:
            if isinstance(s, str):
                item = s.strip()
                if item and item.lower() not in seen:
                    seen.add(item.lower())
                    cleaned.append(item)
        return cleaned


class StudentDashboardResponse(BaseModel):
    user_id: str
    full_name: str
    email: str
    phone: str
    skills: List[str]
    experience: Optional[str] = None
    qualification: Optional[str] = None
    is_active: bool
    verification_status: Dict[str, bool]
    profile_completion_percentage: int
    profile_completion_status: str
    dashboard_route: str = "/dashboard/student"
    latest_resume: Optional[ResumeMetadataSummary] = None
    created_at: datetime
