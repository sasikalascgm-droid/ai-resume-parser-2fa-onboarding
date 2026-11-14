from datetime import datetime, timedelta, timezone

import pyotp
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    decrypt_totp_secret,
    verify_password,
)
from app.models.otp_challenge import OTPChallenge
from app.models.user import User
from app.models.user_resume import UserResume
from tests.conftest import (
    create_sample_docx_bytes,
    create_sample_pdf_bytes,
    create_scanned_pdf_bytes_from_pages,
)


# ============================================================================
# 1. RESUME PARSING WORKFLOW TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_resume_parse_pdf_success(client: AsyncClient):
    pdf_bytes = create_sample_pdf_bytes(
        [
            "Aarav Sharma",
            "Email: aarav.sharma@example.com",
            "Phone: +91 9876543210",
            "Qualification: B.Tech in Computer Science",
            "Experience: 3 years of experience",
            "Skills: Python, FastAPI, PostgreSQL, React, Docker",
        ]
    )
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("aarav_resume.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["resume_id"]
    extracted = data["extracted_data"]
    assert extracted["full_name"] == "Aarav Sharma"
    assert extracted["email"] == "aarav.sharma@example.com"
    assert "9876543210" in extracted["phone"]
    assert "Python" in extracted["skills"]
    assert "FastAPI" in extracted["skills"]
    assert "PostgreSQL" in extracted["skills"]
    assert extracted["experience"] is not None
    assert "B.Tech" in extracted["qualification"]


@pytest.mark.asyncio
async def test_resume_parse_docx_success(client: AsyncClient):
    docx_bytes = create_sample_docx_bytes(
        [
            "Priya Nair",
            "priya.nair@edtech.org",
            "9123456789",
            "Education: M.Tech in Data Science",
            "Work Experience: 2 years",
            "Technical Skills: Python, SQL, Machine Learning, PyTorch",
        ]
    )
    response = await client.post(
        "/api/v1/resume/parse",
        files={
            "file": (
                "priya_resume.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    extracted = data["extracted_data"]
    assert extracted["full_name"] == "Priya Nair"
    assert extracted["email"] == "priya.nair@edtech.org"
    assert extracted["phone"] == "9123456789"
    assert "Python" in extracted["skills"]
    assert "SQL" in extracted["skills"]
    assert "2 years" in extracted["experience"]
    assert "M.Tech" in extracted["qualification"]


@pytest.mark.asyncio
async def test_resume_parse_invalid_format(client: AsyncClient):
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("malicious.exe", b"MZ\x90\x00", "application/octet-stream")},
    )
    assert response.status_code == 415
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "UNSUPPORTED_FORMAT"


@pytest.mark.asyncio
async def test_resume_parse_empty_file(client: AsyncClient):
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )
    assert response.status_code == 400
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "EMPTY_FILE"


@pytest.mark.asyncio
async def test_resume_parse_corrupted_document(client: AsyncClient):
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("corrupted.pdf", b"%PDF-1.7 broken binary garbage", "application/pdf")},
    )
    assert response.status_code == 422
    data = response.json()
    assert data["success"] is False
    assert data["error_code"] == "CORRUPTED_FILE"


@pytest.mark.asyncio
async def test_resume_parse_missing_candidate_details_never_fabricates(client: AsyncClient):
    docx_bytes = create_sample_docx_bytes(
        [
            "General Notes",
            "Completed coursework in software engineering.",
        ]
    )
    response = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("minimal.docx", docx_bytes, "application/octet-stream")},
    )
    assert response.status_code == 200
    extracted = response.json()["extracted_data"]
    assert extracted["email"] is None
    assert extracted["phone"] is None
    assert extracted["skills"] == []
    assert extracted["experience"] is None
    assert extracted["qualification"] is None


