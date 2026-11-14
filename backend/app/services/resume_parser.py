import io
import os
import re
import shutil
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import docx
import pdfplumber
import pymupdf
import pytesseract
from PIL import Image

from app.core.config import get_settings
from app.core.logging import logger
from app.schemas.resume import ExtractedResumeData
from app.utils.file_validation import ResumeValidationError

_WINDOWS_TESSERACT_CANDIDATES: Tuple[str, ...] = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe",
    r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe",
    r"%USERPROFILE%\scoop\apps\tesseract\current\tesseract.exe",
    r"C:\ProgramData\chocolatey\bin\tesseract.exe",
)


def _resolve_tesseract_executable() -> Optional[str]:
    """
    Locate the local Tesseract OCR executable from settings, environment variables,
    system PATH, or standard Windows installation directories.
    """
    settings = get_settings()
    candidates: List[str] = []

    if getattr(settings, "TESSERACT_CMD", ""):
        candidates.append(settings.TESSERACT_CMD.strip())

    env_cmd = os.environ.get("TESSERACT_CMD", "").strip()
    if env_cmd:
        candidates.append(env_cmd)

    which_cmd = shutil.which("tesseract")
    if which_cmd:
        candidates.append(which_cmd)

    current_pytesseract_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "")
    if current_pytesseract_cmd and current_pytesseract_cmd != "tesseract":
        candidates.append(current_pytesseract_cmd)

    for raw_win_path in _WINDOWS_TESSERACT_CANDIDATES:
        expanded = os.path.expandvars(raw_win_path)
        candidates.append(expanded)

    for candidate in candidates:
        if not candidate:
            continue
        resolved = shutil.which(candidate) if not os.path.isabs(candidate) else candidate
        if resolved and os.path.isfile(resolved):
            pytesseract.pytesseract.tesseract_cmd = resolved
            return resolved

    return None

# Curated canonical skills dictionary for deterministic, zero-hallucination matching
KNOWN_SKILLS_MAP = {
    "python": "Python",
    "fastapi": "FastAPI",
    "django": "Django",
    "flask": "Flask",
    "java": "Java",
    "spring boot": "Spring Boot",
    "javascript": "JavaScript",
    "typescript": "TypeScript",
    "react": "React",
    "react.js": "React",
    "reactjs": "React",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "vue": "Vue.js",
    "angular": "Angular",
    "node.js": "Node.js",
    "nodejs": "Node.js",
    "express": "Express.js",
    "html": "HTML",
    "html5": "HTML5",
    "css": "CSS",
    "css3": "CSS3",
    "tailwind": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "sql": "SQL",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "mongodb": "MongoDB",
    "redis": "Redis",
    "sqlite": "SQLite",
    "sqlalchemy": "SQLAlchemy",
    "alembic": "Alembic",
    "pydantic": "Pydantic",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "aws": "AWS",
    "azure": "Azure",
    "gcp": "GCP",
    "git": "Git",
    "github": "GitHub",
    "ci/cd": "CI/CD",
    "linux": "Linux",
    "rest api": "REST API",
    "graphql": "GraphQL",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "nlp": "NLP",
    "pytorch": "PyTorch",
    "tensorflow": "TensorFlow",
    "pandas": "Pandas",
    "numpy": "NumPy",
    "scikit-learn": "Scikit-Learn",
    "c++": "C++",
    "c#": "C#",
    "go": "Go",
    "golang": "Go",
    "rust": "Rust",
    "pytest": "Pytest",
    "playwright": "Playwright",
    "selenium": "Selenium",
}

EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(
    r"(?:(?:\+|00)\d{1,3}[\s\-\.]?)?(?:\(?\d{3,5}\)?[\s\-\.]?)\d{3,5}[\s\-\.]?\d{3,5}"
)
EXPERIENCE_PATTERNS = [
    re.compile(
        r"\b(\d+(?:\.\d+)?\s*\+?\s*(?:years?|yrs?)(?:\s+of\s+(?:work\s+|professional\s+)?experience)?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:experience)\s*[:\-]\s*([^\n\r]{2,60})",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(fresher|entry[\s\-]level|intern(?:ship)?)\b",
        re.IGNORECASE,
    ),
]

