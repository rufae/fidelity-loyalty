"""Matriz de autorización por rol en rutas de comercio (§8.1, §8.2).

El backend es el control definitivo: la interfaz se adapta por rol, pero quien
llame a la API directamente recibe 404 (idéntico a un comercio inexistente)
cuando su rol no permite la operación, y 200/201 cuando sí lo permite. Estas
pruebas fijan esa matriz para evitar que un cambio la relaje sin avisar.

    | Sección                 | owner/admin | staff | viewer | público |
    |-------------------------|-------------|-------|--------|---------|
    | Programa y recompensas  |      ✓      |   ✗   |   ✗    |    ✗    |
    | Clientes (listado)      |      ✓      |   ✗   |   ✗    |    ✗    |
    | Operaciones (lookup)    |      ✓      |   ✓   |   ✗    |    ✗    |
    | NFC y reseñas           |      ✓      |   ✗   |   ✗    |    ✗    |
    | Resumen (dashboard)     |      ✓      |   ✗   |   ✗    |    ✗    |
"""

import uuid

from app.domain.roles import MerchantRole
from app.models.members import Member, Membership
from app.services.members import new_public_token
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import add_member, create_merchant_with_owner, create_user, login


def _login(client: TestClient, email: str) -> None:
    login(client, email)


def _roles_world(db_session: Session) -> tuple[uuid.UUID, str, str, str]:
    """Comercio con owner, staff y viewer. Devuelve (id, owner, staff, viewer)."""
    paso = str(uuid.uuid4())[:8]
    owner = create_user(db_session, f"owner-matriz-{paso}@example.com")
    staff = create_user(db_session, f"staff-matriz-{paso}@example.com")
    viewer = create_user(db_session, f"viewer-matriz-{paso}@example.com")
    merchant = create_merchant_with_owner(db_session, owner, name=f"Matriz {paso}")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    add_member(db_session, viewer, merchant, MerchantRole.VIEWER)
    db_session.commit()
    return merchant.id, owner.email, staff.email, viewer.email


def _published_program(client: TestClient, merchant_id: uuid.UUID, owner_email: str) -> str:
    _login(client, owner_email)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club Matriz", "terms": "Prueba de roles."},
    ).json()
    client.post(f"/api/v1/merchants/{merchant_id}/programs/{program['id']}/publish")
    client.post("/api/v1/auth/logout")
    return str(program["id"])


def _member_card(db_session: Session, merchant_id: uuid.UUID, program_id: str) -> str:
    """Membresía real (con token) para que la búsqueda autorizada dé 200."""
    member = Member(
        merchant_id=merchant_id,
        email=f"cliente-matriz-{uuid.uuid4().hex[:8]}@example.com",
        display_name="Cliente Matriz",
    )
    db_session.add(member)
    db_session.flush()
    membership = Membership(
        merchant_id=merchant_id,
        program_id=uuid.UUID(program_id),
        member_id=member.id,
        public_token=new_public_token(),
    )
    db_session.add(membership)
    db_session.commit()
    return membership.public_token


def _admin_routes(client: TestClient, merchant_id: uuid.UUID) -> list[int]:
    """Rutas que exigen owner/admin (o admin de plataforma)."""
    return [
        client.get(f"/api/v1/merchants/{merchant_id}/programs").status_code,
        client.get(f"/api/v1/merchants/{merchant_id}/memberships").status_code,
        client.get(f"/api/v1/merchants/{merchant_id}/nfc-tags").status_code,
        client.get(f"/api/v1/merchants/{merchant_id}/dashboard/summary").status_code,
        client.get(f"/api/v1/merchants/{merchant_id}/dashboard/onboarding").status_code,
        client.get(f"/api/v1/merchants/{merchant_id}/review-destination").status_code,
    ]


def _lookup(client: TestClient, merchant_id: uuid.UUID, token: str) -> int:
    """Búsqueda de tarjeta: exige rol operativo (owner/admin/staff)."""
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/lookup",
        json={"token": token},
    )
    return int(response.status_code)


def test_matriz_de_permisos_por_rol(client: TestClient, db_session: Session) -> None:
    merchant_id, owner_email, staff_email, viewer_email = _roles_world(db_session)
    program_id = _published_program(client, merchant_id, owner_email)
    card_token = _member_card(db_session, merchant_id, program_id)

    # Owner: administración y operaciones permitidas.
    _login(client, owner_email)
    assert all(code == 200 for code in _admin_routes(client, merchant_id))
    assert _lookup(client, merchant_id, card_token) == 200
    client.post("/api/v1/auth/logout")

    # Staff: nada de administración; operar tarjetas sí (con tarjeta real).
    _login(client, staff_email)
    assert set(_admin_routes(client, merchant_id)) == {404}
    assert _lookup(client, merchant_id, card_token) == 200
    client.post("/api/v1/auth/logout")

    # Viewer: solo lectura de la ficha; sin administración ni operaciones.
    _login(client, viewer_email)
    assert set(_admin_routes(client, merchant_id)) == {404}
    assert _lookup(client, merchant_id, card_token) == 404
    assert client.get(f"/api/v1/merchants/{merchant_id}").status_code == 200
    client.post("/api/v1/auth/logout")

    # Sin sesión: 401 en todas (la autenticación precede a la autorización).
    assert client.get(f"/api/v1/merchants/{merchant_id}/programs").status_code == 401
    assert _lookup(client, merchant_id, card_token) == 401
