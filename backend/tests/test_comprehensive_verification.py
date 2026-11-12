import io
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import AsyncClient
from PIL import Image
from pydantic import ValidationError
from reportlab.lib.pagesizes import letter
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings, normalize_postgres_asyncpg_url
from app.core.security import hash_otp, hash_password, verify_otp_hash
from app.models.otp_challenge import OTPChallenge
from app.models.user import User
from app.models.user_resume import UserResume
from app.services.email_service import EmailService, ExternalProviderError
from app.services.whatsapp_service import WhatsAppCloudAPIAdapter
from app.utils.file_validation import sanitize_original_filename


def create_scanned_image_only_pdf_bytes() -> bytes:
    """Create a real PDF containing an embedded raster image and zero text streams."""
    img = Image.new("RGB", (200, 80), color=(240, 240, 240))
    img_buf = io.BytesIO()
    img.save(img_buf, format="PNG")
    img_buf.seek(0)

    pdf_buf = io.BytesIO()
    c = canvas.Canvas(pdf_buf, pagesize=letter)
    c.drawImage(ImageReader(img_buf), 100, 600, width=200, height=80)
    c.showPage()
    c.save()
    return pdf_buf.getvalue()


# ============================================================================
# TASK 3: DATABASE CRUD & TRANSACTION ROLLBACK VERIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_database_crud_and_transaction_rollback(db_session: AsyncSession):
    dialect_name = db_session.bind.dialect.name if db_session.bind else "unknown"
    assert dialect_name in {"postgresql", "sqlite"}

    # 1. Create User & Store Resume Metadata in JSONB
    user = User(
        full_name="Siddharth Mehta",
        email="siddharth.m@skillverse.edu",
        phone="9898989898",
        hashed_password=hash_password("Siddharth#2026"),
        skills=["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
        experience="3 years",
        qualification="B.Tech",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()
    user_id = user.id

    resume = UserResume(
        user_id=user_id,
        original_filename="siddharth_cv.pdf",
        stored_filename="safe_uuid_siddharth.pdf",
        extracted_text="Siddharth Mehta | Python FastAPI SQLAlchemy",
        extracted_metadata={
            "full_name": "Siddharth Mehta",
            "skills": ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"],
            "experience": "3 years",
        },
    )
    db_session.add(resume)

    challenge = OTPChallenge(
        user_id=user_id,
        channel="email",
        otp_hash=hash_otp("123456", salt=f"{user_id}:email"),
        expires_at=user.created_at,
        attempts=0,
        verified=False,
    )
    db_session.add(challenge)
    await db_session.commit()

    # 2. Read User & JSONB fields
    fetched = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert fetched.full_name == "Siddharth Mehta"
    assert fetched.skills == ["Python", "FastAPI", "SQLAlchemy", "PostgreSQL"]

    # 3. Update verification status & Activate User
    fetched.is_email_verified = True
    fetched.is_whatsapp_verified = True
    fetched.is_totp_enabled = True
    fetched.is_active = True
    await db_session.commit()

    # 4. Verify Transaction Rollback on Error
    fetched.full_name = "Uncommitted Name Change"
    await db_session.flush()
    await db_session.rollback()

    after_rollback = (
        await db_session.execute(select(User).where(User.id == user_id))
    ).scalar_one()
    assert after_rollback.full_name == "Siddharth Mehta"
    assert after_rollback.is_active is True


# ============================================================================
# TASK 4: EMAIL OTP INTEGRATION (SMTP MESSAGE, COOLDOWN, ERROR HANDLING)
# ============================================================================


@pytest.mark.asyncio
async def test_email_smtp_message_generation_and_cooldown(client: AsyncClient):
    # Register user
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Kavya Krishnan",
            "email": "kavya@skillverse.edu",
            "phone": "9765432109",
            "skills": ["Python"],
            "password": "KavyaPassword#123",
            "confirm_password": "KavyaPassword#123",
        },
    )
    user_id = reg.json()["user_id"]

    # First OTP send succeeds (mock mode explicitly reports delivered=False, is_simulated=True)
    send1 = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "email"},
    )
    assert send1.status_code == 200
    send1_data = send1.json()
    assert send1_data["delivery_mode"] == "mock"
    assert send1_data["delivered"] is False
    assert send1_data["is_simulated"] is True
    assert "[MOCK MODE - NO REAL EMAIL SENT]" in send1_data["message"]

    # Immediate second OTP send within 30s cooldown is blocked with 429
    send2 = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "email"},
    )
    assert send2.status_code == 429
    assert send2.json()["error_code"] == "RESEND_COOLDOWN_ACTIVE"

    # Verify live SMTP adapter message construction & error handling
    settings = get_settings()
    service = EmailService()
    with patch("smtplib.SMTP") as mock_smtp_cls:
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__.return_value = mock_server
        with patch.object(settings, "EMAIL_PROVIDER_MODE", "smtp"), patch.object(
            settings, "SMTP_HOST", "smtp.example.org"
        ), patch.object(settings, "SMTP_PORT", 587), patch.object(
            settings, "SMTP_USERNAME", "smtp_user"
        ), patch.object(
            settings, "SMTP_PASSWORD", "smtp_secret"
        ):
            res = await service.send_otp_email(
                recipient_email="kavya@skillverse.edu",
                full_name="Kavya Krishnan",
                otp_code="654321",
            )
            assert res.delivered is True
            assert res.delivery_mode == "smtp"
            assert res.dev_otp_preview is None
            mock_server.starttls.assert_called_once()
            mock_server.login.assert_called_once_with("smtp_user", "smtp_secret")
            sent_msg = mock_server.send_message.call_args[0][0]
            assert sent_msg["To"] == "kavya@skillverse.edu"
            assert "654321" in sent_msg.get_content()

            # Simulate SMTP connection error -> raises ExternalProviderError
            mock_server.send_message.side_effect = RuntimeError("SMTP socket closed")
            with pytest.raises(ExternalProviderError):
                await service.send_otp_email(
                    recipient_email="kavya@skillverse.edu",
                    full_name="Kavya Krishnan",
                    otp_code="654321",
                )


