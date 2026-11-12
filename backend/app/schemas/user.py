import re
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


PHONE_REGEX = re.compile(r"^\+?[0-9]{10,15}$")


def normalize_phone_number(value: str) -> str:
    cleaned = re.sub(r"[\s\-\(\)\.]", "", value.strip())
    if not PHONE_REGEX.match(cleaned):
        raise ValueError("Phone number must contain 10 to 15 digits (optional + prefix).")
    return cleaned


def validate_password_strength(value: str) -> str:
    if len(value) < 8:
        raise ValueError("Password must be at least 8 characters long.")
    if len(value) > 128:
        raise ValueError("Password must not exceed 128 characters.")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r"[a-z]", value):
        raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r"\d", value):
        raise ValueError("Password must contain at least one digit.")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>\-_=+\[\]\\;'/`~]", value):
        raise ValueError("Password must contain at least one special character.")
    return value


class UserRegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=10, max_length=20)
    skills: List[str] = Field(default_factory=list)
    experience: Optional[str] = Field(default=None, max_length=2000)
    qualification: Optional[str] = Field(default=None, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: str = Field(..., min_length=8, max_length=128)
    resume_id: Optional[str] = Field(default=None, max_length=64)

    @field_validator("full_name")
    @classmethod
    def clean_full_name(cls, v: str) -> str:
        cleaned = " ".join(v.strip().split())
        if len(cleaned) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        return cleaned

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return normalize_phone_number(v)

    @field_validator("skills")
    @classmethod
    def clean_skills(cls, v: List[str]) -> List[str]:
        seen = set()
        result = []
        for item in v:
            if isinstance(item, str):
                s = item.strip()
                if s and s.lower() not in seen:
                    seen.add(s.lower())
                    result.append(s)
        return result

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)

    @model_validator(mode="after")
    def verify_passwords_match(self) -> "UserRegisterRequest":
        if self.password != self.confirm_password:
            raise ValueError("Password and confirm password do not match.")
        return self


class UserRegisterResponse(BaseModel):
    success: bool = True
    message: str
    user_id: str
    email: str
    phone: str
    is_active: bool
    required_2fa_channels: List[str]
    verification_status: Dict[str, bool]
