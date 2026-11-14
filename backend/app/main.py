import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Deque, Dict

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.logging import logger
from app.routers import auth, dashboard, profile, resume
from app.services.email_service import ExternalProviderError
from app.services.otp_service import OTPChallengeError
from app.services.profile_service import ProfileError
from app.services.registration_service import RegistrationError
from app.services.token_service import TokenAuthError
from app.services.totp_service import TOTPVerificationError
from app.utils.file_validation import ResumeValidationError


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Ensure database tables exist on startup and dispose engine on shutdown."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified on startup.")
    except Exception as exc:
        logger.warning("Startup schema check warning: %s", type(exc).__name__)
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "AI-Powered Resume Parser & Multi-Channel 2FA Onboarding Pipeline for EdTech Candidates. "
        "Supports PDF/DOCX extraction, Argon2id password security, Email/WhatsApp/TOTP 2FA, and JWT authentication."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# CORS Configuration
allowed_origins = list(
    {
        settings.FRONTEND_URL,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    }
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Sliding-window in-memory rate limiter (per client IP)
_rate_buckets: Dict[str, Deque[float]] = defaultdict(deque)
RATE_LIMIT_MAX_REQUESTS = 120
RATE_LIMIT_WINDOW_SECONDS = 60.0


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = _rate_buckets[client_ip]
    while bucket and (now - bucket[0]) > RATE_LIMIT_WINDOW_SECONDS:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_MAX_REQUESTS:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "success": False,
                "error_code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down and try again shortly.",
            },
        )
    bucket.append(now)
    return await call_next(request)


# Centralized Exception Handlers
@app.exception_handler(ResumeValidationError)
async def resume_validation_exception_handler(request: Request, exc: ResumeValidationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(RegistrationError)
async def registration_exception_handler(request: Request, exc: RegistrationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(OTPChallengeError)
async def otp_challenge_exception_handler(request: Request, exc: OTPChallengeError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(TOTPVerificationError)
async def totp_verification_exception_handler(request: Request, exc: TOTPVerificationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(TokenAuthError)
async def token_auth_exception_handler(request: Request, exc: TokenAuthError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(ProfileError)
async def profile_exception_handler(request: Request, exc: ProfileError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error_code": exc.error_code,
            "message": exc.message,
        },
    )


@app.exception_handler(ExternalProviderError)
async def external_provider_exception_handler(request: Request, exc: ExternalProviderError):
    return JSONResponse(
        status_code=status.HTTP_502_BAD_GATEWAY,
        content={
            "success": False,
            "error_code": "EXTERNAL_PROVIDER_FAILURE",
            "provider": exc.provider,
            "message": exc.message,
        },
    )


@app.exception_handler(RequestValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        msg = err.get("msg", "Invalid value")
        if msg.startswith("Value error, "):
            msg = msg.replace("Value error, ", "", 1)
        errors.append({"field": loc or "request", "message": msg})

    first_message = errors[0]["message"] if errors else "Request validation failed."
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error_code": "VALIDATION_ERROR",
            "message": first_message,
            "errors": errors,
        },
    )


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logger.error(
        "Database operation error on %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "DATABASE_ERROR",
            "message": "A database error occurred while processing your request.",
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "Unhandled server error on %s %s: %s",
        request.method,
        request.url.path,
        type(exc).__name__,
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


@app.get("/health", tags=["System Health"])
async def health_check():
    db_connected = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_connected = True
    except Exception:
        db_connected = False

    return {
        "status": "healthy" if db_connected else "degraded",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "database_connected": db_connected,
        "required_2fa_channels": settings.required_channels_list,
        "email_provider_mode": settings.EMAIL_PROVIDER_MODE,
        "whatsapp_provider_mode": settings.WHATSAPP_PROVIDER_MODE,
    }


# Mount API v1 Routers
app.include_router(resume.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(profile.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
