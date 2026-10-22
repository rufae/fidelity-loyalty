"""Servicio de autenticación: login, sesiones y contexto de autorización.

La sesión es la **única** fuente de la identidad: ningún `merchant_id` o
`role` enviado por el navegador se usa para autorizar (§8.2).
"""

import hashlib
import hmac
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import hash_password, verify_password
from app.domain.errors import DomainError, invalid_credentials, unauthorized
from app.domain.roles import MerchantRole, MerchantStatus, PlatformRole, UserStatus
from app.domain.tokens import get_session_secret, new_session_id, sign_session_id
from app.models.merchant import Merchant
from app.models.user import MerchantUser, User, UserSession, utcnow
from app.schemas.auth import MerchantMembership, SessionPayload, SessionUser


@dataclass(frozen=True)
class SessionContext:
    """Resultado de validar una cookie: identidad + permisos calculados en servidor."""

    user: User
    platform_role: PlatformRole | None = None
    merchant_roles: dict[uuid.UUID, MerchantRole] = field(default_factory=dict)

    @property
    def is_platform_admin(self) -> bool:
        return self.platform_role is not None

    def merchant_role(self, merchant_id: uuid.UUID) -> MerchantRole | None:
        return self.merchant_roles.get(merchant_id)


def email_hash(email: str, pepper: str = "") -> str:
    """Huella para auditar intentos de login sin guardar el email en claro.

    Con *pepper* configurado (`AUTH_EMAIL_HASH_PEPPER`) es HMAC-SHA256: la
    huella de un correo no se puede revertir con un diccionario aunque se lea
    la base de datos o una copia (§8.1 de la auditoría).
    """
    message = email.strip().lower().encode()
    if pepper:
        return hmac.new(pepper.encode(), message, hashlib.sha256).hexdigest()
    return hashlib.sha256(message).hexdigest()


def find_user_by_email(session: Session, email: str) -> User | None:
    return session.scalar(select(User).where(User.email == email.strip().lower()))


def authenticate(session: Session, email: str, password: str) -> User:
    """Valida credenciales. Lanza `invalid_credentials` en cualquier fallo."""
    user = find_user_by_email(session, email)
    if user is None or not user.is_active:
        # Hash ficticio para que el tiempo de respuesta no revele si el email existe.
        verify_password(hash_password("decoy-password"), password)
        raise invalid_credentials()
    if not verify_password(user.password_hash, password):
        raise invalid_credentials()
    # La suspensión de un comercio debe impedir también el login de su equipo
    # (§8.2): si todas las membresías del usuario son de comercios suspendidos,
    # no puede operar. Un usuario sin comercios (p. ej. plataforma) no aplica.
    memberships = session.scalars(
        select(MerchantUser).where(
            MerchantUser.user_id == user.id, MerchantUser.status == UserStatus.ACTIVE.value
        )
    ).all()
    if memberships:
        merchant_ids = [membership.merchant_id for membership in memberships]
        activos = session.scalar(
            select(func.count())
            .select_from(Merchant)
            .where(Merchant.id.in_(merchant_ids), Merchant.status == MerchantStatus.ACTIVE.value)
        )
        if not activos:
            raise DomainError(
                403,
                "merchant_suspended",
                "El comercio está suspendido: contacta con el soporte de la plataforma",
            )
    return user


def create_session(session: Session, user: User, settings: Settings) -> str:
    """Crea la sesión en servidor y devuelve el valor completo de la cookie."""
    session_id = new_session_id()
    expires_at = utcnow() + timedelta(seconds=settings.auth_session_ttl_seconds)
    session.add(UserSession(id=session_id, user_id=user.id, expires_at=expires_at))
    user.last_login_at = utcnow()
    secret = get_session_secret(settings)
    return sign_session_id(session_id, secret)


def revoke_session(session: Session, token: str, settings: Settings) -> None:
    from app.domain.tokens import verify_session_token

    session_id = verify_session_token(token, get_session_secret(settings))
    if session_id is None:
        return
    row = session.get(UserSession, session_id)
    if row is not None and row.revoked_at is None:
        row.revoked_at = utcnow()


def load_context(session: Session, token: str, settings: Settings) -> SessionContext:
    """Convierte la cookie en un contexto de permisos. Lanza `unauthorized` si no vale."""
    from app.domain.tokens import verify_session_token

    session_id = verify_session_token(token, get_session_secret(settings))
    if session_id is None:
        raise unauthorized()
    row = session.get(UserSession, session_id)
    if row is None or not row.is_valid:
        raise unauthorized()
    user = session.get(User, row.user_id)
    if user is None or not user.is_active:
        raise unauthorized()

    memberships = session.scalars(
        select(MerchantUser).where(
            MerchantUser.user_id == user.id, MerchantUser.status == UserStatus.ACTIVE.value
        )
    ).all()
    roles: dict[uuid.UUID, MerchantRole] = {}
    for membership in memberships:
        try:
            roles[membership.merchant_id] = MerchantRole(membership.role)
        except ValueError:
            continue

    platform_role = None
    if user.platform_role is not None:
        try:
            platform_role = PlatformRole(user.platform_role)
        except ValueError:
            platform_role = None

    return SessionContext(user=user, platform_role=platform_role, merchant_roles=roles)


def build_session_payload(session: Session, context: SessionContext) -> SessionPayload:
    """Compone la respuesta de sesión con los comercios visibles para este usuario."""
    merchants: list[MerchantMembership] = []
    if context.merchant_roles:
        rows = session.scalars(
            select(Merchant).where(Merchant.id.in_(list(context.merchant_roles)))
        ).all()
        for merchant in rows:
            role = context.merchant_roles.get(merchant.id)
            if role is None:
                continue
            merchants.append(
                MerchantMembership(
                    merchant_id=merchant.id,
                    merchant_name=merchant.name,
                    merchant_slug=merchant.slug,
                    merchant_status=merchant.status,
                    role=role,
                )
            )
    return SessionPayload(
        user=SessionUser.model_validate(context.user),
        merchants=sorted(merchants, key=lambda m: m.merchant_name),
    )


def bootstrap_platform_owner(session: Session, settings: Settings) -> bool:
    """Crea el primer administrador si y solo si no existe ningún usuario (§8.3)."""
    if not settings.bootstrap_configured:
        return False
    if session.scalar(select(User.id).limit(1)) is not None:
        return False
    email = (settings.auth_bootstrap_email or "").strip().lower()
    session.add(
        User(
            email=email,
            password_hash=hash_password(settings.auth_bootstrap_password or ""),
            display_name="Administrador de plataforma",
            platform_role=PlatformRole.OWNER.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    session.flush()
    return True


def change_password(session: Session, user: User, new_password: str) -> None:
    """Cambia la contraseña y **revoca todas las sesiones** del usuario (§8.3)."""
    user.password_hash = hash_password(new_password)
    now = datetime.now(UTC)
    for row in session.scalars(select(UserSession).where(UserSession.user_id == user.id)):
        if row.revoked_at is None:
            row.revoked_at = now
