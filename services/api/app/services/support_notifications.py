"""Avisos del soporte: outbox persistente y worker de reintentos (Plan.md §11).

Reglas:

- El mensaje se guarda **antes** de intentar cualquier aviso.
- El worker solo envía avisos; nunca borra ni corrige conversaciones.
- Cada canal (email, ntfy, Telegram) es independiente y opcional.
- Los errores externos se convierten en códigos internos, sin secretos ni
  detalles sensibles (§16.6).
- En varios nodos, cada aviso se reclama con un `UPDATE` condicional para que
  dos procesos no lo envíen dos veces.
"""

import logging
import uuid
from collections.abc import Callable
from datetime import timedelta

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.urls import absolute_url
from app.domain.errors import DomainError
from app.models.merchant import Merchant
from app.models.support import (
    SupportCallbackRequest,
    SupportMessage,
    SupportNotification,
    SupportNotificationChannel,
    SupportNotificationStatus,
    SupportThread,
)
from app.models.user import User, utcnow
from app.services import email as email_service

logger = logging.getLogger(__name__)

#: Errores que no tiene sentido reintentar automáticamente: falta de
#: configuración o canal deshabilitado. Solo se resuelven corrigiendo el
#: despliegue y pulsando «reintentar».
PERMANENT_ERROR_CODES = frozenset(
    {
        "email_delivery_not_configured",
        "notification_not_configured",
        "support_notification_not_configured",
    }
)

Sender = Callable[..., None]


def _excerpt(text: str, limit: int = 180) -> str:
    clean = " ".join(text.split())
    return clean if len(clean) <= limit else clean[: limit - 1].rstrip() + "…"


def _merchant_name(session: Session, merchant_id: uuid.UUID) -> str:
    merchant = session.get(Merchant, merchant_id)
    return merchant.name if merchant else "Comercio"


def _thread_url(settings: Settings, thread: SupportThread, *, platform: bool) -> str:
    path = (
        f"/platform/support/{thread.id}"
        if platform
        else f"/merchants/{thread.merchant_id}/support/{thread.id}"
    )
    return absolute_url(path, (settings.public_base_url or "").rstrip("/"))


def _enabled_channels(
    settings: Settings,
    *,
    event: str,
    merchant_recipient: str | None,
) -> list[str]:
    channels: list[str] = []
    if event == "platform_message":
        if settings.support_email_enabled and merchant_recipient:
            channels.append(SupportNotificationChannel.EMAIL_MERCHANT)
        return channels
    if settings.support_email_enabled and settings.support_notification_email:
        channels.append(SupportNotificationChannel.EMAIL_PLATFORM)
    if settings.support_ntfy_enabled:
        channels.append(SupportNotificationChannel.NTFY)
    if settings.support_telegram_enabled:
        channels.append(SupportNotificationChannel.TELEGRAM)
    return channels


def queue_notifications(
    session: Session,
    settings: Settings,
    thread: SupportThread,
    *,
    event: str,
    message: SupportMessage | None = None,
    callback: SupportCallbackRequest | None = None,
) -> list[SupportNotification]:
    """Registra los avisos pendientes en la misma transacción que el evento."""
    merchant_recipient: str | None = None
    if event == "platform_message":
        creator = session.get(User, thread.created_by_user_id)
        merchant_recipient = creator.email if creator else None

    source_id = (
        message.id if message is not None else callback.id if callback is not None else thread.id
    )
    rows: list[SupportNotification] = []
    for channel in _enabled_channels(settings, event=event, merchant_recipient=merchant_recipient):
        idempotency_key = f"support:{event}:{source_id}:{channel}"
        existing = session.scalar(
            select(SupportNotification).where(
                SupportNotification.idempotency_key == idempotency_key
            )
        )
        if existing is not None:
            continue
        row = SupportNotification(
            thread_id=thread.id,
            message_id=message.id if message is not None else None,
            channel=channel,
            idempotency_key=idempotency_key,
        )
        session.add(row)
        rows.append(row)
    if rows:
        session.flush()
    return rows


def _notification_text(
    session: Session,
    settings: Settings,
    thread: SupportThread,
    notification: SupportNotification,
    message: SupportMessage | None,
    callback: SupportCallbackRequest | None,
) -> tuple[str, str, str]:
    """Devuelve (asunto, texto, URL de acción) sin datos sensibles."""
    merchant_name = _merchant_name(session, thread.merchant_id)
    if callback is not None:
        subject = f"[Soporte] {merchant_name} — solicitud de llamada"
        text = (
            f"El comercio «{merchant_name}» solicita una llamada privada. "
            "Consulta el número y la disponibilidad en el buzón de soporte."
        )
        return subject, text, _thread_url(settings, thread, platform=True)
    if message is None:
        subject = f"[Soporte] {merchant_name} — {thread.subject}"
        return (
            subject,
            "Nueva actividad en la conversación.",
            _thread_url(settings, thread, platform=True),
        )
    if notification.channel == SupportNotificationChannel.EMAIL_MERCHANT:
        subject = f"[Soporte] Nueva respuesta en «{thread.subject}»"
        text = (
            "El equipo de LocalAI Fidelity ha respondido en tu conversación: "
            f"{_excerpt(message.body)}"
        )
        return subject, text, _thread_url(settings, thread, platform=False)
    subject = f"[Soporte] {merchant_name} — {thread.subject}"
    text = f"Nuevo mensaje de «{merchant_name}»: {_excerpt(message.body)}"
    return subject, text, _thread_url(settings, thread, platform=True)


