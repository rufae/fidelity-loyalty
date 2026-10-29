"""Dominio del soporte B2B: conversaciones, mensajes y llamadas (Plan.md §7–§9).

Responsabilidades:

- Aislar cada conversación por comercio y, para `staff`, por usuario creador.
- Validar límites antiabuso con datos persistentes (multi-nodo correcto).
- Aplicar idempotencia en creación de conversaciones, mensajes y llamadas.
- Guardar el teléfono de llamada cifrado, nunca en claro.
- Encolar avisos en la misma transacción que el mensaje.
- Marcar lecturas y calcular no leídos sin exponer datos ajenos.

La API decide quién puede llamar; aquí se vuelve a comprobar el alcance para
que ningún endpoint pueda saltarse accidentalmente el aislamiento (§8.2).
"""

import uuid
from datetime import timedelta
from typing import Literal

from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.crypto import decrypt_text, encrypt_text
from app.domain.errors import DomainError, not_found
from app.domain.roles import MerchantRole
from app.models.merchant import Merchant
from app.models.support import (
    SupportAuthorType,
    SupportCallbackRequest,
    SupportCallbackStatus,
    SupportMessage,
    SupportNotification,
    SupportThread,
    SupportThreadStatus,
)
from app.models.user import User, utcnow
from app.schemas.support import (
    SupportCallbackRequestCreate,
    SupportCallbackRequestOut,
    SupportMessageCreate,
    SupportMessageOut,
    SupportNotificationOut,
    SupportThreadCreate,
    SupportThreadDetailOut,
    SupportThreadOut,
    SupportThreadUpdate,
)
from app.services.support_notifications import notifications_for_thread, queue_notifications

ViewerSide = Literal["merchant", "platform"]


def _rate_limited(message: str) -> DomainError:
    error = DomainError(429, "support_rate_limited", message)
    error.headers = {"Retry-After": "3600"}
    return error


def _display_name(session: Session, user_id: uuid.UUID | None, fallback: str) -> str:
    if user_id is None:
        return fallback
    user = session.get(User, user_id)
    return user.display_name if user else fallback


def message_out(session: Session, message: SupportMessage) -> SupportMessageOut:
    return SupportMessageOut(
        id=message.id,
        thread_id=message.thread_id,
        author_type=message.author_type,
        author_user_id=message.author_user_id,
        author_display_name=_display_name(
            session,
            message.author_user_id,
            "Soporte" if message.author_type == SupportAuthorType.PLATFORM else "Comercio",
        ),
        body=message.body,
        created_at=message.created_at,
        read_by_merchant_at=message.read_by_merchant_at,
        read_by_platform_at=message.read_by_platform_at,
    )


def callback_out(
    session: Session,
    settings: Settings,
    callback: SupportCallbackRequest,
    *,
    include_phone: bool,
) -> SupportCallbackRequestOut:
    phone: str | None = None
    if include_phone:
        try:
            phone = decrypt_text(settings, callback.phone_encrypted)
        except DomainError:
            # Un registro corrupto no debe romper toda la bandeja: se muestra
            # sin teléfono y queda visible el estado para repararlo.
            phone = None
    return SupportCallbackRequestOut(
        id=callback.id,
        status=callback.status,
        availability=callback.availability,
        requested_at=callback.requested_at,
        handled_at=callback.handled_at,
        phone=phone,
    )


def _unread_for_side(session: Session, thread_id: uuid.UUID, side: ViewerSide) -> int:
    if side == "merchant":
        condition = (
            SupportMessage.author_type == SupportAuthorType.PLATFORM,
            SupportMessage.read_by_merchant_at.is_(None),
        )
    else:
        condition = (
            SupportMessage.author_type == SupportAuthorType.MERCHANT,
            SupportMessage.read_by_platform_at.is_(None),
        )
    return int(
        session.scalar(
            select(func.count())
            .select_from(SupportMessage)
            .where(SupportMessage.thread_id == thread_id, *condition)
        )
        or 0
    )