# ============================================================================
# 2. REGISTRATION & PASSWORD SECURITY TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_registration_valid_and_argon2id_hash(
    client: AsyncClient, db_session: AsyncSession
):
    payload = {
        "full_name": "Rohan Verma",
        "email": "rohan.verma@example.com",
        "phone": "9876501234",
        "skills": ["Python", "FastAPI"],
        "experience": "1 year",
        "qualification": "B.Tech",
        "password": "StrongPassword@123",
        "confirm_password": "StrongPassword@123",
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["success"] is True
    assert data["is_active"] is False

    # Verify Argon2id hash in database and ensure plaintext password is never stored
    stmt = select(User).where(User.id == data["user_id"])
    user = (await db_session.execute(stmt)).scalar_one()
    assert user.hashed_password != "StrongPassword@123"
    assert user.hashed_password.startswith("$argon2id$")
    assert verify_password("StrongPassword@123", user.hashed_password) is True
    assert user.is_active is False


@pytest.mark.asyncio
async def test_registration_duplicate_email_and_phone(client: AsyncClient):
    base_payload = {
        "full_name": "Ananya Gupta",
        "email": "ananya@example.com",
        "phone": "9988776655",
        "skills": ["React"],
        "experience": "2 years",
        "qualification": "B.E.",
        "password": "SecurePassword#2026",
        "confirm_password": "SecurePassword#2026",
    }
    res1 = await client.post("/api/v1/auth/register", json=base_payload)
    assert res1.status_code == 201

    # Duplicate email
    dup_email_payload = {**base_payload, "phone": "9988770000"}
    res_dup_email = await client.post("/api/v1/auth/register", json=dup_email_payload)
    assert res_dup_email.status_code == 409
    assert res_dup_email.json()["error_code"] == "DUPLICATE_EMAIL"

    # Duplicate phone
    dup_phone_payload = {**base_payload, "email": "ananya2@example.com"}
    res_dup_phone = await client.post("/api/v1/auth/register", json=dup_phone_payload)
    assert res_dup_phone.status_code == 409
    assert res_dup_phone.json()["error_code"] == "DUPLICATE_PHONE"


@pytest.mark.asyncio
async def test_registration_weak_password_and_mismatch(client: AsyncClient):
    weak_payload = {
        "full_name": "Weak Pass User",
        "email": "weak@example.com",
        "phone": "9111222333",
        "skills": [],
        "password": "weakpassword",
        "confirm_password": "weakpassword",
    }
    res_weak = await client.post("/api/v1/auth/register", json=weak_payload)
    assert res_weak.status_code == 422

    mismatch_payload = {
        **weak_payload,
        "password": "ValidPassword@123",
        "confirm_password": "DifferentPassword@123",
    }
    res_mismatch = await client.post("/api/v1/auth/register", json=mismatch_payload)
    assert res_mismatch.status_code == 422


# ============================================================================
# 3. MULTI-CHANNEL 2FA TESTS (EMAIL, WHATSAPP, TOTP, EXPIRY, ATTEMPTS, REUSE)
# ============================================================================


async def _register_test_user(client: AsyncClient, email: str, phone: str) -> str:
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Test Candidate",
            "email": email,
            "phone": phone,
            "skills": ["Python", "SQL"],
            "experience": "2 years",
            "qualification": "B.Tech",
            "password": "ValidPassword@123",
            "confirm_password": "ValidPassword@123",
        },
    )
    assert res.status_code == 201
    return res.json()["user_id"]


