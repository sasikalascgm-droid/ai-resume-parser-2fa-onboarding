from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db
from app.dependencies.authentication import (
    get_current_user,
    get_current_verified_active_user,
    get_optional_current_user,
)
from app.models.user import User
from app.models.user_resume import UserResume
from app.schemas.resume import ExtractedResumeData, ResumeParseResponse
from app.services.profile_service import ProfileError, profile_service
from app.services.resume_parser import resume_parser_service
from app.utils.file_validation import validate_and_read_resume_upload

router = APIRouter(prefix="/resume", tags=["Resume Parsing"])


def _resolve_stored_resume_path(stored_filename: str) -> Optional[Path]:
    settings = get_settings()
    safe_name = Path(stored_filename).name
    candidates = [
        Path(settings.UPLOAD_DIR).resolve() / safe_name,
        (Path(__file__).resolve().parents[2] / settings.UPLOAD_DIR / safe_name).resolve(),
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and parse a candidate PDF or DOCX resume",
)
async def parse_resume_endpoint(
    file: UploadFile = File(..., description="Candidate resume in .pdf or .docx format"),
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeParseResponse:
    safe_original, safe_stored, content, ext = await validate_and_read_resume_upload(file)
    raw_text, extracted_data, warnings = resume_parser_service.parse_resume_bytes(
        content=content,
        extension=ext,
    )
    metadata_dict = extracted_data.model_dump()

    if current_user is not None:
        # Check if the latest resume for this authenticated user is an exact duplicate
        latest_stmt = (
            select(UserResume)
            .where(UserResume.user_id == current_user.id)
            .order_by(UserResume.created_at.desc())
            .limit(1)
        )
        latest_existing = (await db.execute(latest_stmt)).scalar_one_or_none()
        if (
            latest_existing is not None
            and latest_existing.original_filename == safe_original
            and latest_existing.extracted_text == raw_text
            and _resolve_stored_resume_path(latest_existing.stored_filename) is not None
        ):
            if profile_service.sync_profile_from_resume_metadata(current_user, metadata_dict):
                await db.commit()
                await db.refresh(current_user)
            return ResumeParseResponse(
                success=True,
                resume_id=latest_existing.id,
                original_filename=latest_existing.original_filename,
                extracted_data=extracted_data,
                warnings=warnings,
            )

        resume_parser_service.save_uploaded_file_safely(safe_stored, content)
        profile_service.sync_profile_from_resume_metadata(current_user, metadata_dict)
        resume_record = UserResume(
            user_id=current_user.id,
            original_filename=safe_original,
            stored_filename=safe_stored,
            extracted_text=raw_text,
            extracted_metadata=metadata_dict,
        )
        db.add(resume_record)
        await db.commit()
        await db.refresh(resume_record)
    else:
        # Check if an identical unlinked resume record already exists to avoid duplicate unlinked rows
        unlinked_stmt = (
            select(UserResume)
            .where(
                UserResume.user_id.is_(None),
                UserResume.original_filename == safe_original,
                UserResume.extracted_text == raw_text,
            )
            .order_by(UserResume.created_at.desc())
            .limit(1)
        )
        existing_unlinked = (await db.execute(unlinked_stmt)).scalar_one_or_none()
        if (
            existing_unlinked is not None
            and _resolve_stored_resume_path(existing_unlinked.stored_filename) is not None
        ):
            return ResumeParseResponse(
                success=True,
                resume_id=existing_unlinked.id,
                original_filename=existing_unlinked.original_filename,
                extracted_data=extracted_data,
                warnings=warnings,
            )

        resume_parser_service.save_uploaded_file_safely(safe_stored, content)
        resume_record = UserResume(
            user_id=None,
            original_filename=safe_original,
            stored_filename=safe_stored,
            extracted_text=raw_text,
            extracted_metadata=metadata_dict,
        )
        db.add(resume_record)
        await db.commit()
        await db.refresh(resume_record)

    return ResumeParseResponse(
        success=True,
        resume_id=resume_record.id,
        original_filename=safe_original,
        extracted_data=extracted_data,
        warnings=warnings,
    )


@router.post(
    "/{resume_id}/associate",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Associate an uploaded resume record with the authenticated candidate and sync profile fields",
)
async def associate_resume_endpoint(
    resume_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeParseResponse:
    resume_record = await profile_service.associate_resume_with_user(
        db=db,
        user=current_user,
        resume_id=resume_id,
    )
    if resume_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded resume record not found.",
        )

    meta = resume_record.extracted_metadata or {}
    return ResumeParseResponse(
        success=True,
        resume_id=resume_record.id,
        original_filename=resume_record.original_filename,
        extracted_data=ExtractedResumeData(
            full_name=meta.get("full_name"),
            email=meta.get("email"),
            phone=meta.get("phone"),
            skills=meta.get("skills") or [],
            experience=meta.get("experience"),
            qualification=meta.get("qualification"),
        ),
        warnings=[],
    )


@router.get(
    "/{resume_id}",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve stored resume record and extracted metadata by resume_id for verified active candidate",
)
async def get_resume_record_endpoint(
    resume_id: str,
    current_user: User = Depends(get_current_verified_active_user),
    db: AsyncSession = Depends(get_db),
) -> ResumeParseResponse:
    stmt = select(UserResume).where(UserResume.id == resume_id)
    resume_record = (await db.execute(stmt)).scalar_one_or_none()
    if resume_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded resume record not found.",
        )
    if resume_record.user_id is not None and resume_record.user_id != current_user.id:
        raise ProfileError(
            "You do not have permission to view this resume record.",
            status_code=403,
            error_code="RESUME_OWNERSHIP_MISMATCH",
        )
    meta = resume_record.extracted_metadata or {}
    return ResumeParseResponse(
        success=True,
        resume_id=resume_record.id,
        original_filename=resume_record.original_filename,
        extracted_data=ExtractedResumeData(
            full_name=meta.get("full_name"),
            email=meta.get("email"),
            phone=meta.get("phone"),
            skills=meta.get("skills") or [],
            experience=meta.get("experience"),
            qualification=meta.get("qualification"),
        ),
        warnings=[],
    )


@router.get(
    "/{resume_id}/file",
    status_code=status.HTTP_200_OK,
    summary="Preview or download the previously uploaded resume document for verified active candidate",
)
async def view_uploaded_resume_file_endpoint(
    resume_id: str,
    download: bool = Query(default=False, description="Set true to force file download attachment"),
    current_user: User = Depends(get_current_verified_active_user),
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    stmt = select(UserResume).where(UserResume.id == resume_id)
    resume_record = (await db.execute(stmt)).scalar_one_or_none()
    if resume_record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded resume record not found.",
        )
    if resume_record.user_id is not None and resume_record.user_id != current_user.id:
        raise ProfileError(
            "You do not have permission to access this resume document.",
            status_code=403,
            error_code="RESUME_OWNERSHIP_MISMATCH",
        )

    file_path = _resolve_stored_resume_path(resume_record.stored_filename)
    if file_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stored resume file is unavailable on disk.",
        )

    ext = Path(resume_record.original_filename).suffix.lower()
    media_type = (
        "application/pdf"
        if ext == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    disposition = "attachment" if download else "inline"
    return FileResponse(
        path=str(file_path),
        media_type=media_type,
        headers={
            "Content-Disposition": f'{disposition}; filename="{resume_record.original_filename}"'
        },
    )