QUALIFICATION_PATTERNS = [
    (
        re.compile(
            r"\b(Ph\.?D\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"M\.?\s*Tech\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"B\.?\s*Tech\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"B\.?\s*E\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"M\.?\s*E\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"M\.?\s*C\.?\s*A\.?|"
            r"B\.?\s*C\.?\s*A\.?|"
            r"M\.?\s*B\.?\s*A\.?|"
            r"M\.?\s*Sc\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"B\.?\s*Sc\.?(?:\s+in\s+[A-Za-z &]+)?|"
            r"Bachelor\s+of\s+(?:Technology|Engineering|Science|Computer\s+Applications|Arts)|"
            r"Master\s+of\s+(?:Technology|Engineering|Science|Computer\s+Applications|Business\s+Administration))\b",
            re.IGNORECASE,
        )
    )
]

HEADER_STOPWORDS = {
    "resume",
    "curriculum vitae",
    "cv",
    "biodata",
    "profile",
    "summary",
    "contact",
    "education",
    "experience",
    "skills",
    "projects",
    "certifications",
    "objective",
}


class BaseResumeExtractor(ABC):
    """Replaceable interface for resume candidate extraction (Regex or LLM/AI model)."""

    @abstractmethod
    def extract(self, raw_text: str) -> ExtractedResumeData:
        raise NotImplementedError


