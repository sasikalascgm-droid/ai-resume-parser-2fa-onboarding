import io
from typing import AsyncGenerator, List

import docx
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.database import Base, get_db
from app.main import _rate_buckets, app

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


def create_sample_pdf_bytes(lines: List[str]) -> bytes:
    """Create a real, valid machine-readable PDF document in memory."""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    y = 750
    for line in lines:
        c.drawString(72, y, line)
        y -= 20
    c.showPage()
    c.save()
    return buffer.getvalue()


def create_sample_docx_bytes(lines: List[str]) -> bytes:
    """Create a real, valid DOCX document in memory."""
    document = docx.Document()
    for line in lines:
        document.add_paragraph(line)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


@pytest_asyncio.fixture()
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    TestSessionLocal = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with TestSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture()
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    _rate_buckets.clear()
    settings = get_settings()
    orig_email_mode = settings.EMAIL_PROVIDER_MODE
    orig_wa_mode = settings.WHATSAPP_PROVIDER_MODE
    settings.EMAIL_PROVIDER_MODE = "mock"
    settings.WHATSAPP_PROVIDER_MODE = "mock"

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
            yield ac
    finally:
        app.dependency_overrides.clear()
        settings.EMAIL_PROVIDER_MODE = orig_email_mode
        settings.WHATSAPP_PROVIDER_MODE = orig_wa_mode