# ============================================================================
# TASK 5: WHATSAPP CLOUD API ADAPTER VERIFICATION
# ============================================================================


@pytest.mark.asyncio
async def test_whatsapp_cloud_api_adapter_payload_and_error_handling():
    settings = get_settings()
    adapter = WhatsAppCloudAPIAdapter()

    with patch.object(settings, "WHATSAPP_ACCESS_TOKEN", "test_meta_bearer_token"), patch.object(
        settings, "WHATSAPP_PHONE_NUMBER_ID", "10987654321"
    ), patch.object(settings, "WHATSAPP_API_VERSION", "v20.0"):
        mock_post = AsyncMock(
            return_value=httpx.Response(200, json={"messages": [{"id": "wamid.123"}]})
        )
        with patch("httpx.AsyncClient.post", mock_post):
            result = await adapter.send_otp("+919876543210", "889900")
            assert result.delivered is True
            assert result.delivery_mode == "cloud"
            assert result.dev_otp_preview is None

            called_url = mock_post.call_args[0][0]
            called_kwargs = mock_post.call_args[1]
            assert called_url == "https://graph.facebook.com/v20.0/10987654321/messages"
            assert called_kwargs["headers"]["Authorization"] == "Bearer test_meta_bearer_token"
            assert called_kwargs["json"]["to"] == "919876543210"
            assert "889900" in called_kwargs["json"]["text"]["body"]

        # Verify HTTP 400+ from Meta Cloud API raises ExternalProviderError
        mock_fail_post = AsyncMock(
            return_value=httpx.Response(401, json={"error": {"message": "Invalid OAuth token"}})
        )
        with patch("httpx.AsyncClient.post", mock_fail_post):
            with pytest.raises(ExternalProviderError):
                await adapter.send_otp("+919876543210", "889900")


# ============================================================================
# TASK 6 & 8: SCANNED PDF DETECTION, PATH TRAVERSAL & OTP HASH SECURITY
# ============================================================================


@pytest.mark.asyncio
async def test_scanned_pdf_detection_and_security_controls(client: AsyncClient):
    scanned_bytes = create_scanned_image_only_pdf_bytes()
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("scanned_resume.pdf", scanned_bytes, "application/pdf")},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "SCANNED_PDF_NEEDS_OCR"

    # Path traversal sanitization check
    safe_name = sanitize_original_filename("../../etc/shadow/../../candidate_cv.pdf")
    assert safe_name == "candidate_cv.pdf"
    assert ".." not in safe_name
    assert "/" not in safe_name

    # OTP hash storage verification
    raw_otp = "492817"
    digest = hash_otp(raw_otp, salt="user-1:email")
    assert digest != raw_otp
    assert len(digest) == 64
    assert verify_otp_hash(raw_otp, digest, salt="user-1:email") is True
    assert verify_otp_hash("000000", digest, salt="user-1:email") is False


# ============================================================================
# TASK 1 AUDIT: SPECIAL CHARACTER PASSWORD HANDLING (@, #, :, /, %, +, SPACES)
# ============================================================================


