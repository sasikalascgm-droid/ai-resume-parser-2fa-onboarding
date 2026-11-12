from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies.authentication import get_current_verified_active_user
from app.models.user import User
from app.schemas.profile import StudentDashboardResponse
from app.services.profile_service import profile_service

router = APIRouter(prefix="/dashboard", tags=["Student Dashboard"])


@router.get(
    "/student",
    response_model=StudentDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve student dashboard data for verified and active candidates",
)
async def get_student_dashboard(
    current_user: User = Depends(get_current_verified_active_user),
    db: AsyncSession = Depends(get_db),
) -> StudentDashboardResponse:
    return await profile_service.get_student_dashboard(db=db, user=current_user)
