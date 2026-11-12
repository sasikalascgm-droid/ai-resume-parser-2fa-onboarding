import re
from typing import Dict, List, Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator


OTP_CODE_REGEX = re.compile(r"^\d{6}$")


class SendOTPRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    channel: Literal["email", "whatsapp"]

    @model_validator(mode="after")
    def ensure_identifier(self) -> "SendOTPRequest":
        if not self.user_id and not self.email:
            raise ValueError("Either user_id or email must be provided.")
        return self


class SendOTPResponse(BaseModel):
    success: bool = True
    channel: str
    delivery_mode: str
    delivered: bool
    is_simulated: bool = False
    message: str
    expires_in_seconds: int
    cooldown_seconds: int
    recipient_masked: str
    dev_otp_preview: Optional[str] = None


class Verify2FARequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    channel: Literal["email", "whatsapp"]
    otp: str = Field(..., min_length=6, max_length=6)

    @field_validator("otp")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not OTP_CODE_REGEX.match(cleaned):
            raise ValueError("OTP must be a 6-digit numeric code.")
        return cleaned

    @model_validator(mode="after")
    def ensure_identifier(self) -> "Verify2FARequest":
        if not self.user_id and not self.email:
            raise ValueError("Either user_id or email must be provided.")
        return self


class TOTPSetupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    email: Optional[EmailStr] = None


class TOTPSetupResponse(BaseModel):
    success: bool = True
    qr_code_data_url: str
    is_totp_enabled: bool


class TOTPVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: Optional[str] = None
    email: Optional[EmailStr] = None
    otp: str = Field(..., min_length=6, max_length=6)

    @field_validator("otp")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        cleaned = v.strip()
        if not OTP_CODE_REGEX.match(cleaned):
            raise ValueError("Authenticator code must be a 6-digit numeric code.")
        return cleaned


class VerificationStatusResponse(BaseModel):
    success: bool = True
    message: str
    user_id: str
    channel_verified: str
    is_email_verified: bool
    is_whatsapp_verified: bool
    is_totp_enabled: bool
    is_active: bool
    required_channels: List[str]
    access_token: Optional[str] = None
    token_type: Optional[str] = None


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    resume_id: Optional[str] = None


class LoginResponse(BaseModel):
    success: bool = True
    message: str
    user_id: str
    email: str
    full_name: str
    is_active: bool
    requires_2fa_completion: bool
    verification_status: Dict[str, bool]
    required_channels: List[str]
    access_token: Optional[str] = None
    token_type: Optional[str] = "bearer"
