"""Dependencias de autorización (AGENTS.md §8.2, §16.2).

Reglas:
- El permiso sale **siempre** de la sesión en servidor; el `merchant_id` del
  camino solo identifica el recurso, nunca otorga acceso.
- Un comercio al que no perteneces responde `404 not_found`, igual que uno
  inexistente: no se permite enumerar comercios ajenos.
"""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.security import SESSION_COOKIE_NAME
from app.db.session import get_session
from app.domain.errors import not_found, unauthorized
from app.domain.roles import MerchantRole
from app.models.merchant import Merchant
from app.services.auth import SessionContext, load_context

DbSession = Annotated[Session, Depends(get_session)]


def get_context(
    request: Request,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> SessionContext:
    """Contexto de permisos de la petición autenticada (401 si no hay sesión válida)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise unauthorized()
    return load_context(session, token, settings)


ContextDep = Annotated[SessionContext, Depends(get_context)]


def require_platform_admin(context: ContextDep) -> SessionContext:
    if not context.is_platform_admin:
        raise unauthorized(code="platform_access_denied", message="Permiso insuficiente")
    return context


PlatformAdminDep = Annotated[SessionContext, Depends(require_platform_admin)]


def merchant_access(
    allowed_roles: set[MerchantRole] | frozenset[MerchantRole],
) -> Callable[[uuid.UUID, ContextDep, DbSession], SessionContext]:
    """Fábrica de dependencias: valida el rol permitido sobre el comercio del camino.

    Además del rol, comprueba que el comercio **no esté suspendido**: la
    suspensión debe cortar el acceso del equipo de inmediato (§8.2), con la
    misma respuesta 404 que un comercio inexistente (sin enumeración).
    """

    def dependency(
        merchant_id: uuid.UUID, context: ContextDep, session: DbSession
    ) -> SessionContext:
        # La administración de plataforma gestiona todos los comercios (§8.1):
        # el panel se la muestra, así que la API no puede devolverle 404.
        if context.is_platform_admin:
            return context
        role = context.merchant_role(merchant_id)
        if role is None or role not in allowed_roles:
            # 404 idéntico al de un comercio inexistente: sin enumeración (§8.2, §23).
            raise not_found("Comercio")
        merchant = session.get(Merchant, merchant_id)
        if merchant is None or not merchant.is_active:
            # Suspendido (o inexistente): el equipo no opera hasta reactivarlo.
            raise not_found("Comercio")
        return context

    return dependency