@pytest.mark.asyncio
async def test_2fa_email_whatsapp_totp_and_activation_tracking(
    client: AsyncClient, db_session: AsyncSession
):
    user_id = await _register_test_user(client, "verify@example.com", "9811122233")

    # 1. Send & Verify Email OTP
    send_email = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "email"},
    )
    assert send_email.status_code == 200
    email_otp = send_email.json()["dev_otp_preview"]
    assert len(email_otp) == 6

    verify_email = await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "email", "otp": email_otp},
    )
    assert verify_email.status_code == 200
    v_email_data = verify_email.json()
    assert v_email_data["is_email_verified"] is True
    assert v_email_data["is_whatsapp_verified"] is False
    assert v_email_data["is_totp_enabled"] is False
    assert v_email_data["is_active"] is False

    # Prevent OTP Reuse
    reuse_res = await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "email", "otp": email_otp},
    )
    assert reuse_res.status_code == 400
    assert reuse_res.json()["error_code"] == "OTP_ALREADY_USED"

    # 2. Send & Verify WhatsApp OTP
    send_wa = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "whatsapp"},
    )
    assert send_wa.status_code == 200
    wa_otp = send_wa.json()["dev_otp_preview"]

    verify_wa = await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "whatsapp", "otp": wa_otp},
    )
    assert verify_wa.status_code == 200
    v_wa_data = verify_wa.json()
    assert v_wa_data["is_whatsapp_verified"] is True
    assert v_wa_data["is_active"] is False

    # 3. Setup & Verify Browser TOTP (and verify regeneration invalidates previous secret)
    setup_totp_first = await client.post(
        "/api/v1/auth/totp/setup",
        json={"user_id": user_id},
    )
    assert setup_totp_first.status_code == 200
    first_totp_data = setup_totp_first.json()
    assert first_totp_data["success"] is True
    assert first_totp_data["qr_code_data_url"].startswith("data:image/png;base64,")
    assert first_totp_data["is_totp_enabled"] is False
    assert "manual_entry_key" not in first_totp_data
    assert "provisioning_uri" not in first_totp_data
    assert "secret" not in first_totp_data

    stmt = select(User).where(User.id == user_id)
    user_db = (await db_session.execute(stmt)).scalar_one()
    await db_session.refresh(user_db)
    first_secret = decrypt_totp_secret(user_db.totp_secret_encrypted)

    # Regenerate TOTP secret and confirm a new secret is generated and encrypted at rest
    setup_totp = await client.post(
        "/api/v1/auth/totp/setup",
        json={"user_id": user_id},
    )
    assert setup_totp.status_code == 200
    totp_data = setup_totp.json()
    assert totp_data["success"] is True
    assert totp_data["qr_code_data_url"].startswith("data:image/png;base64,")
    assert "manual_entry_key" not in totp_data
    assert "provisioning_uri" not in totp_data
    assert "secret" not in totp_data

    await db_session.refresh(user_db)
    secret = decrypt_totp_secret(user_db.totp_secret_encrypted)
    assert user_db.totp_secret_encrypted != secret
    assert secret != first_secret

    # Generate valid TOTP code
    totp_code = pyotp.TOTP(secret).now()
    verify_totp = await client.post(
        "/api/v1/auth/totp/verify",
        json={"user_id": user_id, "otp": totp_code},
    )
    assert verify_totp.status_code == 200
    final_data = verify_totp.json()
    assert final_data["is_totp_enabled"] is True
    assert final_data["is_active"] is True
    assert final_data["access_token"] is not None


@pytest.mark.asyncio
async def test_2fa_expired_otp_and_max_attempts(
    client: AsyncClient, db_session: AsyncSession
):
    user_id = await _register_test_user(client, "attempts@example.com", "9844455566")

    # Send Email OTP
    send_res = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "email"},
    )
    assert send_res.status_code == 200

    # Test 5 invalid attempts -> locks challenge
    for attempt in range(5):
        bad_res = await client.post(
            "/api/v1/auth/verify-2fa",
            json={"user_id": user_id, "channel": "email", "otp": "000000"},
        )
        if attempt < 4:
            assert bad_res.status_code == 400
            assert bad_res.json()["error_code"] == "INVALID_OTP"
        else:
            assert bad_res.status_code == 429
            assert bad_res.json()["error_code"] == "MAX_ATTEMPTS_EXCEEDED"

    # Test Expired OTP on WhatsApp channel
    send_wa = await client.post(
        "/api/v1/auth/send-otp",
        json={"user_id": user_id, "channel": "whatsapp"},
    )
    assert send_wa.status_code == 200
    wa_otp = send_wa.json()["dev_otp_preview"]

    # Force expiration in DB
    stmt = select(OTPChallenge).where(
        OTPChallenge.user_id == user_id,
        OTPChallenge.channel == "whatsapp",
    )
    challenge = (await db_session.execute(stmt)).scalar_one()
    challenge.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    await db_session.commit()

    exp_res = await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "whatsapp", "otp": wa_otp},
    )
    assert exp_res.status_code == 400
    assert exp_res.json()["error_code"] == "OTP_EXPIRED"