def thread_out(
    session: Session,
    thread: SupportThread,
    *,
    side: ViewerSide,
    include_merchant_name: bool = False,
) -> SupportThreadOut:
    merchant_name = None
    if include_merchant_name:
        merchant = session.get(Merchant, thread.merchant_id)
        merchant_name = merchant.name if merchant else None
    has_callback = (
        session.scalar(
            select(SupportCallbackRequest.id)
            .where(SupportCallbackRequest.thread_id == thread.id)
            .limit(1)
        )
        is not None
    )
    return SupportThreadOut(
        id=thread.id,
        merchant_id=thread.merchant_id,
        merchant_name=merchant_name,
        created_by_user_id=thread.created_by_user_id,
        created_by_display_name=_display_name(session, thread.created_by_user_id, "Usuario"),
        subject=thread.subject,
        category=thread.category,
        status=thread.status,
        priority=thread.priority,
        preferred_contact=thread.preferred_contact,
        last_message_at=thread.last_message_at,
        closed_at=thread.closed_at,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        unread_for_viewer=_unread_for_side(session, thread.id, side),
        has_callback_request=has_callback,
    )


def _detail_out(
    session: Session,
    settings: Settings,
    thread: SupportThread,
    *,
    side: ViewerSide,
    include_private: bool,
) -> SupportThreadDetailOut:
    base = thread_out(session, thread, side=side, include_merchant_name=include_private)
    messages = session.scalars(
        select(SupportMessage)
        .where(SupportMessage.thread_id == thread.id)
        .order_by(SupportMessage.created_at, SupportMessage.id)
    ).all()
    callback = session.scalar(
        select(SupportCallbackRequest)
        .where(SupportCallbackRequest.thread_id == thread.id)
        .order_by(SupportCallbackRequest.requested_at.desc())
        .limit(1)
    )
    return SupportThreadDetailOut(
        **base.model_dump(),
        messages=[message_out(session, message) for message in messages],
        callback_request=(
            callback_out(session, settings, callback, include_phone=include_private)
            if callback is not None
            else None
        ),
        notifications=(
            [
                SupportNotificationOut.model_validate(n)
                for n in notifications_for_thread(session, thread.id)
            ]
            if include_private
            else []
        ),
    )


def _count_threads_since(session: Session, user_id: uuid.UUID, *, hours: int = 24) -> int:
    since = utcnow() - timedelta(hours=hours)
    return int(
        session.scalar(
            select(func.count())
            .select_from(SupportThread)
            .where(SupportThread.created_by_user_id == user_id, SupportThread.created_at >= since)
        )
        or 0
    )


def _count_messages_since(
    session: Session, thread_id: uuid.UUID, user_id: uuid.UUID, *, hours: int = 24
) -> int:
    since = utcnow() - timedelta(hours=hours)
    return int(
        session.scalar(
            select(func.count())
            .select_from(SupportMessage)
            .where(
                SupportMessage.thread_id == thread_id,
                SupportMessage.author_user_id == user_id,
                SupportMessage.created_at >= since,
            )
        )
        or 0
    )


def _count_callbacks_since(session: Session, user_id: uuid.UUID, *, hours: int = 24) -> int:
    since = utcnow() - timedelta(hours=hours)
    return int(
        session.scalar(
            select(func.count())
            .select_from(SupportCallbackRequest)
            .where(
                SupportCallbackRequest.requested_by_user_id == user_id,
                SupportCallbackRequest.requested_at >= since,
            )
        )
        or 0
    )


def _validate_body(settings: Settings, body: str) -> str:
    clean = body.strip()
    if not clean:
        raise DomainError(400, "invalid_message", "El mensaje no puede estar vacío")
    if len(clean) > settings.support_message_max_length:
        raise DomainError(400, "message_too_long", "El mensaje es demasiado largo")
    return clean


def _ensure_merchant_can_view(
    thread: SupportThread,
    *,
    merchant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MerchantRole | None,
    is_platform_admin: bool,
) -> None:
    if thread.merchant_id != merchant_id:
        raise not_found("Conversación")
    if is_platform_admin:
        return
    if role is None or role not in {MerchantRole.OWNER, MerchantRole.ADMIN, MerchantRole.STAFF}:
        raise not_found("Conversación")
    if role == MerchantRole.STAFF and thread.created_by_user_id != user_id:
        # Un miembro del personal solo ve sus propias conversaciones (§8.2).
        raise not_found("Conversación")


