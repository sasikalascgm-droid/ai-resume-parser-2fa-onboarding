import os
import re
import uuid
from pathlib import Path
from typing import Tuple

from fastapi import UploadFile

from app.core.config import get_settings

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
ALLOWED_CONTENT_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/octet-stream",
}


class ResumeValidationError(Exception):
    def __init__(self, message: str, status_code: int = 400, error_code: str = "INVALID_FILE"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code


def sanitize_original_filename(filename: str) -> str:
    """Prevent path traversal and sanitize user-supplied filename."""
    if not filename:
        raise ResumeValidationError("Filename is missing.", status_code=400, error_code="MISSING_FILENAME")

    # Strip directory paths (both Unix and Windows separators)
    base_name = os.path.basename(filename.replace("\\", "/")).strip()
    if not base_name or base_name in {".", ".."} or ".." in base_name:
        raise ResumeValidationError("Invalid filename detected.", status_code=400, error_code="PATH_TRAVERSAL_BLOCKED")

    # Replace unsafe characters
    safe_name = re.sub(r"[^A-Za-z0-9._\- ]", "_", base_name)
    return safe_name[:200]


async def validate_and_read_resume_upload(upload_file: UploadFile) -> Tuple[str, str, bytes, str]:
    """
    Validate file extension, size, and magic bytes.
    Returns (safe_original_filename, safe_stored_filename, file_bytes, extension).
    """
    settings = get_settings()
    safe_original = sanitize_original_filename(upload_file.filename or "")
    ext = Path(safe_original).suffix.lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise ResumeValidationError(
            f"Unsupported file format '{ext or 'unknown'}'. Only .pdf and .docx files are accepted.",
            status_code=415,
            error_code="UNSUPPORTED_FORMAT",
        )

    content = await upload_file.read()
    if not content or len(content) == 0:
        raise ResumeValidationError(
            "Uploaded file is empty (0 bytes). Please upload a valid resume.",
            status_code=400,
            error_code="EMPTY_FILE",
        )

    if len(content) > settings.max_upload_bytes:
        raise ResumeValidationError(
            f"File size exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
            status_code=413,
            error_code="FILE_TOO_LARGE",
        )

    # Check magic bytes to detect disguised or corrupted files early
    if ext == ".pdf" and not content.startswith(b"%PDF"):
        raise ResumeValidationError(
            "Corrupted or invalid PDF file header.",
            status_code=422,
            error_code="CORRUPTED_FILE",
        )
    if ext == ".docx" and not content.startswith(b"PK\x03\x04"):
        raise ResumeValidationError(
            "Corrupted or invalid DOCX file header.",
            status_code=422,
            error_code="CORRUPTED_FILE",
        )

    safe_stored_filename = f"{uuid.uuid4().hex}{ext}"
    return safe_original, safe_stored_filename, content, ext
