"""Pruebas de altas públicas y membresías (FASE 4)."""

import uuid
from datetime import timedelta

from app.domain.roles import MerchantRole
from app.models.card_access import MemberEmailToken
from app.models.members import Membership
from app.models.user import utcnow
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import (
    EMAIL_OUTBOX,
    OWNER_EMAIL,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    email_token,
    enroll_verified,
    login,
)

TERMS = "1 sello por visita. Canje desde 10 sellos."


def _active_program(client: TestClient, db_session: Session) -> tuple[uuid.UUID, str]:
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant.id}/programs",
        json={"name": "Club del Café", "terms": TERMS},
    ).json()
    client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 10},
    )
    client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")
    client.post("/api/v1/auth/logout")
    assert merchant.id is not None
    return merchant.id, program["slug"]


def test_alta_publica_requiere_verificar_correo(client: TestClient, db_session: Session) -> None:
    _, slug = _active_program(client, db_session)

    response = client.post(
        f"/api/v1/public/programs/cafeteria-a/{slug}/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert "membership_token" not in payload and "card_url" not in payload
    assert len(EMAIL_OUTBOX) == 1
    assert "Confirma" in EMAIL_OUTBOX[0]["subject"]
    token = email_token(subject="Confirma")
    verified = client.post("/api/v1/public/email/verify", json={"token": token})
    assert verified.status_code == 200, verified.text
    assert verified.json()["merchant_slug"] == "cafeteria-a"
    assert len(EMAIL_OUTBOX) == 2
    assert "Tu tarjeta" in EMAIL_OUTBOX[1]["subject"]
    cards = client.get("/api/v1/public/card-access/cafeteria-a")
    assert cards.status_code == 200
    assert len(cards.json()) == 1
    assert cards.json()[0]["token"]
    assert client.post("/api/v1/public/email/verify", json={"token": token}).status_code == 400


def test_recuperacion_por_correo_no_enumera_y_revoca_sesion(
    client: TestClient, db_session: Session
) -> None:
    _, slug = _active_program(client, db_session)
    body = {
        "email": "cliente@example.com",
        "display_name": "Cliente de Prueba",
        "privacy_notice_version": 1,
        "accepted_terms_version": 1,
    }
    enroll_verified(client, db_session, "cafeteria-a", slug, body)
    other_owner = create_user(db_session, "owner-other@example.com")
    other_merchant = create_merchant_with_owner(db_session, other_owner, name="Otro comercio")
    db_session.commit()

    unknown = client.post(
        "/api/v1/public/card-access/request?merchant_slug=cafeteria-a",
        json={"email": "desconocido@example.com"},
    )
    known = client.post(
        "/api/v1/public/card-access/request?merchant_slug=cafeteria-a",
        json={"email": "cliente@example.com"},
    )

    assert unknown.status_code == known.status_code == 202
    assert unknown.json() == known.json()
    assert len(EMAIL_OUTBOX) == 3
    token = email_token(subject="Acceso a tus tarjetas")
    exchanged = client.post("/api/v1/public/card-access", json={"token": token})
    assert exchanged.status_code == 200
    assert len(client.get("/api/v1/public/card-access/cafeteria-a").json()) == 1
    assert client.get(f"/api/v1/public/card-access/{other_merchant.slug}").status_code == 401
    assert client.get("/api/v1/public/card-access/no-existe").status_code == 404
    assert client.post("/api/v1/public/card-access", json={"token": token}).status_code == 400

    closed = client.post("/api/v1/public/card-access/cafeteria-a/logout")
    assert closed.status_code == 200
    assert client.get("/api/v1/public/card-access/cafeteria-a").status_code == 401


def test_enlace_de_verificacion_expirado_no_abre_tarjeta(
    client: TestClient, db_session: Session
) -> None:
    _, slug = _active_program(client, db_session)
    response = client.post(
        f"/api/v1/public/programs/cafeteria-a/{slug}/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    assert response.status_code == 201
    token = email_token(subject="Confirma")
    email_token_row = db_session.query(MemberEmailToken).one()
    email_token_row.expires_at = utcnow() - timedelta(seconds=1)
    db_session.commit()

    expired = client.post("/api/v1/public/email/verify", json={"token": token})

    assert expired.status_code == 400
    assert expired.json()["detail"]["code"] == "invalid_or_expired_link"
    assert client.get("/api/v1/public/card-access/cafeteria-a").status_code == 401


def test_alta_requiere_programa_activo(client: TestClient, db_session: Session) -> None:
    owner = create_user(db_session, OWNER_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    db_session.commit()
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant.id}/programs",
        json={"name": "Club", "terms": TERMS},
    ).json()
    client.post("/api/v1/auth/logout")

    response = client.post(
        f"/api/v1/public/programs/cafeteria-a/{program['slug']}/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "program_not_active"


def test_alta_exige_aceptar_las_condiciones_vigentes(
    client: TestClient, db_session: Session
) -> None:
    _, slug = _active_program(client, db_session)

    response = client.post(
        f"/api/v1/public/programs/cafeteria-a/{slug}/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 99,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "terms_version_mismatch"


def test_email_repetido_no_duplica_membresia(client: TestClient, db_session: Session) -> None:
    _, slug = _active_program(client, db_session)
    body = {
        "email": "cliente@example.com",
        "display_name": "Cliente de Prueba",
        "privacy_notice_version": 1,
        "accepted_terms_version": 1,
    }

    primera = client.post(f"/api/v1/public/programs/cafeteria-a/{slug}/enroll", json=body)
    segunda = client.post(f"/api/v1/public/programs/cafeteria-a/{slug}/enroll", json=body)

    assert primera.status_code == 201
    assert segunda.status_code == 201
    assert db_session.query(Membership).count() == 1


def test_tarjeta_web_muestra_saldo_y_recompensas(client: TestClient, db_session: Session) -> None:
    _, slug = _active_program(client, db_session)
    _, token = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    tarjeta = client.get(f"/api/v1/public/memberships/{token}")

    assert tarjeta.status_code == 200
    payload = tarjeta.json()
    assert payload["stamps"] == 0
    assert payload["rewards"][0]["earned"] is False
    # §17.2: nunca se presenta como pase emitido si el proveedor es simulado.
    assert payload["simulated_wallet"] is True


def test_tarjeta_desconocida_o_desactivada(client: TestClient, db_session: Session) -> None:
    from app.models.members import Membership

    _, slug = _active_program(client, db_session)
    _, token = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    desconocida = client.get("/api/v1/public/memberships/" + "0" * 64)
    membership = db_session.query(Membership).filter(Membership.public_token == token).one()
    membership.status = "disabled"
    db_session.commit()
    desactivada = client.get(f"/api/v1/public/memberships/{token}")

    assert desconocida.status_code == 404
    assert desactivada.status_code == 403
    assert desactivada.json()["detail"]["code"] == "membership_inactive"


def test_listado_de_miembros_solo_para_el_comercio(client: TestClient, db_session: Session) -> None:
    merchant_id, slug = _active_program(client, db_session)
    enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    login(client, OWNER_EMAIL)
    propietario = client.get(f"/api/v1/merchants/{merchant_id}/members")
    equipo = client.get(f"/api/v1/merchants/{merchant_id}/memberships")

    assert propietario.status_code == 200
    assert len(propietario.json()) == 1
    assert propietario.json()[0]["email"] == "cliente@example.com"
    assert equipo.status_code == 200 and len(equipo.json()) == 1
    # El token público no es una credencial de administración: el listado del
    # comercio es lo que da acceso a la gestión, no el token.
    assert equipo.json()[0]["public_token"]


def test_staff_no_ve_miembros(client: TestClient, db_session: Session) -> None:
    merchant_id, slug = _active_program(client, db_session)
    enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    login(client, STAFF_EMAIL)

    assert client.get(f"/api/v1/merchants/{merchant_id}/members").status_code == 404
    assert client.get(f"/api/v1/merchants/{merchant_id}/memberships").status_code == 404


def test_qr_publico_de_la_tarjeta(client: TestClient, db_session: Session) -> None:
    """§6.7: el cliente puede identificarse con un QR sin instalar una app."""
    _, slug = _active_program(client, db_session)
    _, token = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )

    qr = client.get(f"/api/v1/public/memberships/{token}/qr")

    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/svg+xml"
    # El QR codifica el token (identificador opaco), nunca datos personales.
    assert "cliente" not in qr.text


def test_qr_publico_de_tarjeta_desactivada(client: TestClient, db_session: Session) -> None:
    from app.models.members import Membership

    _, slug = _active_program(client, db_session)
    _, token = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        slug,
        {
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    membership = db_session.query(Membership).filter(Membership.public_token == token).one()
    membership.status = "disabled"
    db_session.commit()

    assert client.get(f"/api/v1/public/memberships/{token}/qr").status_code == 403


def test_alta_audita_solo_membresias_nuevas(client: TestClient, db_session: Session) -> None:
    """Regresión: reintentos del alta no duplican eventos y los nuevos sí se auditan.

    `member.enrolled` se registra exactamente cuando el servicio crea una
    membresía; repetir la solicitud (reenviar enlace) no genera un evento
    nuevo, y el alta en un segundo programa del mismo comercio sí.
    """
    from app.models.audit import AuditEvent

    merchant_id, slug = _active_program(client, db_session)
    login(client, OWNER_EMAIL)
    program_b = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Menú", "terms": TERMS},
    ).json()
    client.post(f"/api/v1/merchants/{merchant_id}/programs/{program_b['id']}/publish")
    client.post("/api/v1/auth/logout")

    body = {
        "email": "auditoria@example.com",
        "display_name": "Cliente Auditoría",
        "privacy_notice_version": 1,
        "accepted_terms_version": 1,
    }

    def enfoques() -> int:
        return db_session.query(AuditEvent).filter(AuditEvent.action == "member.enrolled").count()

    first = client.post(f"/api/v1/public/programs/cafeteria-a/{slug}/enroll", json=body)
    assert first.status_code == 201
    assert enfoques() == 1

    # Reintento del cliente (mismo enlace reenviado): sin evento duplicado.
    again = client.post(f"/api/v1/public/programs/cafeteria-a/{slug}/enroll", json=body)
    assert again.status_code == 201
    assert enfoques() == 1

    # Alta verificada en un segundo programa: membresía nueva → un evento más.
    _, _ = enroll_verified(
        client,
        db_session,
        "cafeteria-a",
        program_b["slug"],
        dict(body),
    )
    assert enfoques() == 2
