from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authentication import get_current_verified_active_user
from app.models.user import User
from app.schemas.profile import ProfileResponse, ProfileUpdateRequest
from app.services.profile_service import profile_service

router = APIRouter(prefix="/profile", tags=["Candidate Profile"])


@router.get(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve authenticated candidate's profile and verification status",
)
async def get_profile(
    current_user: User = Depends(get_current_verified_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    return await profile_service.get_user_profile(db=db, user=current_user)


@router.patch(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update authenticated candidate's editable profile fields",
)
async def update_profile(
    payload: ProfileUpdateRequest,
    current_user: User = Depends(get_current_verified_active_user),
    db: AsyncSession = Depends(get_db),
) -> ProfileResponse:
    return await profile_service.update_user_profile(
        db=db,
        user=current_user,
        payload=payload,
    )
