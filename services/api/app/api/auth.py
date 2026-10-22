"""Endpoints de autenticación (AGENTS.md §12.3, §8.3)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.exc import SQLAlchemyError

from app.api.deps import ContextDep, DbSession
from app.core.config import Settings, get_settings
from app.core.security import SESSION_COOKIE_NAME, LoginRateLimiter, verify_password
from app.domain.errors import (
    DomainError,
    invalid_credentials,
    login_rate_limited,
)
from app.schemas.auth import LoginRequest, PasswordChangeRequest, SessionPayload
from app.services import auth as auth_service
from app.services.audit import record_audit
from app.services.auth import email_hash

router = APIRouter(prefix="/auth", tags=["autenticación"])

_rate_limiter: LoginRateLimiter | None = None


def get_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> LoginRateLimiter:
    """Una sola instancia por proceso; las pruebas la vacían con `reset_rate_limiter`."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = LoginRateLimiter(
            max_attempts=settings.auth_login_max_attempts,
            window_seconds=settings.auth_login_window_seconds,
        )
    return _rate_limiter


def reset_rate_limiter() -> None:
    global _rate_limiter
    _rate_limiter = None


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.auth_session_ttl_seconds,
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
        path="/",
    )


def _clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.is_production,
    )


@router.post("/login", response_model=SessionPayload)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[LoginRateLimiter, Depends(get_rate_limiter)],
) -> SessionPayload:
    """Abre sesión y fija la cookie HttpOnly (el token nunca va en el body)."""
    key = f"{_client_ip(request)}|{payload.email.strip().lower()}"
    decision = limiter.check(key)
    if not decision.allowed:
        raise login_rate_limited(decision.retry_after_seconds)

    try:
        user = auth_service.authenticate(session, str(payload.email), payload.password)
    except DomainError:
        limiter.record_failure(key)
        # El registro debe sobrevivir al rollback de la excepción: se confirma
        # aquí y luego se propaga el error.
        record_audit(
            session,
            action="auth.login.failed",
            entity_type="user",
            actor_type="system",
            metadata={"email_hash": email_hash(payload.email, settings.auth_email_hash_pepper)},
        )
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover - la auditoría no rompe el login
            session.rollback()
        raise

    limiter.reset(key)
    token = auth_service.create_session(session, user, settings)
    context = auth_service.load_context(session, token, settings)
    record_audit(
        session,
        action="auth.login.success",
        entity_type="user",
        actor_id=user.id,
        entity_id=str(user.id),
    )
    session.commit()
    _set_session_cookie(response, token, settings)
    return auth_service.build_session_payload(session, context)


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, bool]:
    """Revoca la sesión en servidor y borra la cookie (idempotente)."""
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if token:
        auth_service.revoke_session(session, token, settings)
        record_audit(session, action="auth.logout", entity_type="user", actor_type="system")
        session.commit()
    _clear_session_cookie(response, settings)
    return {"ok": True}


@router.get("/me", response_model=SessionPayload)
def me(context: ContextDep, session: DbSession) -> SessionPayload:
    """Identidad y comercios visibles para la sesión actual (401 sin sesión)."""
    return auth_service.build_session_payload(session, context)


@router.post("/change-password")
def change_password(
    payload: "PasswordChangeRequest",
    request: Request,
    response: Response,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    limiter: Annotated[LoginRateLimiter, Depends(get_rate_limiter)],
    context: ContextDep,
) -> dict[str, bool]:
    """Cambia la contraseña del usuario autenticado (§8.3, D‑1 de la auditoría).

    Exige la contraseña actual (robo de cookie no implica cambio), revoca
    **todas** las sesiones del usuario y reabre una para este navegador.
    """
    key = f"{_client_ip(request)}|{context.user.email}"
    decision = limiter.check(key)
    if not decision.allowed:
        raise login_rate_limited(decision.retry_after_seconds)
    if not verify_password(
        context.user.password_hash,
        payload.current_password,
    ):
        record_audit(
            session,
            action="auth.password_change.failed",
            entity_type="user",
            actor_id=context.user.id,
            entity_id=str(context.user.id),
        )
        session.commit()
        raise invalid_credentials()
    # La contraseña nueva se valida a la vez que se guarda (longitud, etc.).
    auth_service.change_password(session, context.user, payload.new_password)
    record_audit(
        session,
        action="auth.password_change.success",
        entity_type="user",
        actor_id=context.user.id,
        entity_id=str(context.user.id),
    )
    # Todas las sesiones quedaron revocadas: abre una nueva para este
    # navegador, invalidando cualquier otra copia robada (§8.3).
    token = auth_service.create_session(session, context.user, settings)
    session.commit()
    _set_session_cookie(response, token, settings)
    return {"ok": True}