def create_thread(
    session: Session,
    settings: Settings,
    *,
    merchant_id: uuid.UUID,
    user_id: uuid.UUID,
    data: SupportThreadCreate,
    is_platform_admin: bool = False,
    idempotency_key: str | None = None,
) -> tuple[SupportThread, SupportMessage]:
    if idempotency_key:
        existing = session.scalar(
            select(SupportThread).where(
                SupportThread.merchant_id == merchant_id,
                SupportThread.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            first = session.scalar(
                select(SupportMessage)
                .where(SupportMessage.thread_id == existing.id)
                .order_by(SupportMessage.created_at, SupportMessage.id)
            )
            if first is not None:
                return existing, first

    created = _count_threads_since(session, user_id)
    if created >= settings.support_thread_rate_limit_per_day:
        raise _rate_limited("Has alcanzado el límite de conversaciones nuevas por hoy")

    body = _validate_body(settings, data.body)
    thread = SupportThread(
        merchant_id=merchant_id,
        created_by_user_id=user_id,
        subject=data.subject.strip(),
        category=data.category,
        preferred_contact=data.preferred_contact,
        status=SupportThreadStatus.WAITING_PLATFORM,
        idempotency_key=idempotency_key,
    )
    session.add(thread)
    session.flush()

    message = SupportMessage(
        thread_id=thread.id,
        merchant_id=merchant_id,
        author_type=(
            SupportAuthorType.PLATFORM if is_platform_admin else SupportAuthorType.MERCHANT
        ),
        author_user_id=user_id,
        body=body,
        idempotency_key=f"{idempotency_key}:message" if idempotency_key else None,
    )
    session.add(message)
    session.flush()

    if data.callback_phone:
        request_callback(
            session,
            settings,
            thread=thread,
            user_id=user_id,
            data=SupportCallbackRequestCreate(
                phone=data.callback_phone,
                availability=data.callback_availability,
                consent=data.callback_consent,
            ),
            idempotency_key=f"{idempotency_key}:callback" if idempotency_key else None,
        )

    queue_notifications(session, settings, thread, event="merchant_message", message=message)
    return thread, message


def add_message(
    session: Session,
    settings: Settings,
    *,
    thread: SupportThread,
    user_id: uuid.UUID,
    data: SupportMessageCreate,
    author_type: str,
    is_platform_admin: bool = False,
    idempotency_key: str | None = None,
) -> SupportMessage:
    if thread.status == SupportThreadStatus.CLOSED:
        raise DomainError(409, "support_thread_closed", "La conversación está cerrada")

    if idempotency_key:
        existing = session.scalar(
            select(SupportMessage).where(
                SupportMessage.thread_id == thread.id,
                SupportMessage.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing

    created = _count_messages_since(session, thread.id, user_id)
    if created >= settings.support_message_rate_limit_per_day:
        raise _rate_limited("Has alcanzado el límite de mensajes por hoy en esta conversación")

    body = _validate_body(settings, data.body)
    # Quien responde ha leído lo anterior: así los no leídos reflejan lo que
    # de verdad falta por atender, no el historial completo de la conversación.
    mark_read(
        session,
        thread,
        side=(
            "platform"
            if is_platform_admin or author_type == SupportAuthorType.PLATFORM
            else "merchant"
        ),
    )
    message = SupportMessage(
        thread_id=thread.id,
        merchant_id=thread.merchant_id,
        author_type=(
            SupportAuthorType.PLATFORM
            if is_platform_admin or author_type == SupportAuthorType.PLATFORM
            else SupportAuthorType.MERCHANT
        ),
        author_user_id=user_id,
        body=body,
        idempotency_key=idempotency_key,
    )
    session.add(message)
    thread.last_message_at = utcnow()
    thread.status = (
        SupportThreadStatus.WAITING_PLATFORM
        if message.author_type == SupportAuthorType.MERCHANT
        else SupportThreadStatus.WAITING_MERCHANT
    )
    session.flush()

    event = (
        "merchant_message"
        if message.author_type == SupportAuthorType.MERCHANT
        else "platform_message"
    )
    queue_notifications(session, settings, thread, event=event, message=message)
    return message


def request_callback(
    session: Session,
    settings: Settings,
    *,
    thread: SupportThread,
    user_id: uuid.UUID,
    data: SupportCallbackRequestCreate,
    idempotency_key: str | None = None,
) -> SupportCallbackRequest:
    if thread.status == SupportThreadStatus.CLOSED:
        raise DomainError(409, "support_thread_closed", "La conversación está cerrada")
    if idempotency_key:
        existing = session.scalar(
            select(SupportCallbackRequest).where(
                SupportCallbackRequest.thread_id == thread.id,
                SupportCallbackRequest.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            return existing

    created = _count_callbacks_since(session, user_id)
    if created >= settings.support_callback_rate_limit_per_day:
        raise _rate_limited("Has alcanzado el límite de solicitudes de llamada por hoy")

    request = SupportCallbackRequest(
        thread_id=thread.id,
        merchant_id=thread.merchant_id,
        phone_encrypted=encrypt_text(settings, data.phone),
        availability=data.availability,
        requested_by_user_id=user_id,
        idempotency_key=idempotency_key,
    )
    session.add(request)
    session.flush()
    queue_notifications(session, settings, thread, event="callback_requested", callback=request)
    return request


def close_thread(session: Session, thread: SupportThread) -> SupportThread:
    thread.status = SupportThreadStatus.CLOSED
    thread.closed_at = utcnow()
    session.flush()
    return thread


def update_thread(
    session: Session, thread: SupportThread, data: SupportThreadUpdate
) -> SupportThread:
    if data.status is not None:
        thread.status = data.status
        thread.closed_at = utcnow() if data.status == SupportThreadStatus.CLOSED else None
    if data.priority is not None:
        thread.priority = data.priority
    session.flush()
    return thread


def mark_called(
    session: Session, request: SupportCallbackRequest, *, notes: str | None = None
) -> SupportCallbackRequest:
    request.status = SupportCallbackStatus.CALLED
    request.handled_at = utcnow()
    request.notes = notes[:255] if notes else request.notes
    session.flush()
    return request


def mark_read(session: Session, thread: SupportThread, *, side: ViewerSide) -> None:
    now = utcnow()
    if side == "merchant":
        messages = session.scalars(
            select(SupportMessage).where(
                SupportMessage.thread_id == thread.id,
                SupportMessage.author_type == SupportAuthorType.PLATFORM,
                SupportMessage.read_by_merchant_at.is_(None),
            )
        ).all()
        for message in messages:
            message.read_by_merchant_at = now
    else:
        messages = session.scalars(
            select(SupportMessage).where(
                SupportMessage.thread_id == thread.id,
                SupportMessage.author_type == SupportAuthorType.MERCHANT,
                SupportMessage.read_by_platform_at.is_(None),
            )
        ).all()
        for message in messages:
            message.read_by_platform_at = now
    session.flush()


def unread_count(
    session: Session,
    *,
    merchant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    role: MerchantRole | None = None,
    side: ViewerSide,
    is_platform_admin: bool = False,
) -> int:
    conditions: list[ColumnElement[bool]] = []
    if side == "merchant":
        conditions.extend(
            [
                SupportMessage.author_type == SupportAuthorType.PLATFORM,
                SupportMessage.read_by_merchant_at.is_(None),
            ]
        )
    else:
        conditions.extend(
            [
                SupportMessage.author_type == SupportAuthorType.MERCHANT,
                SupportMessage.read_by_platform_at.is_(None),
            ]
        )
    if side == "merchant":
        if merchant_id is not None:
            conditions.append(SupportMessage.merchant_id == merchant_id)
        if not is_platform_admin and role == MerchantRole.STAFF and user_id is not None:
            conditions.append(SupportMessage.thread_id.in_(_staff_thread_ids(session, user_id)))
    count = session.scalar(select(func.count()).select_from(SupportMessage).where(*conditions))
    return int(count or 0)


def _staff_thread_ids(session: Session, user_id: uuid.UUID) -> list[uuid.UUID]:
    return list(
        session.scalars(
            select(SupportThread.id).where(SupportThread.created_by_user_id == user_id)
        ).all()
    )


def _thread_for_merchant(
    session: Session,
    *,
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MerchantRole | None,
    is_platform_admin: bool,
) -> SupportThread:
    thread = session.get(SupportThread, thread_id)
    if thread is None:
        raise not_found("Conversación")
    _ensure_merchant_can_view(
        thread,
        merchant_id=merchant_id,
        user_id=user_id,
        role=role,
        is_platform_admin=is_platform_admin,
    )
    return thread


def detail_for_merchant(
    session: Session,
    settings: Settings,
    *,
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MerchantRole | None,
    is_platform_admin: bool = False,
) -> SupportThreadDetailOut:
    thread = _thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=user_id,
        role=role,
        is_platform_admin=is_platform_admin,
    )
    return _detail_out(session, settings, thread, side="merchant", include_private=False)


def detail_for_platform(
    session: Session, settings: Settings, thread_id: uuid.UUID
) -> SupportThreadDetailOut:
    thread = session.get(SupportThread, thread_id)
    if thread is None:
        raise not_found("Conversación")
    return _detail_out(session, settings, thread, side="platform", include_private=True)


def list_for_merchant(
    session: Session,
    *,
    merchant_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MerchantRole | None,
    is_platform_admin: bool = False,
    status: str | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SupportThreadOut], int]:
    conditions: list[ColumnElement[bool]] = [SupportThread.merchant_id == merchant_id]
    if not is_platform_admin and role == MerchantRole.STAFF:
        conditions.append(SupportThread.created_by_user_id == user_id)
    if status:
        conditions.append(SupportThread.status == status)
    if q:
        term = f"%{q.strip()}%"
        conditions.append(
            or_(SupportThread.subject.ilike(term), SupportThread.category.ilike(term))
        )
    total = int(
        session.scalar(select(func.count()).select_from(SupportThread).where(*conditions)) or 0
    )
    rows = session.scalars(
        select(SupportThread)
        .where(*conditions)
        .order_by(SupportThread.last_message_at.desc(), SupportThread.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [thread_out(session, row, side="merchant") for row in rows], total


def list_for_platform(
    session: Session,
    *,
    status: str | None = None,
    merchant_id: uuid.UUID | None = None,
    q: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[SupportThreadOut], int]:
    conditions: list[ColumnElement[bool]] = []
    if status:
        conditions.append(SupportThread.status == status)
    if merchant_id:
        conditions.append(SupportThread.merchant_id == merchant_id)
    if q:
        term = f"%{q.strip()}%"
        merchant_ids = select(Merchant.id).where(Merchant.name.ilike(term))
        conditions.append(
            or_(SupportThread.subject.ilike(term), SupportThread.merchant_id.in_(merchant_ids))
        )
    total = int(
        session.scalar(select(func.count()).select_from(SupportThread).where(*conditions)) or 0
    )
    rows = session.scalars(
        select(SupportThread)
        .where(*conditions)
        .order_by(SupportThread.last_message_at.desc(), SupportThread.id)
        .limit(limit)
        .offset(offset)
    ).all()
    return [
        thread_out(session, row, side="platform", include_merchant_name=True) for row in rows
    ], total


def thread_for_platform(session: Session, thread_id: uuid.UUID) -> SupportThread:
    thread = session.get(SupportThread, thread_id)
    if thread is None:
        raise not_found("Conversación")
    return thread


def callback_for_platform(
    session: Session, thread_id: uuid.UUID, request_id: uuid.UUID
) -> SupportCallbackRequest:
    request = session.get(SupportCallbackRequest, request_id)
    if request is None or request.thread_id != thread_id:
        raise not_found("Solicitud de llamada")
    return request


def notification_for_platform(session: Session, notification_id: uuid.UUID) -> SupportNotification:
    notification = session.get(SupportNotification, notification_id)
    if notification is None:
        raise not_found("Aviso")
    return notification


def thread_for_merchant(
    session: Session,
    *,
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    user_id: uuid.UUID,
    role: MerchantRole | None,
    is_platform_admin: bool = False,
) -> SupportThread:
    return _thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=user_id,
        role=role,
        is_platform_admin=is_platform_admin,
    )
