from abc import ABC, abstractmethod
import httpx

from app.core.config import get_settings
from app.core.logging import logger
from app.services.email_service import DeliveryResult, ExternalProviderError


class WhatsAppProviderAdapter(ABC):
    """Configurable adapter interface for WhatsApp OTP delivery."""

    @abstractmethod
    async def send_otp(self, phone_number: str, otp_code: str) -> DeliveryResult:
        raise NotImplementedError


class WhatsAppCloudAPIAdapter(WhatsAppProviderAdapter):
    """Official Meta WhatsApp Business Cloud API adapter."""

    async def send_otp(self, phone_number: str, otp_code: str) -> DeliveryResult:
        settings = get_settings()
        if not settings.WHATSAPP_ACCESS_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
            raise ExternalProviderError(
                "WhatsApp Business Cloud API credentials (WHATSAPP_ACCESS_TOKEN, WHATSAPP_PHONE_NUMBER_ID) are not configured.",
                provider="whatsapp_cloud",
            )

        normalized_phone = phone_number.lstrip("+")
        url = (
            f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
            f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
        )
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": normalized_phone,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": (
                    f"[{settings.TOTP_ISSUER_NAME}] Your WhatsApp verification OTP is {otp_code}. "
                    f"Valid for {settings.OTP_EXPIRE_MINUTES} minutes. Do not share this code."
                ),
            },
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload, headers=headers)
                if response.status_code >= 400:
                    logger.error(
                        "WhatsApp Cloud API returned HTTP %s", response.status_code
                    )
                    raise ExternalProviderError(
                        "WhatsApp Business Cloud API rejected the OTP delivery request.",
                        provider="whatsapp_cloud",
                    )
        except ExternalProviderError:
            raise
        except Exception as exc:
            logger.error("WhatsApp Cloud API error: %s", type(exc).__name__)
            raise ExternalProviderError(
                "Unable to reach WhatsApp Business Cloud API.",
                provider="whatsapp_cloud",
            )

        return DeliveryResult(
            delivered=True,
            delivery_mode="cloud",
            message="OTP delivered via live WhatsApp Business Cloud API.",
            dev_otp_preview=None,
            is_simulated=False,
        )


class WhatsAppMockAdapter(WhatsAppProviderAdapter):
    """Development mock adapter clearly distinguished from live Cloud API delivery."""

    async def send_otp(self, phone_number: str, otp_code: str) -> DeliveryResult:
        logger.info("Generated simulated WhatsApp OTP in development mock mode (no real WhatsApp message sent).")
        return DeliveryResult(
            delivered=False,
            delivery_mode="mock",
            message="[MOCK MODE - NO REAL WHATSAPP SENT] Simulated WhatsApp OTP generated for local development only.",
            dev_otp_preview=otp_code,
            is_simulated=True,
        )


class WhatsAppService:
    """Facade selecting either the live WhatsApp Cloud API adapter or Mock adapter."""

    def get_adapter(self) -> WhatsAppProviderAdapter:
        settings = get_settings()
        mode = settings.WHATSAPP_PROVIDER_MODE.lower().strip()
        if mode == "cloud":
            return WhatsAppCloudAPIAdapter()
        return WhatsAppMockAdapter()

    async def send_otp_whatsapp(self, phone_number: str, otp_code: str) -> DeliveryResult:
        adapter = self.get_adapter()
        return await adapter.send_otp(phone_number=phone_number, otp_code=otp_code)


whatsapp_service = WhatsAppService()
