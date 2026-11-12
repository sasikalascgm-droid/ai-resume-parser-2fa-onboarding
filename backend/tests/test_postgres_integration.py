"""
Dedicated PostgreSQL 18 Integration Test Suite (Task 2).
Strictly uses postgresql+asyncpg:// from .env and NEVER falls back to SQLite.
"""
import subprocess
import uuid
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import PLACEHOLDER_PASSWORDS, get_settings
from app.core.security import hash_otp, hash_password
from app.models.otp_challenge import OTPChallenge
from app.models.user import User
from app.models.user_resume import UserResume
from app.services.resume_parser import resume_parser_service
from tests.conftest import create_sample_pdf_bytes

BACKEND_DIR = Path(__file__).resolve().parent.parent


def _get_verified_postgres_url() -> str:
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql+asyncpg://"):
        pytest.fail(
            "DATABASE_URL is not configured with postgresql+asyncpg://. "
            "PostgreSQL integration tests never fall back to SQLite."
        )
    u = make_url(db_url)
    if (
        not u.username
        or u.username.upper() == "USERNAME"
        or (u.password or "").upper() in PLACEHOLDER_PASSWORDS
    ):
        pytest.fail(
            "BLOCKED: PostgreSQL credentials in .env are still set to placeholder "
            "postgresql+asyncpg://USERNAME:PASSWORD@localhost:5432/edtech_onboarding. "
            "Please configure your local PostgreSQL username and password in .env."
        )
    return db_url


@pytest.mark.asyncio
async def test_postgres_connection_and_database_creation():
    db_url = _get_verified_postgres_url()
    u = make_url(db_url)
    target_db = u.database or "edtech_onboarding"

    conn = await asyncpg.connect(
        user=u.username,
        password=u.password,
        host=u.host or "localhost",
        port=u.port or 5432,
        database="postgres",
    )
    try:
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        if not exists:
            await conn.execute(f'CREATE DATABASE "{target_db}"')
        exists_after = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", target_db
        )
        assert exists_after == 1
    finally:
        await conn.close()


@pytest.mark.asyncio
async def test_postgres_alembic_migration_and_schema_verification():
    db_url = _get_verified_postgres_url()
    alembic_exe = BACKEND_DIR / ".venv" / "Scripts" / "alembic.exe"
    result = subprocess.run(
        [str(alembic_exe), "upgrade", "head"],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"Alembic migration failed: {result.stderr}"

    engine = create_async_engine(db_url, echo=False, future=True)
    try:
        async with engine.connect() as conn:
            assert conn.dialect.name == "postgresql"

            # 1. Verify all three tables
            tables_res = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                )
            )
            tables = {r[0] for r in tables_res.fetchall()}
            assert {"users", "user_resumes", "otp_challenges", "alembic_version"}.issubset(
                tables
            )

            # 2. Verify JSONB columns
            jsonb_res = await conn.execute(
                text(
                    "SELECT table_name, column_name, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND udt_name = 'jsonb'"
                )
            )
            jsonb_cols = {(r[0], r[1]) for r in jsonb_res.fetchall()}
            assert ("users", "skills") in jsonb_cols
            assert ("user_resumes", "extracted_metadata") in jsonb_cols

            # 3. Verify indexes & unique constraints
            idx_res = await conn.execute(
                text(
                    "SELECT indexname FROM pg_indexes WHERE schemaname = 'public'"
                )
            )
            indexes = {r[0] for r in idx_res.fetchall()}
            assert "uq_users_email" in indexes
            assert "uq_users_phone" in indexes
            assert "ix_users_email" in indexes
            assert "ix_users_phone" in indexes
            assert "ix_user_resumes_user_id" in indexes
            assert "ix_otp_challenges_user_channel" in indexes
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_postgres_async_crud_and_transaction_rollback():
    db_url = _get_verified_postgres_url()
    engine = create_async_engine(db_url, echo=False, future=True)
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    unique_tag = uuid.uuid4().hex[:8]
    test_email = f"pg.test.{unique_tag}@skillverse.edu"
    test_phone = f"+9198{int(unique_tag, 16) % 100000000:08d}"

    try:
        async with SessionLocal() as session:
            assert session.bind.dialect.name == "postgresql"

            # Create User
            user = User(
                full_name=f"PG Integration User {unique_tag}",
                email=test_email,
                phone=test_phone,
                hashed_password=hash_password("PostgresPass#2026"),
                skills=["Python", "FastAPI", "PostgreSQL", "AsyncPG"],
                experience="3 years",
                qualification="B.Tech",
                is_active=False,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

            # Store Resume Metadata in JSONB and save real PDF file on disk
            pdf_bytes = create_sample_pdf_bytes(
                [
                    user.full_name,
                    f"Email: {test_email}",
                    f"Phone: {test_phone}",
                    "Qualification: B.Tech",
                    "Experience: 3 years",
                    "Skills: Python, FastAPI, PostgreSQL, AsyncPG",
                ]
            )
            resume_parser_service.save_uploaded_file_safely(f"{unique_tag}.pdf", pdf_bytes)
            resume = UserResume(
                user_id=user_id,
                original_filename="pg_resume.pdf",
                stored_filename=f"{unique_tag}.pdf",
                extracted_text="PG Integration User Resume",
                extracted_metadata={
                    "full_name": user.full_name,
                    "email": test_email,
                    "phone": test_phone,
                    "qualification": "B.Tech",
                    "experience": "3 years",
                    "skills": ["Python", "FastAPI", "PostgreSQL", "AsyncPG"],
                },
            )
            session.add(resume)

            # Create OTP Challenge
            challenge = OTPChallenge(
                user_id=user_id,
                channel="email",
                otp_hash=hash_otp("654321", salt=f"{user_id}:email"),
                expires_at=user.created_at,
                attempts=1,
                verified=True,
            )
            session.add(challenge)
            await session.commit()

            # Read & Update User + Activate
            fetched = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert fetched.skills == ["Python", "FastAPI", "PostgreSQL", "AsyncPG"]
            fetched.is_email_verified = True
            fetched.is_whatsapp_verified = True
            fetched.is_totp_enabled = True
            fetched.is_active = True
            await session.commit()

            # Transaction Rollback verification
            fetched.full_name = "Rolled Back Name"
            await session.flush()
            await session.rollback()

            after_rb = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert after_rb.full_name == f"PG Integration User {unique_tag}"
            assert after_rb.is_active is True
    finally:
        await engine.dispose()