class RegexHeuristicResumeExtractor(BaseResumeExtractor):
    """Deterministic regex and section-heuristic extractor that never fabricates fields."""

    def extract(self, raw_text: str) -> ExtractedResumeData:
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        email = self._extract_email(raw_text)
        phone = self._extract_phone(raw_text)
        full_name = self._extract_name(lines, email)
        skills = self._extract_skills(raw_text, lines)
        experience = self._extract_experience(raw_text, lines)
        qualification = self._extract_qualification(raw_text, lines)

        return ExtractedResumeData(
            full_name=full_name,
            email=email,
            phone=phone,
            skills=skills,
            experience=experience,
            qualification=qualification,
        )

    def _extract_email(self, text: str) -> Optional[str]:
        match = EMAIL_PATTERN.search(text)
        return match.group(0).lower().strip() if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        for match in PHONE_PATTERN.finditer(text):
            raw = match.group(0)
            digits_only = re.sub(r"[^\d+]", "", raw)
            just_digits = re.sub(r"\D", "", digits_only)
            if 10 <= len(just_digits) <= 15:
                return digits_only
        return None

    def _extract_name(self, lines: List[str], email: Optional[str]) -> Optional[str]:
        # First check explicit "Name: ..." pattern
        for line in lines[:10]:
            explicit = re.match(r"^(?:full\s*name|name|candidate\s*name)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
            if explicit:
                candidate = explicit.group(1).strip()
                if self._looks_like_person_name(candidate):
                    return candidate

        # Next inspect top non-header lines
        for line in lines[:6]:
            cleaned = re.sub(r"[|#*_]", " ", line).strip()
            cleaned = " ".join(cleaned.split())
            if not cleaned:
                continue
            low = cleaned.lower()
            if low in HEADER_STOPWORDS:
                continue
            if email and email in low:
                continue
            if "@" in cleaned or any(char.isdigit() for char in cleaned):
                continue
            if self._looks_like_person_name(cleaned):
                return cleaned
        return None

    def _looks_like_person_name(self, candidate: str) -> bool:
        words = candidate.split()
        if not (1 <= len(words) <= 5):
            return False
        if len(candidate) < 2 or len(candidate) > 60:
            return False
        lower_words = {w.lower().strip(".,:") for w in words}
        if lower_words & HEADER_STOPWORDS:
            return False
        for word in words:
            stripped = word.replace(".", "").replace("-", "").replace("'", "")
            if not stripped.isalpha():
                return False
        return True

    def _extract_skills(self, text: str, lines: List[str]) -> List[str]:
        found: List[str] = []
        seen = set()

        # Check explicit "Skills: a, b, c" line first
        for idx, line in enumerate(lines):
            m = re.match(r"^(?:technical\s+skills|core\s+skills|skills|technologies)\s*[:\-]\s*(.+)$", line, re.IGNORECASE)
            if m:
                items = re.split(r"[,|•;/]", m.group(1))
                for item in items:
                    clean_item = item.strip(" .-•\t")
                    if 1 < len(clean_item) <= 35:
                        canonical = KNOWN_SKILLS_MAP.get(clean_item.lower(), clean_item)
                        if canonical.lower() not in seen:
                            seen.add(canonical.lower())
                            found.append(canonical)

        # Also scan full text for known technical skills with word boundaries
        for key, canonical in KNOWN_SKILLS_MAP.items():
            if canonical.lower() in seen:
                continue
            escaped = re.escape(key)
            # Handle skills ending with non-word chars like C++ or C#
            if key in {"c++", "c#"}:
                pattern = rf"(?<![A-Za-z0-9]){escaped}(?![A-Za-z0-9])"
            else:
                pattern = rf"\b{escaped}\b"
            if re.search(pattern, text, re.IGNORECASE):
                seen.add(canonical.lower())
                found.append(canonical)

        return found

    def _extract_experience(self, text: str, lines: List[str]) -> Optional[str]:
        for pattern in EXPERIENCE_PATTERNS:
            m = pattern.search(text)
            if m:
                val = " ".join(m.group(1).strip(" .,-:").split())
                if val:
                    return val[:120]
        return None

    def _extract_qualification(self, text: str, lines: List[str]) -> Optional[str]:
        # Check explicit "Qualification: ..." or "Education: ..." line
        for line in lines:
            m = re.match(
                r"^(?:highest\s+qualification|qualification|education|degree)\s*[:\-]\s*(.+)$",
                line,
                re.IGNORECASE,
            )
            if m:
                val = " ".join(m.group(1).strip(" .,-").split())
                if 2 <= len(val) <= 120:
                    return val

        for pattern in QUALIFICATION_PATTERNS:
            m = pattern.search(text)
            if m:
                val = " ".join(m.group(1).strip(" .,-").split())
                if val:
                    return val[:120]
        return None


class ResumeParserService:
    """Service responsible for safe file text extraction and structured field parsing."""

    def __init__(self, extractor: Optional[BaseResumeExtractor] = None) -> None:
        self.extractor = extractor or RegexHeuristicResumeExtractor()

    def extract_text_from_bytes(self, content: bytes, extension: str) -> Tuple[str, List[str]]:
        warnings: List[str] = []
        if extension == ".pdf":
            return self._extract_pdf_text(content, warnings)
        elif extension == ".docx":
            return self._extract_docx_text(content, warnings)
        else:
            raise ResumeValidationError(
                f"Unsupported file extension: {extension}",
                status_code=415,
                error_code="UNSUPPORTED_FORMAT",
            )

    def _extract_pdf_text(self, content: bytes, warnings: List[str]) -> Tuple[str, List[str]]:
        try:
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                total_pages = len(pdf.pages)
                if total_pages == 0:
                    raise ResumeValidationError(
                        "The uploaded PDF contains no pages.",
                        status_code=422,
                        error_code="EMPTY_DOCUMENT",
                    )
                page_texts_by_idx: Dict[int, str] = {}
                total_images = 0
                for idx, page in enumerate(pdf.pages):
                    try:
                        total_images += len(getattr(page, "images", []) or [])
                    except Exception:
                        pass
                    txt = (page.extract_text() or "").replace("\x00", "").strip()
                    if txt:
                        page_texts_by_idx[idx] = txt

                # Fast path: all pages yielded machine-readable text
                if len(page_texts_by_idx) == total_pages:
                    combined = "\n".join(
                        page_texts_by_idx[i] for i in range(total_pages)
                    )
                    combined = combined.encode("utf-8", "replace").decode("utf-8").strip()
                    if combined:
                        return combined, warnings

                # Inspect pages lacking text with PyMuPDF to determine if they contain scanned images
                has_visual_content = total_images > 0
                if not has_visual_content:
                    with pymupdf.open(stream=content, filetype="pdf") as mupdf_doc:
                        for mpage in mupdf_doc:
                            if len(mpage.get_images(full=True)) > 0:
                                has_visual_content = True
                                break

                # If some pages had text and there are no scanned images on the remaining pages, return text
                if page_texts_by_idx and not has_visual_content:
                    combined = "\n".join(
                        page_texts_by_idx[i] for i in sorted(page_texts_by_idx.keys())
                    )
                    combined = combined.encode("utf-8", "replace").decode("utf-8").strip()
                    if combined:
                        return combined, warnings

                # If no pages had text and no pages contain any images, the PDF is blank
                if not page_texts_by_idx and not has_visual_content:
                    raise ResumeValidationError(
                        "No readable text found in the PDF. If this is a scanned PDF, OCR is required.",
                        status_code=422,
                        error_code="EMPTY_OR_SCANNED_PDF",
                    )

                # Scanned or hybrid PDF detected -> run local OCR on pages missing text
                return self._extract_pdf_text_via_ocr(
                    content=content,
                    warnings=warnings,
                    existing_page_texts=page_texts_by_idx,
                )
        except ResumeValidationError:
            raise
        except Exception as exc:
            logger.warning("Failed to parse PDF file due to structural corruption: %s", type(exc).__name__)
            raise ResumeValidationError(
                "Unable to read PDF file. The file appears to be corrupted or password-protected.",
                status_code=422,
                error_code="CORRUPTED_FILE",
            )

    def _extract_pdf_text_via_ocr(
        self,
        content: bytes,
        warnings: List[str],
        existing_page_texts: Optional[Dict[int, str]] = None,
    ) -> Tuple[str, List[str]]:
        """
        Render scanned PDF pages to grayscale images using PyMuPDF and extract text
        locally using Tesseract OCR (pytesseract), enforcing page, resolution, and timeout limits.
        """
        settings = get_settings()
        if len(content) > settings.max_upload_bytes:
            raise ResumeValidationError(
                f"File size exceeds the maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB} MB.",
                status_code=413,
                error_code="FILE_TOO_LARGE",
            )

        max_pages = max(1, int(getattr(settings, "OCR_MAX_PAGES", 10)))
        dpi = min(max(72, int(getattr(settings, "OCR_RENDER_DPI", 200))), 300)
        max_dim = max(500, int(getattr(settings, "OCR_MAX_IMAGE_DIMENSION", 2500)))
        page_timeout = max(2, int(getattr(settings, "OCR_PAGE_TIMEOUT_SECONDS", 15)))
        total_timeout = max(5, int(getattr(settings, "OCR_TOTAL_TIMEOUT_SECONDS", 60)))

        _resolve_tesseract_executable()

        existing_map = existing_page_texts or {}
        collected_pages: List[str] = []
        start_mono = time.monotonic()

        with pymupdf.open(stream=content, filetype="pdf") as doc:
            total_pages = len(doc)
            if total_pages == 0:
                raise ResumeValidationError(
                    "The uploaded PDF contains no pages.",
                    status_code=422,
                    error_code="EMPTY_DOCUMENT",
                )

            pages_to_process = min(total_pages, max_pages)
            if total_pages > max_pages:
                warnings.append(
                    f"PDF has {total_pages} pages; OCR was limited to the first {max_pages} pages."
                )

            for idx in range(pages_to_process):
                if idx in existing_map and existing_map[idx].strip():
                    collected_pages.append(existing_map[idx].strip())
                    continue

                elapsed = time.monotonic() - start_mono
                if elapsed > total_timeout:
                    if collected_pages:
                        warnings.append(
                            f"OCR time limit ({total_timeout}s) reached after {idx} page(s); returning partial text."
                        )
                        break
                    raise ResumeValidationError(
                        f"OCR processing exceeded the {total_timeout}-second time limit. "
                        "Please upload a smaller or clearer resume PDF.",
                        status_code=422,
                        error_code="OCR_TIMEOUT",
                    )

                mpage = doc[idx]
                pix = mpage.get_pixmap(dpi=dpi, alpha=False)
                pil_img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")

                if max(pil_img.width, pil_img.height) > max_dim:
                    pil_img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

                try:
                    ocr_text = (
                        pytesseract.image_to_string(
                            pil_img,
                            lang="eng",
                            timeout=page_timeout,
                        )
                        or ""
                    )
                except pytesseract.TesseractNotFoundError:
                    raise ResumeValidationError(
                        "Scanned PDF detected, but Tesseract OCR is not installed or could not be found on the server. "
                        "Please install Tesseract OCR (e.g., 'winget install --id UB-Mannheim.TesseractOCR -e' on Windows) "
                        "or set TESSERACT_CMD in .env to the full path of tesseract.exe.",
                        status_code=422,
                        error_code="OCR_UNAVAILABLE",
                    )
                except RuntimeError:
                    raise ResumeValidationError(
                        f"OCR timed out while processing page {idx + 1} (limit: {page_timeout}s). "
                        "Please upload a clearer or smaller PDF resume.",
                        status_code=422,
                        error_code="OCR_TIMEOUT",
                    )
                except Exception as exc:
                    logger.warning("OCR failed on page %d: %s", idx + 1, type(exc).__name__)
                    raise ResumeValidationError(
                        "Scanned PDF detected, but OCR processing failed. Please ensure Tesseract OCR is properly installed.",
                        status_code=422,
                        error_code="OCR_PROCESSING_ERROR",
                    )

                cleaned_page = ocr_text.replace("\x00", "").strip()
                if cleaned_page:
                    collected_pages.append(cleaned_page)

        combined = "\n".join(collected_pages).replace("\x00", "")
        combined = combined.encode("utf-8", "replace").decode("utf-8").strip()
        if not combined:
            raise ResumeValidationError(
                "Scanned PDF detected: no machine-readable text could be extracted even after running OCR. "
                "Please upload a clearer scan or a text-based PDF/DOCX.",
                status_code=422,
                error_code="SCANNED_PDF_NEEDS_OCR",
            )

        warnings.append("Scanned PDF processed using local Tesseract OCR.")
        return combined, warnings

    def _extract_docx_text(self, content: bytes, warnings: List[str]) -> Tuple[str, List[str]]:
        try:
            document = docx.Document(io.BytesIO(content))
            chunks: List[str] = []
            for para in document.paragraphs:
                if para.text and para.text.strip():
                    chunks.append(para.text.strip())
            for table in document.tables:
                for row in table.rows:
                    row_cells = [cell.text.strip() for cell in row.cells if cell.text and cell.text.strip()]
                    if row_cells:
                        chunks.append(" | ".join(row_cells))

            combined = "\n".join(chunks).replace("\x00", "")
            combined = combined.encode("utf-8", "replace").decode("utf-8").strip()
            if not combined:
                raise ResumeValidationError(
                    "The uploaded DOCX document contains no readable text.",
                    status_code=422,
                    error_code="EMPTY_DOCUMENT",
                )
            return combined, warnings
        except ResumeValidationError:
            raise
        except Exception as exc:
            logger.warning("Failed to parse DOCX file due to structural corruption: %s", type(exc).__name__)
            raise ResumeValidationError(
                "Unable to read DOCX file. The file appears to be corrupted or invalid.",
                status_code=422,
                error_code="CORRUPTED_FILE",
            )

    def save_uploaded_file_safely(self, stored_filename: str, content: bytes) -> Path:
        settings = get_settings()
        raw_upload_dir = Path(settings.UPLOAD_DIR)
        if not raw_upload_dir.is_absolute():
            raw_upload_dir = Path(__file__).resolve().parents[2] / raw_upload_dir
        upload_dir = raw_upload_dir.resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = Path(stored_filename).name
        target_path = (upload_dir / safe_name).resolve()
        if upload_dir not in target_path.parents:
            raise ResumeValidationError(
                "Invalid destination path detected.",
                status_code=400,
                error_code="PATH_TRAVERSAL_BLOCKED",
            )
        target_path.write_bytes(content)
        return target_path

    def parse_resume_bytes(self, content: bytes, extension: str) -> Tuple[str, ExtractedResumeData, List[str]]:
        raw_text, warnings = self.extract_text_from_bytes(content, extension)
        try:
            extracted = self.extractor.extract(raw_text)
        except Exception as exc:
            logger.error("Failed to extract structured metadata from resume text: %s", type(exc).__name__, exc_info=True)
            extracted = ExtractedResumeData()
            warnings.append("Some structured candidate fields could not be automatically extracted.")
        return raw_text, extracted, warnings


resume_parser_service = ResumeParserService()
