"""Fixtures comunes de la FASE 2.

Las pruebas de API corren contra **SQLite en memoria** (misma sesión
sobrescrita en la dependencia `get_session`): rápido y sin dependencias.
Las migraciones se validan contra PostgreSQL real en el arranque del contenedor
(`alembic upgrade head` en el CMD del Dockerfile), verificado en vivo.
"""

from collections.abc import Iterator
from urllib.parse import parse_qs, urlparse

import pytest
from app.api.auth import reset_rate_limiter
from app.core.config import Settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_session
from app.domain.roles import MerchantRole, PlatformRole, UserStatus
from app.main import app
from app.models.loyalty import LoyaltyProgram
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.user import MerchantUser, User
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

OWNER_EMAIL = "owner-a@example.com"
OWNER_B_EMAIL = "owner-b@example.com"
STAFF_EMAIL = "staff-a@example.com"
PLATFORM_EMAIL = "admin@plataforma.example.com"
PASSWORD = "contrasena-larga-1234"
EMAIL_OUTBOX: list[dict[str, str]] = []


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()


@pytest.fixture()
def client(db_session: Session, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    def override_get_session() -> Iterator[Session]:
        yield db_session

    from app.api.public import (
        card_access_limiter,
        enroll_limiter,
        public_limiter,
        public_read_limiter,
    )
    from app.services import email as email_service

    EMAIL_OUTBOX.clear()

    def capture_email(
        settings: Settings,
        recipient: str,
        subject: str,
        text: str,
        action_url: str,
        cta_label: str = "Abrir mi tarjeta",
        merchant_name: str = "",
    ) -> None:
        EMAIL_OUTBOX.append(
            {"recipient": recipient, "subject": subject, "text": text, "action_url": action_url}
        )

    monkeypatch.setattr(email_service, "ensure_email_configured", lambda settings: None)
    monkeypatch.setattr(email_service, "send_email", capture_email)

    app.dependency_overrides[get_session] = override_get_session
    reset_rate_limiter()
    public_limiter.reset()
    public_read_limiter.reset()
    enroll_limiter.reset()
    card_access_limiter.reset()
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    reset_rate_limiter()


def email_token(*, subject: str | None = None) -> str:

    matches = [mail for mail in EMAIL_OUTBOX if subject is None or subject in mail["subject"]]
    assert matches, f"No se encontró un correo con asunto {subject!r}"
    return parse_qs(urlparse(matches[-1]["action_url"]).query)["token"][0]


def enroll_verified(
    client: TestClient,
    db_session: Session,
    merchant_slug: str,
    program_slug: str,
    body: dict[str, object],
) -> tuple[TestClient, str]:
    """Crea un alta y confirma el correo como lo haría el destinatario."""
    response = client.post(
        f"/api/v1/public/programs/{merchant_slug}/{program_slug}/enroll", json=body
    )
    assert response.status_code == 201, response.text
    if "Confirm" in EMAIL_OUTBOX[-1]["subject"]:
        confirmed = client.post(
            "/api/v1/public/email/verify", json={"token": email_token(subject="Confirma")}
        )
        assert confirmed.status_code == 200, confirmed.text
    else:
        exchanged = client.post(
            "/api/v1/public/card-access", json={"token": email_token(subject="Tu tarjeta")}
        )
        assert exchanged.status_code == 200, exchanged.text
    email = str(body["email"]).strip().lower()
    member = db_session.query(Member).filter(Member.email == email).one()
    program = db_session.query(LoyaltyProgram).filter(LoyaltyProgram.slug == program_slug).one()
    membership = (
        db_session.query(Membership)
        .filter(
            Membership.member_id == member.id,
            Membership.program_id == program.id,
        )
        .one()
    )
    return client, membership.public_token


def create_user(
    session: Session,
    email: str,
    *,
    password: str = PASSWORD,
    platform_role: PlatformRole | None = None,
    display_name: str = "Usuario de prueba",
) -> User:
    user = User(
        email=email,
        password_hash=hash_password(password),
        display_name=display_name,
        platform_role=platform_role.value if platform_role else None,
        status=UserStatus.ACTIVE.value,
    )
    session.add(user)
    session.flush()
    return user


def create_merchant_with_owner(
    session: Session, owner: User, name: str = "Cafetería de prueba"
) -> Merchant:
    from app.models.merchant import slugify

    base = slugify(name)
    slug = base
    suffix = 2
    while session.query(Merchant).filter(Merchant.slug == slug).first() is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    merchant = Merchant(name=name, slug=slug)
    session.add(merchant)
    session.flush()
    session.add(
        MerchantUser(
            user_id=owner.id,
            merchant_id=merchant.id,
            role=MerchantRole.OWNER.value,
            status=UserStatus.ACTIVE.value,
        )
    )
    session.flush()
    return merchant


def add_member(
    session: Session, user: User, merchant: Merchant, role: MerchantRole
) -> MerchantUser:
    membership = MerchantUser(
        user_id=user.id,
        merchant_id=merchant.id,
        role=role.value,
        status=UserStatus.ACTIVE.value,
    )
    session.add(membership)
    session.flush()
    return membership


def login(client: TestClient, email: str, password: str = PASSWORD) -> None:
    response = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text


__all__ = [
    "OWNER_EMAIL",
    "OWNER_B_EMAIL",
    "STAFF_EMAIL",
    "PLATFORM_EMAIL",
    "PASSWORD",
    "add_member",
    "create_merchant_with_owner",
    "create_user",
    "login",
]