# ============================================================================
# 4. JWT AUTHENTICATION, PROFILE, AND STUDENT DASHBOARD TESTS
# ============================================================================


@pytest.mark.asyncio
async def test_jwt_validation_inactive_rejection_and_end_to_end_lifecycle(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Upload Resume
    pdf_bytes = create_sample_pdf_bytes(
        [
            "Meera Krishnan",
            "meera.k@example.com",
            "9822334455",
            "Qualification: B.Tech",
            "Experience: 4 years",
            "Skills: Python, FastAPI, React, TypeScript",
        ]
    )
    parse_res = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("meera_cv.pdf", pdf_bytes, "application/pdf")},
    )
    assert parse_res.status_code == 200
    parsed = parse_res.json()
    resume_id = parsed["resume_id"]

    # 2. Register Staged Account
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "full_name": parsed["extracted_data"]["full_name"],
            "email": parsed["extracted_data"]["email"],
            "phone": parsed["extracted_data"]["phone"],
            "skills": parsed["extracted_data"]["skills"],
            "experience": parsed["extracted_data"]["experience"],
            "qualification": parsed["extracted_data"]["qualification"],
            "password": "MeeraSecure#2026",
            "confirm_password": "MeeraSecure#2026",
            "resume_id": resume_id,
        },
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user_id"]

    # 3. Verify that an inactive user with a valid JWT is rejected (403) from Profile & Dashboard
    inactive_token = create_access_token(subject=user_id)
    inactive_dash = await client.get(
        "/api/v1/dashboard/student",
        headers={"Authorization": f"Bearer {inactive_token}"},
    )
    assert inactive_dash.status_code == 403
    assert inactive_dash.json()["error_code"] == "ACCOUNT_INACTIVE_OR_UNVERIFIED"

    # 4. Verify Unauthorized (no token, invalid token, expired token) -> 401
    unauth_res = await client.get("/api/v1/profile")
    assert unauth_res.status_code == 401

    invalid_res = await client.get(
        "/api/v1/profile",
        headers={"Authorization": "Bearer malformed.jwt.token"},
    )
    assert invalid_res.status_code == 401

    expired_token = create_access_token(
        subject=user_id, expires_delta=timedelta(seconds=-10)
    )
    expired_res = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {expired_token}"},
    )
    assert expired_res.status_code == 401
    assert expired_res.json()["error_code"] == "TOKEN_EXPIRED"

    # 5. Complete all 3 2FA channels
    e_otp = (
        await client.post(
            "/api/v1/auth/send-otp", json={"user_id": user_id, "channel": "email"}
        )
    ).json()["dev_otp_preview"]
    await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "email", "otp": e_otp},
    )

    w_otp = (
        await client.post(
            "/api/v1/auth/send-otp", json={"user_id": user_id, "channel": "whatsapp"}
        )
    ).json()["dev_otp_preview"]
    await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "whatsapp", "otp": w_otp},
    )

    totp_setup_res = await client.post("/api/v1/auth/totp/setup", json={"user_id": user_id})
    assert totp_setup_res.status_code == 200
    totp_setup_json = totp_setup_res.json()
    assert totp_setup_json["qr_code_data_url"].startswith("data:image/png;base64,")
    assert "manual_entry_key" not in totp_setup_json
    assert "provisioning_uri" not in totp_setup_json

    user_row = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    await db_session.refresh(user_row)
    totp_secret = decrypt_totp_secret(user_row.totp_secret_encrypted)
    totp_verify_res = await client.post(
        "/api/v1/auth/totp/verify",
        json={"user_id": user_id, "otp": pyotp.TOTP(totp_secret).now()},
    )
    assert totp_verify_res.status_code == 200
    active_token = totp_verify_res.json()["access_token"]
    assert active_token

    # 6. Get Profile & Ensure no sensitive fields are leaked
    prof_res = await client.get(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {active_token}"},
    )
    assert prof_res.status_code == 200
    prof_data = prof_res.json()
    assert prof_data["full_name"] == "Meera Krishnan"
    assert prof_data["latest_resume"]["original_filename"] == "meera_cv.pdf"
    assert "hashed_password" not in prof_data
    assert "totp_secret_encrypted" not in prof_data

    # 7. Attempt to modify sensitive verification flags via PATCH /api/v1/profile -> 422 Forbidden extra field
    tamper_res = await client.patch(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {active_token}"},
        json={"full_name": "Meera K", "is_email_verified": False},
    )
    assert tamper_res.status_code == 422

    # 8. Valid Profile Update
    update_res = await client.patch(
        "/api/v1/profile",
        headers={"Authorization": f"Bearer {active_token}"},
        json={
            "full_name": "Meera Krishnan Iyer",
            "skills": ["Python", "FastAPI", "React", "TypeScript", "PostgreSQL"],
            "experience": "4.5 years",
            "qualification": "M.Tech in Software Systems",
        },
    )
    assert update_res.status_code == 200
    assert update_res.json()["full_name"] == "Meera Krishnan Iyer"
    assert "PostgreSQL" in update_res.json()["skills"]

    # 9. Access Student Dashboard
    dash_res = await client.get(
        "/api/v1/dashboard/student",
        headers={"Authorization": f"Bearer {active_token}"},
    )
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert dash_data["user_id"] == user_id
    assert dash_data["is_active"] is True
    assert dash_data["dashboard_route"] == "/dashboard/student"
    assert dash_data["profile_completion_percentage"] == 100
    assert dash_data["verification_status"]["all_required_verified"] is True

    # 10. Logout revokes token
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {active_token}"},
    )
    assert logout_res.status_code == 200

    after_logout_res = await client.get(
        "/api/v1/dashboard/student",
        headers={"Authorization": f"Bearer {active_token}"},
    )
    assert after_logout_res.status_code == 401
    assert after_logout_res.json()["error_code"] == "TOKEN_REVOKED"


