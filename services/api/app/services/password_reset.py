"""Recuperación de contraseña de personal (§8.3).

Flujo en dos pasos, sin enumeración de cuentas (§8.2): la solicitud siempre
responde igual exista o no el email, y solo si existe se crea un enlace de un
solo uso (30 minutos) que llega por correo. Al confirmar el cambio se
invalidan **todas** las sesiones del usuario: si alguien había robado una
sesión activa, no sobrevive al cambio de credencial.

Vale para todo el personal (propietario, admin, staff y plataforma): todos
viven en la misma tabla `users`.
"""

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password
from app.domain.errors import DomainError
from app.domain.roles import UserStatus
from app.models.user import PasswordResetToken, User, UserSession, utcnow
from app.services import email as email_service

RESET_TTL = timedelta(minutes=30)


def _hash(raw: str) -> str:
    import hashlib

    return hashlib.sha256(raw.encode()).hexdigest()


def request_reset(session: Session, settings: Settings, email: str) -> bool:
    """Prepara el enlace si el email existe. Devuelve True si se envió correo.

    Nunca revela por la API si el email existe: el endpoint responde 202 igual
    en ambos casos (§8.2, sin enumeración de cuentas).
    """
    normalized = email.strip().lower()
    user = session.scalar(select(User).where(User.email == normalized))
    if user is None:
        return False
    # El token nuevo invalida los pendientes anteriores del usuario.
    session.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    raw = secrets.token_urlsafe(32)
    session.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=_hash(raw),
            expires_at=utcnow() + RESET_TTL,
        )
    )
    session.flush()
    base = (settings.public_base_url or "").rstrip("/")
    link = f"{base}/recuperar?token={raw}"
    email_service.send_email(
        settings,
        recipient=user.email,
        subject="Nueva contraseña para tu panel",
        text=(
            "Alguien solicitó una nueva contraseña para tu cuenta del panel de "
            "fidelización. Si has sido tú, pulsa el botón para definirla. El "
            "enlace caduca en 30 minutos y solo puede usarse una vez."
        ),
        action_url=link,
        cta_label="Elegir nueva contraseña",
        merchant_name="",
    )
    return True


def confirm_reset(session: Session, raw: str, new_password: str) -> User:
    """Consume el token, cambia la contraseña e invalida todas las sesiones."""
    token_hash = _hash(raw)
    token = session.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    if token is None or token.used_at is not None:
        raise DomainError(400, "invalid_reset_token", "El enlace no es válido o ya se usó")
    expires = token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        raise DomainError(400, "invalid_reset_token", "El enlace ha caducado")
    if len(new_password) < 10:
        raise DomainError(422, "weak_password", "La contraseña debe tener al menos 10 caracteres")
    user = session.get(User, token.user_id)
    if user is None or user.status != UserStatus.ACTIVE.value:
        raise DomainError(400, "invalid_reset_token", "El enlace no es válido")

    user.password_hash = hash_password(new_password)
    token.used_at = utcnow()
    # Rotación de credenciales (§8.3): fuera todas las sesiones del usuario.
    session.execute(
        update(UserSession)
        .where(UserSession.user_id == user.id, UserSession.revoked_at.is_(None))
        .values(revoked_at=utcnow())
    )
    session.flush()
    return user