@pytest.mark.parametrize(
    "case_label,synthetic_password,percent_encoded_password",
    [
        ("at_sign", "synth@pass!1", "synth%40pass%211"),
        ("hash_sign", "synth#pass!2", "synth%23pass%212"),
        ("colon_sign", "synth:pass!3", "synth%3Apass%213"),
        ("slash_sign", "synth/pass!4", "synth%2Fpass%214"),
        ("percent_sign", "synth%pass!5", "synth%25pass%215"),
        ("plus_sign", "synth+pass!6", "synth%2Bpass%216"),
        ("spaces", "synth space pass 7", "synth%20space%20pass%207"),
        (
            "combined_all_special_chars",
            "S@y#n:t/h%p+a s s!8",
            "S%40y%23n%3At%2Fh%25p%2Ba%20s%20s%218",
        ),
    ],
)
def test_postgres_url_special_characters_handling(
    case_label: str, synthetic_password: str, percent_encoded_password: str
):
    # 1. Construct via separate POSTGRES_USER, POSTGRES_PASSWORD, etc. (uses URL.create)
    s_separate = Settings(
        POSTGRES_USER="test_user",
        POSTGRES_PASSWORD=synthetic_password,
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5432,
        POSTGRES_DB="edtech_onboarding",
    )
    parsed_sep = make_url(s_separate.DATABASE_URL)
    assert parsed_sep.username == "test_user"
    assert parsed_sep.password == synthetic_password, f"Failed URL.create for {case_label}"
    assert (
        s_separate.masked_database_url
        == "postgresql+asyncpg://test_user:***@localhost:5432/edtech_onboarding"
    )
    assert synthetic_password not in s_separate.masked_database_url

    # 2. Construct via already percent-encoded DATABASE_URL (must NOT double-encode)
    encoded_input_url = (
        f"postgresql+asyncpg://test_user:{percent_encoded_password}"
        "@localhost:5432/edtech_onboarding"
    )
    normalized_from_encoded = normalize_postgres_asyncpg_url(encoded_input_url)
    parsed_enc = make_url(normalized_from_encoded)
    assert parsed_enc.password == synthetic_password, (
        f"Double-encoding or corruption on percent-encoded input for {case_label}"
    )
    assert (
        parsed_enc.render_as_string(hide_password=True)
        == "postgresql+asyncpg://test_user:***@localhost:5432/edtech_onboarding"
    )

    # 3. Construct via raw unencoded DATABASE_URL (including literal '+', spaces, '@', '#', ':', '/', '%')
    raw_input_url = (
        f"postgresql+asyncpg://test_user:{synthetic_password}"
        "@localhost:5432/edtech_onboarding"
    )
    normalized_from_raw = normalize_postgres_asyncpg_url(raw_input_url)
    parsed_raw = make_url(normalized_from_raw)
    assert parsed_raw.password == synthetic_password, (
        f"Corruption on raw DATABASE_URL input for {case_label}"
    )
    assert (
        parsed_raw.render_as_string(hide_password=True)
        == "postgresql+asyncpg://test_user:***@localhost:5432/edtech_onboarding"
    )


# ============================================================================
# CONFIGURATION & MOCK VS LIVE DELIVERY SAFEGUARD UNIT TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_configuration_validation_and_mock_safeguards():
    # 1. Confirm DATABASE_URL rejects SQLite fallback in Settings
    with pytest.raises(ValidationError):
        Settings(DATABASE_URL="sqlite+aiosqlite:///./fallback.db")

    # 2. Confirm JWT_SECRET_KEY rejects short or placeholder values
    with pytest.raises(ValidationError):
        Settings(JWT_SECRET_KEY="short-secret")
    with pytest.raises(ValidationError):
        Settings(
            JWT_SECRET_KEY="change-this-to-a-cryptographically-secure-256-bit-secret-key-in-prod"
        )

    # 3. Confirm TOTP_ENCRYPTION_KEY rejects invalid Fernet key
    with pytest.raises(ValidationError):
        Settings(TOTP_ENCRYPTION_KEY="not-a-valid-fernet-key")

    # 4. Confirm EMAIL_PROVIDER_MODE and WHATSAPP_PROVIDER_MODE validation
    with pytest.raises(ValidationError):
        Settings(EMAIL_PROVIDER_MODE="invalid_mode")
    with pytest.raises(ValidationError):
        Settings(WHATSAPP_PROVIDER_MODE="invalid_mode")

    # 5. Confirm .env and .env.example variable names match Settings.model_fields
    root_dir = Path(__file__).resolve().parent.parent.parent
    cfg_fields = set(Settings.model_fields.keys())
    for filename in (".env", ".env.example"):
        env_path = root_dir / filename
        if env_path.exists():
            keys = {
                line.split("=", 1)[0].strip()
                for line in env_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#") and "=" in line
            }
            assert keys.issubset(cfg_fields), (
                f"Unrecognized variable names in {filename}: {keys - cfg_fields}"
            )

    # 6. Confirm EMAIL_PROVIDER_MODE=smtp without credentials raises ExternalProviderError (no silent mock fallback)
    settings = get_settings()
    email_svc = EmailService()
    with patch.object(settings, "EMAIL_PROVIDER_MODE", "smtp"), patch.object(
        settings, "SMTP_USERNAME", ""
    ), patch.object(settings, "SMTP_PASSWORD", ""):
        with pytest.raises(ExternalProviderError):
            await email_svc.send_otp_email("user@example.com", "User", "123456")