@pytest.mark.asyncio
async def test_resume_linking_synchronization_multiple_uploads_and_preview_security(
    client: AsyncClient, db_session: AsyncSession
):
    # 1. Register and activate candidate account via legitimate 2FA flow
    user_id = await _register_test_user(client, "sync.candidate@example.com", "9877665544")

    # Verify that an unauthenticated upload with the same email/phone is NOT auto-matched by email/phone alone
    unauth_pdf = create_sample_pdf_bytes(
        [
            "Kiran Deshmukh",
            "Email: sync.candidate@example.com",
            "Phone: 9877665544",
            "Qualification: B.Tech in Information Technology",
            "Experience: 3 years",
            "Skills: Python, FastAPI, PostgreSQL, Docker, Kubernetes",
        ]
    )
    unauth_parse = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("kiran_v1.pdf", unauth_pdf, "application/pdf")},
    )
    assert unauth_parse.status_code == 200
    resume_v1_id = unauth_parse.json()["resume_id"]

    r1_db = (await db_session.execute(select(UserResume).where(UserResume.id == resume_v1_id))).scalar_one()
    assert r1_db.user_id is None  # Never matched by email/phone alone

    # Unauthenticated and inactive requests to resume preview/download must be rejected
    unauth_preview = await client.get(f"/api/v1/resume/{resume_v1_id}/file")
    assert unauth_preview.status_code == 401

    inactive_token = create_access_token(subject=user_id)
    inactive_preview = await client.get(
        f"/api/v1/resume/{resume_v1_id}/file",
        headers={"Authorization": f"Bearer {inactive_token}"},
    )
    assert inactive_preview.status_code == 403

    # Complete all 3 2FA channels to legitimately activate the account
    e_otp = (
        await client.post(
            "/api/v1/auth/send-otp", json={"user_id": user_id, "channel": "email"}
        )
    ).json()["dev_otp_preview"]
    await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "email", "otp": e_otp},
    )

    w_otp = (
        await client.post(
            "/api/v1/auth/send-otp", json={"user_id": user_id, "channel": "whatsapp"}
        )
    ).json()["dev_otp_preview"]
    await client.post(
        "/api/v1/auth/verify-2fa",
        json={"user_id": user_id, "channel": "whatsapp", "otp": w_otp},
    )

    await client.post("/api/v1/auth/totp/setup", json={"user_id": user_id})
    user_row = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    await db_session.refresh(user_row)
    totp_secret = decrypt_totp_secret(user_row.totp_secret_encrypted)
    totp_res = await client.post(
        "/api/v1/auth/totp/verify",
        json={"user_id": user_id, "otp": pyotp.TOTP(totp_secret).now()},
    )
    assert totp_res.status_code == 200
    token = totp_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Associate resume_v1 via authenticated endpoint and verify profile & dashboard synchronization
    assoc_res = await client.post(f"/api/v1/resume/{resume_v1_id}/associate", headers=headers)
    assert assoc_res.status_code == 200

    await db_session.refresh(r1_db)
    assert r1_db.user_id == user_id

    prof_v1 = (await client.get("/api/v1/profile", headers=headers)).json()
    dash_v1 = (await client.get("/api/v1/dashboard/student", headers=headers)).json()
    assert prof_v1["full_name"] == "Kiran Deshmukh"
    assert dash_v1["full_name"] == "Kiran Deshmukh"
    assert prof_v1["skills"] == dash_v1["skills"]
    assert "Kubernetes" in prof_v1["skills"]
    assert prof_v1["experience"] == dash_v1["experience"] == "3 years"
    assert "B.Tech" in prof_v1["qualification"]
    assert prof_v1["qualification"] == dash_v1["qualification"]
    assert prof_v1["latest_resume"]["id"] == resume_v1_id
    assert dash_v1["latest_resume"]["id"] == resume_v1_id
    assert prof_v1["profile_completion"] == 100
    assert dash_v1["profile_completion_percentage"] == 100

    # 3. Upload a second resume with empty experience/qualification while authenticated:
    # must NOT overwrite existing non-empty experience/qualification with empty values,
    # must preserve the first resume record, and must update latest_resume to the new resume.
    minimal_pdf = create_sample_pdf_bytes(
        [
            "Kiran Deshmukh",
            "Skills: Python, FastAPI, PostgreSQL, GraphQL",
        ]
    )
    parse_v2 = await client.post(
        "/api/v1/resume/parse",
        headers=headers,
        files={"file": ("kiran_v2.pdf", minimal_pdf, "application/pdf")},
    )
    assert parse_v2.status_code == 200
    resume_v2_id = parse_v2.json()["resume_id"]
    assert resume_v2_id != resume_v1_id

    # Re-uploading the exact same file while authenticated avoids creating a duplicate record
    parse_v2_dup = await client.post(
        "/api/v1/resume/parse",
        headers=headers,
        files={"file": ("kiran_v2.pdf", minimal_pdf, "application/pdf")},
    )
    assert parse_v2_dup.status_code == 200
    assert parse_v2_dup.json()["resume_id"] == resume_v2_id

    # Verify both v1 and v2 are preserved in PostgreSQL user_resumes
    user_resumes = (
        await db_session.execute(select(UserResume).where(UserResume.user_id == user_id))
    ).scalars().all()
    assert len(user_resumes) == 2

    # Verify existing experience and qualification were NOT overwritten by empty fields
    prof_v2 = (await client.get("/api/v1/profile", headers=headers)).json()
    dash_v2 = (await client.get("/api/v1/dashboard/student", headers=headers)).json()
    assert prof_v2["experience"] == "3 years"
    assert "B.Tech" in prof_v2["qualification"]
    assert "GraphQL" in prof_v2["skills"]
    assert prof_v2["latest_resume"]["id"] == resume_v2_id
    assert dash_v2["latest_resume"]["id"] == resume_v2_id

    # 4. Verify resume preview and download endpoints for authenticated active owner
    meta_res = await client.get(f"/api/v1/resume/{resume_v2_id}", headers=headers)
    assert meta_res.status_code == 200
    assert meta_res.json()["original_filename"] == "kiran_v2.pdf"

    file_inline = await client.get(f"/api/v1/resume/{resume_v2_id}/file", headers=headers)
    assert file_inline.status_code == 200
    assert file_inline.headers["content-type"] == "application/pdf"
    assert "inline" in file_inline.headers["content-disposition"]

    file_download = await client.get(
        f"/api/v1/resume/{resume_v2_id}/file?download=true", headers=headers
    )
    assert file_download.status_code == 200
    assert "attachment" in file_download.headers["content-disposition"]


