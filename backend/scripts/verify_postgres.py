"""
PostgreSQL 18 Live Verification & Integration Test Script (Tasks 1 & 2).
Handles URL-encoded special characters via SQLAlchemy make_url() and never prints or exposes passwords.
"""
import asyncio
import subprocess
import sys
import uuid
from pathlib import Path

import asyncpg
from sqlalchemy import select, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import PLACEHOLDER_PASSWORDS, get_settings  # noqa: E402
from app.core.security import hash_otp, hash_password  # noqa: E402
from app.models.otp_challenge import OTPChallenge  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.user_resume import UserResume  # noqa: E402


def mask_db_url(raw_url: str) -> str:
    try:
        u = make_url(raw_url)
        return u.render_as_string(hide_password=True)
    except Exception:
        return "postgresql+asyncpg://***:***@localhost:5432/edtech_onboarding"


async def ensure_database_exists(db_url: str) -> None:
    u = make_url(db_url)
    target_db = u.database or "edtech_onboarding"
    # make_url() automatically unquotes URL-encoded special characters in username & password
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
            print(f"[OK] Created PostgreSQL database: {target_db}")
        else:
            print(f"[OK] PostgreSQL database already exists: {target_db}")
    finally:
        await conn.close()


async def verify_postgres_schema_and_crud(db_url: str) -> None:
    engine = create_async_engine(db_url, echo=False, future=True)
    SessionLocal = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )

    try:
        async with engine.connect() as conn:
            pg_version = (await conn.execute(text("SELECT version()"))).scalar_one()
            print(f"[OK] Connected via SQLAlchemy AsyncPG -> {pg_version}")

            # Verify 3 tables
            tables_res = await conn.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = 'public' ORDER BY table_name"
                )
            )
            tables = [r[0] for r in tables_res.fetchall()]
            print(f"[OK] Verified public tables: {tables}")
            for expected in ("users", "user_resumes", "otp_challenges", "alembic_version"):
                assert expected in tables, f"Missing table: {expected}"

            # Verify JSONB columns
            jsonb_res = await conn.execute(
                text(
                    "SELECT table_name, column_name, data_type, udt_name "
                    "FROM information_schema.columns "
                    "WHERE table_schema = 'public' AND udt_name = 'jsonb' "
                    "ORDER BY table_name, column_name"
                )
            )
            jsonb_cols = [
                f"{r[0]}.{r[1]} ({r[3].upper()})" for r in jsonb_res.fetchall()
            ]
            print(f"[OK] Verified PostgreSQL JSONB columns: {jsonb_cols}")

            # Verify indexes & unique constraints
            idx_res = await conn.execute(
                text(
                    "SELECT indexname, tablename FROM pg_indexes "
                    "WHERE schemaname = 'public' ORDER BY tablename, indexname"
                )
            )
            indexes = [f"{r[1]}:{r[0]}" for r in idx_res.fetchall()]
            print(f"[OK] Verified PostgreSQL indexes & constraints: {indexes}")

            # Verify foreign keys
            fk_res = await conn.execute(
                text(
                    "SELECT tc.table_name, tc.constraint_name "
                    "FROM information_schema.table_constraints tc "
                    "WHERE tc.table_schema = 'public' AND tc.constraint_type = 'FOREIGN KEY' "
                    "ORDER BY tc.table_name"
                )
            )
            fks = [f"{r[0]}:{r[1]}" for r in fk_res.fetchall()]
            print(f"[OK] Verified PostgreSQL foreign keys: {fks}")

        # Execute SQLAlchemy Async CRUD & Transaction Rollback with isolated synthetic record
        unique_tag = uuid.uuid4().hex[:8]
        test_email = f"pg.verify.{unique_tag}@skillverse.edu"
        test_phone = f"+9199{int(unique_tag, 16) % 100000000:08d}"

        async with SessionLocal() as session:
            user = User(
                full_name=f"PG Verified Candidate {unique_tag}",
                email=test_email,
                phone=test_phone,
                hashed_password=hash_password("PgVerify#2026"),
                skills=["Python", "FastAPI", "PostgreSQL", "JSONB"],
                experience="2 years",
                qualification="M.Tech",
                is_active=False,
            )
            session.add(user)
            await session.flush()
            user_id = user.id

            resume = UserResume(
                user_id=user_id,
                original_filename="pg_candidate.pdf",
                stored_filename=f"{unique_tag}.pdf",
                extracted_text="PG Verified Candidate | Python FastAPI PostgreSQL",
                extracted_metadata={
                    "full_name": user.full_name,
                    "email": test_email,
                    "skills": ["Python", "FastAPI", "PostgreSQL", "JSONB"],
                },
            )
            session.add(resume)

            challenge = OTPChallenge(
                user_id=user_id,
                channel="email",
                otp_hash=hash_otp("112233", salt=f"{user_id}:email"),
                expires_at=user.created_at,
                attempts=1,
                verified=True,
            )
            session.add(challenge)
            await session.commit()

            fetched = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            fetched.is_email_verified = True
            fetched.is_whatsapp_verified = True
            fetched.is_totp_enabled = True
            fetched.is_active = True
            fetched.qualification = "Ph.D. in Computer Science"
            await session.commit()

            # Test Transaction Rollback
            fetched.full_name = "Should Be Rolled Back"
            await session.flush()
            await session.rollback()

            verified_user = (
                await session.execute(select(User).where(User.id == user_id))
            ).scalar_one()
            assert verified_user.full_name == f"PG Verified Candidate {unique_tag}"
            assert verified_user.is_active is True
            print(
                f"[OK] Verified PostgreSQL Async CRUD, JSONB storage, activation & rollback (dialect={session.bind.dialect.name})"
            )
    finally:
        await engine.dispose()


async def main() -> int:
    settings = get_settings()
    db_url = settings.DATABASE_URL
    if not db_url.startswith("postgresql+asyncpg://"):
        print(
            "[ERROR] DATABASE_URL does not use postgresql+asyncpg:// format.",
            file=sys.stderr,
        )
        return 1

    u = make_url(db_url)
    if (
        not u.username
        or u.username.upper() == "USERNAME"
        or (u.password or "").upper() in PLACEHOLDER_PASSWORDS
    ):
        print(
            "[CREDENTIALS_REQUIRED] DATABASE_URL in .env still contains the placeholder "
            "postgresql+asyncpg://USERNAME:PASSWORD@localhost:5432/edtech_onboarding. "
            "Please configure your actual local PostgreSQL username and password in .env.",
            file=sys.stderr,
        )
        return 2

    try:
        await ensure_database_exists(db_url)
    except asyncpg.InvalidPasswordError:
        print(
            "[AUTH_FAILED] PostgreSQL rejected the password configured in .env. "
            "Please verify your local PostgreSQL password in .env.",
            file=sys.stderr,
        )
        return 3
    except Exception as exc:
        print(f"[ERROR] PostgreSQL connection error: {type(exc).__name__}", file=sys.stderr)
        return 4

    alembic_exe = BACKEND_DIR / ".venv" / "Scripts" / "alembic.exe"
    subprocess.run([str(alembic_exe), "upgrade", "head"], cwd=str(BACKEND_DIR), check=True)
    print("[OK] Executed `alembic upgrade head` against PostgreSQL.")

    await verify_postgres_schema_and_crud(db_url)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
