"""Canales de aviso del soporte: ntfy y Telegram (Plan.md §11.3–§11.4).

Ambos son opcionales y **nunca** son la fuente de verdad: si fallan, la
conversación queda en el buzón del panel y el outbox permite reintentar. No
reciben el teléfono de llamada ni datos personales completos.

Las peticiones usan la biblioteca estándar con timeout: sin dependencias
extra ni estado compartido. Los secretos solo viven en variables de entorno.
"""

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import Settings
from app.domain.errors import DomainError

_HTTP_TIMEOUT_SECONDS = 10


def _delivery_error() -> DomainError:
    return DomainError(
        503,
        "notification_delivery_failed",
        "No se pudo enviar el aviso ahora. Inténtalo más tarde.",
    )


def send_ntfy(
    settings: Settings,
    title: str,
    message: str,
    click_url: str,
    topic: str | None = None,
) -> None:
    """Publica en un tema ntfy autoalojado; falla sin exponer URL ni token.

    El tema por omisión es el de la plataforma (`SUPPORT_NTFY_TOPIC`); los
    avisos al comercio llevan su tema propio.
    """
    if not settings.support_ntfy_enabled:
        raise DomainError(
            503,
            "notification_not_configured",
            "El aviso ntfy no está configurado.",
        )
    resolved_topic = topic or settings.support_ntfy_topic
    if not resolved_topic:
        raise DomainError(
            503,
            "notification_not_configured",
            "Falta el tema de avisos.",
        )
    if not settings.support_ntfy_base_url:
        raise DomainError(
            503,
            "notification_not_configured",
            "Falta la URL del servidor de avisos.",
        )
    quoted_topic = quote(resolved_topic, safe="")
    url = f"{settings.support_ntfy_base_url.rstrip('/')}/{quoted_topic}"
    headers = {
        "Title": title.encode("utf-8").decode("latin-1", errors="replace"),
        "Priority": "high",
        "Tags": "bell",
        "Click": click_url,
    }
    if settings.support_ntfy_token:
        headers["Authorization"] = f"Bearer {settings.support_ntfy_token}"
    request = Request(url, data=message.encode("utf-8"), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            if response.status >= 300:
                raise _delivery_error()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise _delivery_error() from exc


def send_telegram(settings: Settings, text: str) -> None:
    """Envía un mensaje al chat del propietario mediante un bot de Telegram."""
    if not settings.support_telegram_enabled:
        raise DomainError(
            503,
            "notification_not_configured",
            "El aviso de Telegram no está configurado.",
        )
    assert settings.support_telegram_bot_token and settings.support_telegram_chat_id
    url = f"https://api.telegram.org/bot{settings.support_telegram_bot_token}/sendMessage"
    payload = json.dumps(
        {
            "chat_id": settings.support_telegram_chat_id,
            "text": text[:3900],
            "disable_web_page_preview": True,
        }
    ).encode("utf-8")
    request = Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=_HTTP_TIMEOUT_SECONDS) as response:
            if response.status >= 300:
                raise _delivery_error()
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise _delivery_error() from exc