@pytest.mark.asyncio
async def test_totp_drift_window_ntp_reference_and_replay_protection(
    client: AsyncClient, db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
):
    user_id = await _register_test_user(client, "totp.drift@example.com", "9811223344")

    setup_res = await client.post(
        "/api/v1/auth/totp/setup",
        json={"user_id": user_id},
    )
    assert setup_res.status_code == 200

    user_db = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    await db_session.refresh(user_db)
    secret = decrypt_totp_secret(user_db.totp_secret_encrypted)
    totp = pyotp.TOTP(secret)

    # 1. Code outside valid_window (+90 seconds = +3 steps) must be rejected
    far_future_code = totp.at(datetime.now(timezone.utc) + timedelta(seconds=90))
    if far_future_code != totp.now():
        bad_res = await client.post(
            "/api/v1/auth/totp/verify",
            json={"user_id": user_id, "otp": far_future_code},
        )
        assert bad_res.status_code == 400
        assert bad_res.json()["error_code"] == "INVALID_TOTP"

    # 2. Simulate 12-hour host clock skew relative to NTP (Google Authenticator on mobile uses NTP time)
    simulated_ntp_time = datetime.now(timezone.utc) + timedelta(hours=12)
    monkeypatch.setattr(
        "app.services.totp_service._get_verification_reference_times",
        lambda: [simulated_ntp_time, datetime.now(timezone.utc)],
    )

    # Code from mobile Google Authenticator at NTP time (-30s drift step) must be accepted
    mobile_code = totp.at(simulated_ntp_time - timedelta(seconds=30))
    ok_res = await client.post(
        "/api/v1/auth/totp/verify",
        json={"user_id": user_id, "otp": mobile_code},
    )
    assert ok_res.status_code == 200
    assert ok_res.json()["is_totp_enabled"] is True

    # 3. Replaying the exact same TOTP code within the 90s window must be rejected
    replay_res = await client.post(
        "/api/v1/auth/totp/verify",
        json={"user_id": user_id, "otp": mobile_code},
    )
    assert replay_res.status_code == 400
    assert replay_res.json()["error_code"] == "OTP_REPLAY_DETECTED"


