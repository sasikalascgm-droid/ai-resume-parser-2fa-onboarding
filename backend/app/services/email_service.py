import asyncio
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Optional

from app.core.config import get_settings
from app.core.logging import logger


class ExternalProviderError(Exception):
    def __init__(self, message: str, provider: str = "external"):
        super().__init__(message)
        self.message = message
        self.provider = provider


@dataclass
class DeliveryResult:
    delivered: bool
    delivery_mode: str  # "smtp" or "mock"
    message: str
    dev_otp_preview: Optional[str] = None
    is_simulated: bool = False


class EmailService:
    """SMTP email service with explicit development mock mode."""

    async def send_otp_email(self, recipient_email: str, full_name: str, otp_code: str) -> DeliveryResult:
        settings = get_settings()
        mode = settings.EMAIL_PROVIDER_MODE.lower().strip()

        if mode == "smtp":
            if not settings.SMTP_HOST or not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
                raise ExternalProviderError(
                    "SMTP credentials (SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD) are not configured for EMAIL_PROVIDER_MODE=smtp.",
                    provider="smtp",
                )
            try:
                await asyncio.to_thread(
                    self._send_via_smtp,
                    recipient_email=recipient_email,
                    full_name=full_name,
                    otp_code=otp_code,
                )
                logger.info("Sent Email OTP via live SMTP to masked recipient.")
                return DeliveryResult(
                    delivered=True,
                    delivery_mode="smtp",
                    message="OTP sent to your email address via live SMTP.",
                    dev_otp_preview=None,
                    is_simulated=False,
                )
            except Exception as exc:
                logger.error("SMTP OTP delivery failed: %s", type(exc).__name__)
                raise ExternalProviderError(
                    "Failed to send verification email through SMTP provider.",
                    provider="smtp",
                )

        # Development Mock Mode (never claims live SMTP delivery)
        logger.info("Generated simulated Email OTP in development mock mode (no real email sent).")
        return DeliveryResult(
            delivered=False,
            delivery_mode="mock",
            message="[MOCK MODE - NO REAL EMAIL SENT] Simulated Email OTP generated for local development only.",
            dev_otp_preview=otp_code,
            is_simulated=True,
        )

    def _send_via_smtp(self, recipient_email: str, full_name: str, otp_code: str) -> None:
        settings = get_settings()
        msg = EmailMessage()
        msg["Subject"] = f"{settings.TOTP_ISSUER_NAME} - Your Email Verification Code"
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = recipient_email
        msg.set_content(
            f"Hello {full_name},\n\n"
            f"Your verification code for {settings.TOTP_ISSUER_NAME} is: {otp_code}\n\n"
            f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
            f"If you did not request this verification, please ignore this email.\n"
        )

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.ehlo()
            if settings.SMTP_PORT in (587, 2525):
                server.starttls()
                server.ehlo()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)


email_service = EmailService()