def _dispatch(
    session: Session,
    settings: Settings,
    notification: SupportNotification,
    message: SupportMessage | None,
    callback: SupportCallbackRequest | None,
) -> None:
    thread = session.get(SupportThread, notification.thread_id)
    if thread is None:
        raise DomainError(404, "support_thread_not_found", "Conversación no encontrada")
    subject, text, action_url = _notification_text(
        session, settings, thread, notification, message, callback
    )

    if notification.channel == SupportNotificationChannel.EMAIL_PLATFORM:
        recipient = settings.support_notification_email
        if not recipient:
            raise DomainError(
                503,
                "support_notification_not_configured",
                "Falta el correo privado de notificación.",
            )
        email_service.send_support_email(settings, recipient, subject, text, action_url)
        return
    if notification.channel == SupportNotificationChannel.EMAIL_MERCHANT:
        creator = session.get(User, thread.created_by_user_id)
        if creator is None:
            raise DomainError(
                503,
                "support_notification_not_configured",
                "No hay destinatario para el aviso al comercio.",
            )
        email_service.send_support_email(settings, creator.email, subject, text, action_url)
        return
    if notification.channel == SupportNotificationChannel.NTFY:
        from app.integrations import notify

        notify.send_ntfy(settings, subject, text, action_url)
        return
    if notification.channel == SupportNotificationChannel.TELEGRAM:
        from app.integrations import notify

        notify.send_telegram(settings, f"{subject}\n\n{text}\n\n{action_url}")
        return
    raise DomainError(
        503,
        "support_notification_not_configured",
        "Canal de aviso no soportado.",
    )


def _record_failure(
    notification: SupportNotification, settings: Settings, *, code: str, detail: str
) -> None:
    notification.error_code = code
    notification.error_detail = detail[:255] or None
    permanent = code in PERMANENT_ERROR_CODES
    if not permanent and notification.attempts < settings.support_notification_max_attempts:
        seconds = min(settings.support_notification_backoff_seconds * notification.attempts, 3600)
        notification.status = SupportNotificationStatus.RETRYING
        notification.next_attempt_at = utcnow() + timedelta(seconds=seconds)
    else:
        notification.status = SupportNotificationStatus.FAILED
        notification.next_attempt_at = None


def _execute(
    session: Session,
    settings: Settings,
    notification: SupportNotification,
) -> None:
    message = (
        session.get(SupportMessage, notification.message_id)
        if notification.message_id is not None
        else None
    )
    callback = None
    if message is None:
        callback = session.scalar(
            select(SupportCallbackRequest)
            .where(SupportCallbackRequest.thread_id == notification.thread_id)
            .order_by(SupportCallbackRequest.requested_at.desc())
            .limit(1)
        )
    try:
        _dispatch(session, settings, notification, message, callback)
    except DomainError as error:
        detail = error.detail.get("message", "") if isinstance(error.detail, dict) else ""
        _record_failure(notification, settings, code=error.code, detail=str(detail))
    except Exception as error:  # noqa: BLE001 — el worker nunca debe morir
        logger.warning(
            "support notification %s falló: %s", notification.channel, type(error).__name__
        )
        _record_failure(
            notification,
            settings,
            code="notification_delivery_failed",
            detail=type(error).__name__,
        )
    else:
        notification.status = SupportNotificationStatus.SUCCEEDED
        notification.sent_at = utcnow()
        notification.error_code = None
        notification.error_detail = None
        notification.next_attempt_at = None
    session.flush()


def due_notifications(session: Session, limit: int = 50) -> list[SupportNotification]:
    now = utcnow()
    return list(
        session.scalars(
            select(SupportNotification)
            .where(
                SupportNotification.status.in_(tuple(SupportNotificationStatus.DUE)),
                or_(
                    SupportNotification.next_attempt_at.is_(None),
                    SupportNotification.next_attempt_at <= now,
                ),
            )
            .order_by(SupportNotification.created_at)
            .limit(limit)
        ).all()
    )


def _claim(session: Session, notification: SupportNotification) -> bool:
    """Reclama un aviso de forma atómica; sirve también con varios nodos."""
    result = session.execute(
        update(SupportNotification)
        .where(
            SupportNotification.id == notification.id,
            SupportNotification.status.in_(tuple(SupportNotificationStatus.DUE)),
        )
        .values(
            status=SupportNotificationStatus.RUNNING,
            attempts=SupportNotification.attempts + 1,
            next_attempt_at=None,
        )
    )
    return bool(result.rowcount)  # type: ignore[attr-defined]


def run_due_notifications(session: Session, settings: Settings, limit: int = 50) -> int:
    processed = 0
    for notification in due_notifications(session, limit=limit):
        if not _claim(session, notification):
            continue
        session.refresh(notification)
        _execute(session, settings, notification)
        processed += 1
    return processed


def retry_notification(
    session: Session, notification: SupportNotification, settings: Settings
) -> SupportNotification:
    """Reintento manual visible en el panel (§15)."""
    if notification.status in {
        SupportNotificationStatus.QUEUED,
        SupportNotificationStatus.RUNNING,
        SupportNotificationStatus.SUCCEEDED,
    }:
        return notification
    notification.status = SupportNotificationStatus.QUEUED
    notification.next_attempt_at = None
    notification.manual_retries += 1
    session.flush()
    if _claim(session, notification):
        session.refresh(notification)
        _execute(session, settings, notification)
    return notification


def notifications_for_thread(session: Session, thread_id: uuid.UUID) -> list[SupportNotification]:
    return list(
        session.scalars(
            select(SupportNotification)
            .where(SupportNotification.thread_id == thread_id)
            .order_by(SupportNotification.created_at)
        ).all()
    )