@pytest.mark.asyncio
async def test_scanned_pdf_single_page_ocr_extraction(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    import pdfplumber
    import io as _io
    from app.services.resume_parser import _resolve_tesseract_executable

    page_lines = [
        "Rohan Kulkarni",
        "Email: rohan.kulkarni@example.com",
        "Phone: +91 9876501234",
        "Qualification: M.Tech in Computer Science",
        "Experience: 5 years of experience",
        "Skills: Python, FastAPI, PostgreSQL, Docker, React",
    ]
    scanned_pdf_bytes = create_scanned_pdf_bytes_from_pages([page_lines])

    # Confirm the generated PDF is genuinely image-only (zero machine-readable text in pdfplumber)
    with pdfplumber.open(_io.BytesIO(scanned_pdf_bytes)) as pdf:
        assert len(pdf.pages) == 1
        assert (pdf.pages[0].extract_text() or "").strip() == ""

    # If Tesseract binary is not installed in the test environment, mock image_to_string deterministically
    if _resolve_tesseract_executable() is None:
        monkeypatch.setattr(
            "pytesseract.image_to_string",
            lambda img, **kwargs: "\n".join(page_lines),
        )

    res = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("rohan_scanned_cv.pdf", scanned_pdf_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert any("OCR" in w for w in body["warnings"])
    ext = body["extracted_data"]
    assert ext["full_name"] == "Rohan Kulkarni"
    assert ext["email"] == "rohan.kulkarni@example.com"
    assert "9876501234" in ext["phone"]
    assert "M.Tech" in ext["qualification"]
    assert "5 years" in ext["experience"]
    assert "Python" in ext["skills"]
    assert "FastAPI" in ext["skills"]
    assert "PostgreSQL" in ext["skills"]


@pytest.mark.asyncio
async def test_scanned_pdf_multipage_ocr_extraction_and_page_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    from app.core.config import get_settings
    from app.services.resume_parser import _resolve_tesseract_executable

    page1_lines = [
        "Ananya Deshpande",
        "Email: ananya.d@example.com",
        "Phone: 9823456789",
        "Qualification: B.Tech in Information Technology",
    ]
    page2_lines = [
        "Professional Summary",
        "Experience: 4 years",
        "Skills: TypeScript, React, Node.js, PostgreSQL, AWS",
    ]
    page3_lines = [
        "Additional Appendix Page",
        "Skills: Kubernetes",
    ]
    multipage_scanned_bytes = create_scanned_pdf_bytes_from_pages(
        [page1_lines, page2_lines, page3_lines]
    )

    if _resolve_tesseract_executable() is None:
        call_idx = {"n": 0}
        pages_data = [page1_lines, page2_lines, page3_lines]

        def _fake_ocr(img, **kwargs):
            i = call_idx["n"]
            call_idx["n"] += 1
            return "\n".join(pages_data[min(i, len(pages_data) - 1)])

        monkeypatch.setattr("pytesseract.image_to_string", _fake_ocr)

    # Set OCR_MAX_PAGES=2 to verify multi-page aggregation (pages 1 & 2) and page limit warning
    settings = get_settings()
    monkeypatch.setattr(settings, "OCR_MAX_PAGES", 2)

    res = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("ananya_multipage_scan.pdf", multipage_scanned_bytes, "application/pdf")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert any("limited to the first 2 pages" in w for w in body["warnings"])
    ext = body["extracted_data"]
    assert ext["full_name"] == "Ananya Deshpande"
    assert ext["email"] == "ananya.d@example.com"
    assert "9823456789" in ext["phone"]
    assert "B.Tech" in ext["qualification"]
    assert "4 years" in ext["experience"]
    assert "TypeScript" in ext["skills"]
    assert "React" in ext["skills"]
    assert "PostgreSQL" in ext["skills"]


@pytest.mark.asyncio
async def test_scanned_pdf_ocr_unavailable_returns_actionable_error(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
):
    import pytesseract

    scanned_bytes = create_scanned_pdf_bytes_from_pages(
        [["Candidate Name", "Email: candidate@example.com"]]
    )

    def _raise_not_found(*args, **kwargs):
        raise pytesseract.TesseractNotFoundError()

    monkeypatch.setattr("pytesseract.image_to_string", _raise_not_found)

    res = await client.post(
        "/api/v1/resume/parse",
        files={"file": ("missing_ocr_scan.pdf", scanned_bytes, "application/pdf")},
    )
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error_code"] == "OCR_UNAVAILABLE"
    assert "Tesseract OCR" in data["message"]
