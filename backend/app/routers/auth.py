from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies.authentication import bearer_scheme, extract_token_from_request
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    SendOTPRequest,
    SendOTPResponse,
    TOTPSetupRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    VerificationStatusResponse,
    Verify2FARequest,
)
from app.schemas.user import UserRegisterRequest, UserRegisterResponse
from app.services.otp_service import otp_service
from app.services.profile_service import profile_service
from app.services.registration_service import registration_service
from app.services.token_service import token_service
from app.services.totp_service import totp_service

router = APIRouter(prefix="/auth", tags=["Authentication & Multi-Channel 2FA"])


@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a staged candidate account with Argon2id password hashing",
)
async def register_user(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> UserRegisterResponse:
    return await registration_service.register_candidate(db=db, payload=payload)


@router.post(
    "/send-otp",
    response_model=SendOTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate and send a 6-digit OTP via Email (SMTP) or WhatsApp Cloud API",
)
async def send_otp(
    payload: SendOTPRequest,
    db: AsyncSession = Depends(get_db),
) -> SendOTPResponse:
    user = await otp_service.get_target_user(
        db=db,
        user_id=payload.user_id,
        email=str(payload.email) if payload.email else None,
    )
    return await otp_service.send_otp(
        db=db,
        user=user,
        channel=payload.channel,
    )


@router.post(
    "/verify-2fa",
    response_model=VerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify a 6-digit OTP for Email or WhatsApp channel",
)
async def verify_2fa(
    payload: Verify2FARequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> VerificationStatusResponse:
    user = await otp_service.get_target_user(
        db=db,
        user_id=payload.user_id,
        email=str(payload.email) if payload.email else None,
    )
    result = await otp_service.verify_channel_otp(
        db=db,
        user=user,
        channel=payload.channel,
        otp_code=payload.otp,
    )
    if result.access_token:
        token_service.set_auth_cookie(response, result.access_token)
    return result


@router.post(
    "/totp/setup",
    response_model=TOTPSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Enroll Browser/Authenticator App TOTP and generate QR Code & encrypted secret",
)
async def setup_totp(
    payload: TOTPSetupRequest,
    db: AsyncSession = Depends(get_db),
) -> TOTPSetupResponse:
    user = await otp_service.get_target_user(
        db=db,
        user_id=payload.user_id,
        email=str(payload.email) if payload.email else None,
    )
    setup_data = await totp_service.setup_totp_for_user(db=db, user=user)
    return TOTPSetupResponse(success=True, **setup_data)


@router.post(
    "/totp/verify",
    response_model=VerificationStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify time-based 6-digit Authenticator TOTP code and activate account when policy met",
)
async def verify_totp(
    payload: TOTPVerifyRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> VerificationStatusResponse:
    user = await otp_service.get_target_user(
        db=db,
        user_id=payload.user_id,
        email=str(payload.email) if payload.email else None,
    )
    result = await otp_service.verify_totp_and_update_state(
        db=db,
        user=user,
        otp_code=payload.otp,
    )
    if result.access_token:
        token_service.set_auth_cookie(response, result.access_token)
    return result


@router.get(
    "/status/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Get current multi-channel 2FA verification status for a user",
)
async def get_verification_status(
    user_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    settings = get_settings()
    user = await otp_service.get_target_user(db=db, user_id=user_id)
    return {
        "success": True,
        "user_id": user.id,
        "email": user.email,
        "phone": user.phone,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_email_verified": user.is_email_verified,
        "is_whatsapp_verified": user.is_whatsapp_verified,
        "is_totp_enabled": user.is_totp_enabled,
        "required_channels": settings.required_channels_list,
    }


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate candidate credentials and issue JWT if account is active",
)
async def login_user(
    payload: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    user = await registration_service.authenticate_user(
        db=db,
        email=str(payload.email),
        password=payload.password,
    )
    if payload.resume_id:
        await profile_service.associate_resume_with_user(
            db=db,
            user=user,
            resume_id=payload.resume_id,
        )
    required = settings.required_channels_list
    verification_status = {
        "email": user.is_email_verified,
        "whatsapp": user.is_whatsapp_verified,
        "totp": user.is_totp_enabled,
    }
    all_verified = all(verification_status.get(ch, False) for ch in required)

    if not user.is_active or not all_verified:
        return LoginResponse(
            success=True,
            message="Credentials verified. Please complete pending 2FA verifications to activate your account.",
            user_id=user.id,
            email=user.email,
            full_name=user.full_name,
            is_active=False,
            requires_2fa_completion=True,
            verification_status=verification_status,
            required_channels=required,
            access_token=None,
            token_type=None,
        )

    token = token_service.issue_token_for_user(user)
    token_service.set_auth_cookie(response, token)
    return LoginResponse(
        success=True,
        message="Login successful.",
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=True,
        requires_2fa_completion=False,
        verification_status=verification_status,
        required_channels=required,
        access_token=token,
        token_type="bearer",
    )


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Revoke current JWT token and clear HttpOnly authentication cookie",
)
async def logout_user(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    try:
        token = extract_token_from_request(request, credentials)
        token_service.revoke_token(token)
    except Exception:
        pass
    token_service.clear_auth_cookie(response)
    return {
        "success": True,
        "message": "Successfully logged out.",
    }
