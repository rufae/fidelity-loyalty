"""API de soporte B2B (Plan.md §9).

Dos superficies separadas:

- `/merchants/{merchant_id}/support`: conversaciones del comercio. `owner`,
  `admin` y `staff` entran; `staff` solo ve sus propios hilos. `viewer` queda
  fuera con la misma respuesta 404 que un comercio ajeno (§8.2).
- `/platform/support`: buzón global de la plataforma, solo
  `platform_owner`/`platform_admin`.

Ninguna ruta es pública. El teléfono de llamada solo aparece en el buzón de
plataforma; el comercio conserva el mensaje, no el dato sensible.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Query

from app.api.deps import DbSession, PlatformAdminDep, merchant_access
from app.core.config import Settings, get_settings
from app.domain.roles import MERCHANT_OPERATOR_ROLES
from app.schemas.support import (
    SupportCallbackRequestCreate,
    SupportCallbackRequestOut,
    SupportMessageCreate,
    SupportMessageOut,
    SupportNotificationOut,
    SupportThreadCreate,
    SupportThreadDetailOut,
    SupportThreadOut,
    SupportThreadPageOut,
    SupportThreadUpdate,
    SupportUnreadOut,
)
from app.services import support as support_service
from app.services import support_notifications
from app.services.audit import record_audit

merchant_router = APIRouter(prefix="/merchants/{merchant_id}/support", tags=["soporte"])
platform_router = APIRouter(prefix="/platform/support", tags=["soporte-plataforma"])

support_operator = merchant_access(MERCHANT_OPERATOR_ROLES)
SupportOperatorDep = Annotated[object, Depends(support_operator)]
IdempotencyKey = Annotated[
    str | None, Header(alias="Idempotency-Key", min_length=1, max_length=120)
]
SupportSettings = Annotated[Settings, Depends(get_settings)]
_STATUS_PATTERN = "^(open|waiting_platform|waiting_merchant|resolved|closed)$"


@merchant_router.get("", response_model=SupportThreadPageOut)
def list_threads(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: SupportOperatorDep,
    status: Annotated[str | None, Query(pattern=_STATUS_PATTERN)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SupportThreadPageOut:
    rows, total = support_service.list_for_merchant(
        session,
        merchant_id=merchant_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
        status=status,
        q=q,
        limit=limit,
        offset=offset,
    )
    return SupportThreadPageOut(items=rows, total=total, limit=limit, offset=offset)


@merchant_router.post("", response_model=SupportThreadDetailOut, status_code=201)
def create_thread(
    merchant_id: uuid.UUID,
    data: SupportThreadCreate,
    session: DbSession,
    context: SupportOperatorDep,
    settings: SupportSettings,
    idempotency_key: IdempotencyKey = None,
) -> SupportThreadDetailOut:
    thread, message = support_service.create_thread(
        session,
        settings,
        merchant_id=merchant_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        data=data,
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
        idempotency_key=idempotency_key,
    )
    record_audit(
        session,
        action="support.thread.created",
        entity_type="support_thread",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(thread.id),
        metadata={"fields": [thread.category]},
    )
    session.commit()
    return support_service.detail_for_merchant(
        session,
        settings,
        merchant_id=merchant_id,
        thread_id=thread.id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )


@merchant_router.get("/unread-count", response_model=SupportUnreadOut)
def unread_count(
    merchant_id: uuid.UUID,
    session: DbSession,
    context: SupportOperatorDep,
) -> SupportUnreadOut:
    return SupportUnreadOut(
        count=support_service.unread_count(
            session,
            merchant_id=merchant_id,
            user_id=context.user.id,  # type: ignore[attr-defined]
            role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
            side="merchant",
            is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
        )
    )


@merchant_router.get("/{thread_id}", response_model=SupportThreadDetailOut)
def get_thread(
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    session: DbSession,
    context: SupportOperatorDep,
    settings: SupportSettings,
) -> SupportThreadDetailOut:
    return support_service.detail_for_merchant(
        session,
        settings,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )


@merchant_router.post("/{thread_id}/messages", response_model=SupportMessageOut, status_code=201)
def add_message(
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    data: SupportMessageCreate,
    session: DbSession,
    context: SupportOperatorDep,
    settings: SupportSettings,
    idempotency_key: IdempotencyKey = None,
) -> SupportMessageOut:
    thread = support_service.thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )
    message = support_service.add_message(
        session,
        settings,
        thread=thread,
        user_id=context.user.id,  # type: ignore[attr-defined]
        data=data,
        author_type="merchant",
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
        idempotency_key=idempotency_key,
    )
    record_audit(
        session,
        action="support.message.created",
        entity_type="support_message",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(message.id),
    )
    session.commit()
    return support_service.message_out(session, message)


@merchant_router.post(
    "/{thread_id}/callback-requests", response_model=SupportCallbackRequestOut, status_code=201
)
def request_callback(
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    data: SupportCallbackRequestCreate,
    session: DbSession,
    context: SupportOperatorDep,
    settings: SupportSettings,
    idempotency_key: IdempotencyKey = None,
) -> SupportCallbackRequestOut:
    thread = support_service.thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )
    request = support_service.request_callback(
        session,
        settings,
        thread=thread,
        user_id=context.user.id,  # type: ignore[attr-defined]
        data=data,
        idempotency_key=idempotency_key,
    )
    record_audit(
        session,
        action="support.callback.requested",
        entity_type="support_callback_request",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(request.id),
    )
    session.commit()
    # El comercio no recibe el teléfono: solo confirma que la solicitud existe.
    return SupportCallbackRequestOut(
        id=request.id,
        status=request.status,
        availability=request.availability,
        requested_at=request.requested_at,
        handled_at=request.handled_at,
    )


@merchant_router.post("/{thread_id}/close", response_model=SupportThreadOut)
def close_thread(
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    session: DbSession,
    context: SupportOperatorDep,
    settings: SupportSettings,
) -> SupportThreadOut:
    thread = support_service.thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )
    support_service.close_thread(session, thread)
    record_audit(
        session,
        action="support.thread.status_changed",
        entity_type="support_thread",
        actor_id=context.user.id,  # type: ignore[attr-defined]
        merchant_id=merchant_id,
        entity_id=str(thread.id),
        metadata={"new_status": thread.status},
    )
    session.commit()
    return support_service.thread_out(session, thread, side="merchant")


@merchant_router.post("/{thread_id}/read", response_model=SupportUnreadOut)
def mark_thread_read(
    merchant_id: uuid.UUID,
    thread_id: uuid.UUID,
    session: DbSession,
    context: SupportOperatorDep,
) -> SupportUnreadOut:
    thread = support_service.thread_for_merchant(
        session,
        merchant_id=merchant_id,
        thread_id=thread_id,
        user_id=context.user.id,  # type: ignore[attr-defined]
        role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
        is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
    )
    support_service.mark_read(session, thread, side="merchant")
    session.commit()
    return SupportUnreadOut(
        count=support_service.unread_count(
            session,
            merchant_id=merchant_id,
            user_id=context.user.id,  # type: ignore[attr-defined]
            role=context.merchant_role(merchant_id),  # type: ignore[attr-defined]
            side="merchant",
            is_platform_admin=context.is_platform_admin,  # type: ignore[attr-defined]
        )
    )


@platform_router.get("/threads", response_model=SupportThreadPageOut)
def platform_list_threads(
    session: DbSession,
    context: PlatformAdminDep,  # noqa: ARG001
    status: Annotated[str | None, Query(pattern=_STATUS_PATTERN)] = None,
    merchant_id: uuid.UUID | None = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SupportThreadPageOut:
    rows, total = support_service.list_for_platform(
        session, status=status, merchant_id=merchant_id, q=q, limit=limit, offset=offset
    )
    return SupportThreadPageOut(items=rows, total=total, limit=limit, offset=offset)


@platform_router.get("/threads/{thread_id}", response_model=SupportThreadDetailOut)
def platform_get_thread(
    thread_id: uuid.UUID,
    session: DbSession,
    context: PlatformAdminDep,  # noqa: ARG001
    settings: SupportSettings,
) -> SupportThreadDetailOut:
    return support_service.detail_for_platform(session, settings, thread_id)


@platform_router.post(
    "/threads/{thread_id}/messages", response_model=SupportMessageOut, status_code=201
)
def platform_add_message(
    thread_id: uuid.UUID,
    data: SupportMessageCreate,
    session: DbSession,
    context: PlatformAdminDep,
    settings: SupportSettings,
    idempotency_key: IdempotencyKey = None,
) -> SupportMessageOut:
    thread = support_service.thread_for_platform(session, thread_id)
    message = support_service.add_message(
        session,
        settings,
        thread=thread,
        user_id=context.user.id,
        data=data,
        author_type="platform",
        is_platform_admin=True,
        idempotency_key=idempotency_key,
    )
    record_audit(
        session,
        action="support.message.created",
        entity_type="support_message",
        actor_id=context.user.id,
        merchant_id=thread.merchant_id,
        entity_id=str(message.id),
    )
    session.commit()
    return support_service.message_out(session, message)


@platform_router.patch("/threads/{thread_id}", response_model=SupportThreadOut)
def platform_update_thread(
    thread_id: uuid.UUID,
    data: SupportThreadUpdate,
    session: DbSession,
    context: PlatformAdminDep,
    settings: SupportSettings,
) -> SupportThreadOut:
    thread = support_service.thread_for_platform(session, thread_id)
    previous = thread.status
    support_service.update_thread(session, thread, data)
    record_audit(
        session,
        action="support.thread.status_changed",
        entity_type="support_thread",
        actor_id=context.user.id,
        merchant_id=thread.merchant_id,
        entity_id=str(thread.id),
        metadata={"previous_status": previous, "new_status": thread.status},
    )
    session.commit()
    return support_service.thread_out(session, thread, side="platform", include_merchant_name=True)


@platform_router.post(
    "/threads/{thread_id}/callback-requests/{request_id}/mark-called",
    response_model=SupportCallbackRequestOut,
)
def platform_mark_called(
    thread_id: uuid.UUID,
    request_id: uuid.UUID,
    session: DbSession,
    context: PlatformAdminDep,
    settings: SupportSettings,
    notes: Annotated[str | None, Query(max_length=255)] = None,
) -> SupportCallbackRequestOut:
    request = support_service.callback_for_platform(session, thread_id, request_id)
    support_service.mark_called(session, request, notes=notes)
    record_audit(
        session,
        action="support.callback.handled",
        entity_type="support_callback_request",
        actor_id=context.user.id,
        merchant_id=request.merchant_id,
        entity_id=str(request.id),
    )
    session.commit()
    return support_service.callback_out(session, settings, request, include_phone=True)


@platform_router.post("/threads/{thread_id}/read", response_model=SupportUnreadOut)
def platform_mark_read(
    thread_id: uuid.UUID,
    session: DbSession,
    context: PlatformAdminDep,
) -> SupportUnreadOut:
    thread = support_service.thread_for_platform(session, thread_id)
    support_service.mark_read(session, thread, side="platform")
    session.commit()
    return SupportUnreadOut(count=support_service.unread_count(session, side="platform"))


@platform_router.get("/unread-count", response_model=SupportUnreadOut)
def platform_unread_count(
    session: DbSession,
    context: PlatformAdminDep,  # noqa: ARG001
) -> SupportUnreadOut:
    return SupportUnreadOut(count=support_service.unread_count(session, side="platform"))


@platform_router.post(
    "/notifications/{notification_id}/retry", response_model=SupportNotificationOut
)
def retry_notification(
    notification_id: uuid.UUID,
    session: DbSession,
    context: PlatformAdminDep,
    settings: SupportSettings,
) -> SupportNotificationOut:
    notification = support_service.notification_for_platform(session, notification_id)
    support_notifications.retry_notification(session, notification, settings)
    record_audit(
        session,
        action="support.notification.retried",
        entity_type="support_notification",
        actor_id=context.user.id,
        merchant_id=None,
        entity_id=str(notification.id),
    )
    session.commit()
    return SupportNotificationOut.model_validate(notification)
