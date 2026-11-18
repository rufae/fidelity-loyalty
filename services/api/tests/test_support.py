"""Soporte B2B: conversaciones, permisos, idempotencia y avisos (Plan.md).

Cubre los criterios de aceptación del MVP: aislamiento multiempresa, roles,
teléfono cifrado, límites antiabuso, outbox con reintentos y canales de aviso
sin exponer datos personales del propietario.
"""

import uuid
from typing import Any

import pytest
from app.core.config import Settings, get_settings
from app.core.crypto import decrypt_text, encrypt_text
from app.domain.errors import DomainError
from app.domain.roles import MerchantRole, PlatformRole
from app.main import app
from app.models.support import SupportCallbackRequest, SupportNotification
from app.services.support_notifications import run_due_notifications
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import (
    EMAIL_OUTBOX,
    NOTIFY_OUTBOX,
    PLATFORM_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    login,
)

OWNER_A = "owner-soporte-a@example.com"
OWNER_B = "owner-soporte-b@example.com"
STAFF_A = "staff-soporte-a@example.com"
VIEWER_A = "viewer-soporte-a@example.com"

THREAD_BODY = {
    "subject": "La impresora del mostrador no imprime",
    "category": "technical",
    "body": "No puedo imprimir los tiques desde esta mañana.",
    "preferred_contact": "in_app",
}


def _settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "auth_session_secret": "secreto-largo-de-pruebas-1234567890",
        "support_email_enabled": True,
        "support_notification_email": "propietario@plataforma.example.com",
        "support_from_email": "soporte@localai.example.com",
        "support_ntfy_enabled": True,
        "support_ntfy_base_url": "http://ntfy.local",
        "support_ntfy_topic": "soporte",
        "support_telegram_enabled": True,
        "support_telegram_bot_token": "token-de-prueba",
        "support_telegram_chat_id": "12345",
        "support_thread_rate_limit_per_day": 100,
        "support_message_rate_limit_per_day": 100,
        "support_callback_rate_limit_per_day": 100,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.fixture()
def support_settings() -> Settings:
    return _settings()


@pytest.fixture()
def support_client(client: TestClient, support_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: support_settings
    return client


def _world(db_session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    owner_a = create_user(db_session, OWNER_A, display_name="Owner A")
    owner_b = create_user(db_session, OWNER_B, display_name="Owner B")
    staff_a = create_user(db_session, STAFF_A, display_name="Staff A")
    viewer_a = create_user(db_session, VIEWER_A, display_name="Viewer A")
    create_user(db_session, PLATFORM_EMAIL, platform_role=PlatformRole.OWNER)
    merchant_a = create_merchant_with_owner(db_session, owner_a, name="Cafetería Norte")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar Sur")
    add_member(db_session, staff_a, merchant_a, MerchantRole.STAFF)
    add_member(db_session, viewer_a, merchant_a, MerchantRole.VIEWER)
    db_session.commit()
    return merchant_a.id, merchant_b.id


def _create_thread(
    client: TestClient,
    merchant_id: uuid.UUID,
    body: dict[str, Any] | None = None,
    key: str | None = None,
) -> dict[str, Any]:
    headers = {"Idempotency-Key": key} if key else {}
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/support",
        json=body or THREAD_BODY,
        headers=headers,
    )
    assert response.status_code == 201, response.text
    payload: dict[str, Any] = response.json()
    return payload


def test_owner_crea_conversacion_y_encola_los_tres_avisos(
    support_client: TestClient, db_session: Session, support_settings: Settings
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)

    payload = _create_thread(support_client, merchant_a)
    run_due_notifications(db_session, support_settings)
    db_session.commit()

    assert payload["status"] == "waiting_platform"
    assert payload["subject"] == THREAD_BODY["subject"]
    assert len(payload["messages"]) == 1
    assert payload["messages"][0]["author_type"] == "merchant"
    # Los tres canales están habilitados en esta prueba y todos quedan en outbox.
    queued = db_session.scalars(select(SupportNotification)).all()
    channels = {row.channel for row in queued}
    assert channels == {"email_platform", "ntfy", "telegram"}
    assert all(row.status == "succeeded" for row in queued)
    assert any(mail["recipient"] == "propietario@plataforma.example.com" for mail in EMAIL_OUTBOX)
    assert {row["channel"] for row in NOTIFY_OUTBOX} == {"ntfy", "telegram"}
    # El aviso nunca debe contener datos personales del propietario.
    assert all("propietario@" not in row.get("message", "") for row in NOTIFY_OUTBOX)


def test_idempotencia_de_conversacion_mensaje_y_llamada(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)

    first = _create_thread(support_client, merchant_a, key="thread-1")
    second = _create_thread(support_client, merchant_a, key="thread-1")
    assert first["id"] == second["id"]
    assert len(second["messages"]) == 1

    message_url = f"/api/v1/merchants/{merchant_a}/support/{first['id']}/messages"
    one = support_client.post(
        message_url, json={"body": "Adjunto más detalle."}, headers={"Idempotency-Key": "msg-1"}
    )
    two = support_client.post(
        message_url, json={"body": "Adjunto más detalle."}, headers={"Idempotency-Key": "msg-1"}
    )
    assert one.status_code == two.status_code == 201
    assert one.json()["id"] == two.json()["id"]

    callback_url = f"/api/v1/merchants/{merchant_a}/support/{first['id']}/callback-requests"
    callback_body = {"phone": "+34600111222", "availability": "Por la tarde", "consent": True}
    cb_one = support_client.post(
        callback_url, json=callback_body, headers={"Idempotency-Key": "call-1"}
    )
    cb_two = support_client.post(
        callback_url, json=callback_body, headers={"Idempotency-Key": "call-1"}
    )
    assert cb_one.status_code == cb_two.status_code == 201
    assert cb_one.json()["id"] == cb_two.json()["id"]


def test_limite_de_conversaciones_nuevas(client: TestClient, db_session: Session) -> None:
    settings = _settings(support_thread_rate_limit_per_day=1)
    app.dependency_overrides[get_settings] = lambda: settings
    merchant_a, _ = _world(db_session)
    login(client, OWNER_A)

    assert (
        client.post(f"/api/v1/merchants/{merchant_a}/support", json=THREAD_BODY).status_code == 201
    )
    limited = client.post(f"/api/v1/merchants/{merchant_a}/support", json=THREAD_BODY)

    assert limited.status_code == 429
    assert limited.json()["detail"]["code"] == "support_rate_limited"


def test_staff_solo_ve_sus_propias_conversaciones(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    owner_thread = _create_thread(support_client, merchant_a)

    login(support_client, STAFF_A)
    staff_thread = _create_thread(
        support_client, merchant_a, {**THREAD_BODY, "subject": "Problema de caja"}
    )

    listing = support_client.get(f"/api/v1/merchants/{merchant_a}/support").json()
    assert [row["id"] for row in listing["items"]] == [staff_thread["id"]]
    assert (
        support_client.get(
            f"/api/v1/merchants/{merchant_a}/support/{owner_thread['id']}"
        ).status_code
        == 404
    )


def test_viewer_no_puede_abrir_soporte(support_client: TestClient, db_session: Session) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, VIEWER_A)

    assert support_client.get(f"/api/v1/merchants/{merchant_a}/support").status_code == 404
    assert (
        support_client.post(f"/api/v1/merchants/{merchant_a}/support", json=THREAD_BODY).status_code
        == 404
    )


def test_un_comercio_no_ve_las_conversaciones_de_otro(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, merchant_b = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)

    login(support_client, OWNER_B)
    assert (
        support_client.get(f"/api/v1/merchants/{merchant_a}/support/{thread['id']}").status_code
        == 404
    )
    listing = support_client.get(f"/api/v1/merchants/{merchant_b}/support").json()
    assert listing["items"] == []


def test_plataforma_ve_todos_y_su_respuesta_avisa_al_comercio(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, merchant_b = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)
    login(support_client, OWNER_B)
    _create_thread(support_client, merchant_b, {**THREAD_BODY, "subject": "Otra consulta"})

    login(support_client, PLATFORM_EMAIL)
    listing = support_client.get("/api/v1/platform/support/threads").json()
    assert listing["total"] == 2

    reply = support_client.post(
        f"/api/v1/platform/support/threads/{thread['id']}/messages",
        json={"body": "Lo revisamos hoy mismo."},
    )
    assert reply.status_code == 201
    assert reply.json()["author_type"] == "platform"

    detail = support_client.get(f"/api/v1/platform/support/threads/{thread['id']}").json()
    assert detail["merchant_name"] == "Cafetería Norte"
    assert detail["status"] == "waiting_merchant"
    email_to_merchant = db_session.scalar(
        select(SupportNotification).where(SupportNotification.channel == "email_merchant")
    )
    assert email_to_merchant is not None


def test_telefono_de_llamada_cifrado_y_solo_para_plataforma(
    support_client: TestClient, db_session: Session, support_settings: Settings
) -> None:
    merchant_a, _ = _world(db_session)
    phone = "+34600111222"
    login(support_client, OWNER_A)
    payload = _create_thread(
        support_client,
        merchant_a,
        {
            **THREAD_BODY,
            "preferred_contact": "phone",
            "callback_phone": phone,
            "callback_availability": "De 16:00 a 18:00",
            "callback_consent": True,
        },
    )
    run_due_notifications(db_session, support_settings)
    db_session.commit()

    # El comercio ve que pidió llamada, pero no el número.
    assert payload["callback_request"] is not None
    assert payload["callback_request"]["phone"] is None
    assert payload["callback_request"]["status"] == "requested"

    # En base de datos solo queda cifrado.
    request = db_session.scalar(select(SupportCallbackRequest))
    assert request is not None
    assert request.phone_encrypted != phone
    assert decrypt_text(support_settings, request.phone_encrypted) == phone

    # El propietario sí lo ve en su buzón.
    login(support_client, PLATFORM_EMAIL)
    detail = support_client.get(f"/api/v1/platform/support/threads/{payload['id']}").json()
    assert detail["callback_request"]["phone"] == phone

    # Ni el correo ni el push contienen el teléfono.
    assert all(phone not in mail.get("text", "") for mail in EMAIL_OUTBOX)
    assert all(
        phone not in row.get("text", "") and phone not in row.get("message", "")
        for row in NOTIFY_OUTBOX
    )


def test_solicitud_de_llamada_exige_consentimiento(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)

    response = support_client.post(
        f"/api/v1/merchants/{merchant_a}/support",
        json={**THREAD_BODY, "callback_phone": "+34600111222", "callback_consent": False},
    )

    assert response.status_code == 422


def test_cerrar_conversacion_bloquea_nuevos_mensajes(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)

    closed = support_client.post(
        f"/api/v1/merchants/{merchant_a}/support/{thread['id']}/close", json={}
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    blocked = support_client.post(
        f"/api/v1/merchants/{merchant_a}/support/{thread['id']}/messages",
        json={"body": "Una pregunta más"},
    )
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "support_thread_closed"


def test_marcar_leido_actualiza_no_leidos(support_client: TestClient, db_session: Session) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)

    login(support_client, PLATFORM_EMAIL)
    support_client.post(
        f"/api/v1/platform/support/threads/{thread['id']}/messages",
        json={"body": "¿Puedes darme más detalle?"},
    )
    assert support_client.get("/api/v1/platform/support/unread-count").json()["count"] == 0

    login(support_client, OWNER_A)
    assert (
        support_client.get(f"/api/v1/merchants/{merchant_a}/support/unread-count").json()["count"]
        == 1
    )
    marked = support_client.post(
        f"/api/v1/merchants/{merchant_a}/support/{thread['id']}/read", json={}
    )
    assert marked.status_code == 200
    assert marked.json()["count"] == 0


def test_fallo_de_aviso_no_pierde_la_conversacion_y_se_reintenta(
    support_client: TestClient,
    db_session: Session,
    support_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import email as email_service

    def _boom(*args: object, **kwargs: object) -> None:
        raise RuntimeError("SMTP caído")

    monkeypatch.setattr(email_service, "send_support_email", _boom)
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    payload = _create_thread(support_client, merchant_a)

    processed = run_due_notifications(db_session, support_settings)
    db_session.commit()
    assert processed >= 1

    # La conversación sigue viva aunque el correo falle.
    detail = support_client.get(f"/api/v1/merchants/{merchant_a}/support/{payload['id']}").json()
    assert len(detail["messages"]) == 1

    notification = db_session.scalar(
        select(SupportNotification).where(SupportNotification.channel == "email_platform")
    )
    assert notification is not None
    assert notification.status in {"retrying", "failed"}
    assert notification.error_code == "notification_delivery_failed"

    # Al arreglar el canal, el reintento manual lo envía.
    monkeypatch.setattr(email_service, "send_support_email", lambda *a, **k: None)
    login(support_client, PLATFORM_EMAIL)
    retried = support_client.post(
        f"/api/v1/platform/support/notifications/{notification.id}/retry", json={}
    )
    assert retried.status_code == 200
    assert retried.json()["status"] == "succeeded"


def test_respuesta_plataforma_encola_aviso_push_con_tema_propio(
    support_client: TestClient, db_session: Session
) -> None:
    """Plan.md §11.3: el push al comercio usa SU tema, aleatorio y único."""
    from app.models.merchant import Merchant

    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)

    login(support_client, PLATFORM_EMAIL)
    reply = support_client.post(
        f"/api/v1/platform/support/threads/{thread['id']}/messages",
        json={"body": "Respuesta con aviso push."},
    )
    assert reply.status_code == 201

    notification = db_session.scalar(
        select(SupportNotification).where(SupportNotification.channel == "ntfy_merchant")
    )
    assert notification is not None
    # El tema se genera en la misma transacción que el evento (§6.3).
    merchant = db_session.get(Merchant, merchant_a)
    assert merchant is not None
    assert merchant.support_ntfy_topic is not None
    assert merchant.support_ntfy_topic.startswith("s-")


def test_aviso_push_del_comercio_se_entrega_con_su_tema(
    support_client: TestClient, db_session: Session, support_settings: Settings
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    thread = _create_thread(support_client, merchant_a)

    login(support_client, PLATFORM_EMAIL)
    support_client.post(
        f"/api/v1/platform/support/threads/{thread['id']}/messages",
        json={"body": "Entrega del push."},
    )
    NOTIFY_OUTBOX.clear()
    processed = run_due_notifications(db_session, support_settings)
    assert processed >= 1

    entregas = [row for row in NOTIFY_OUTBOX if row["channel"] == "ntfy_merchant"]
    assert len(entregas) == 1
    from app.models.merchant import Merchant

    merchant = db_session.get(Merchant, merchant_a)
    assert merchant is not None and merchant.support_ntfy_topic is not None
    assert entregas[0]["topic"] == merchant.support_ntfy_topic
    assert "conversación" in entregas[0]["title"].lower() or "Soporte" in entregas[0]["title"]


def test_tema_de_avisos_solo_para_administracion_y_estable(
    support_client: TestClient, db_session: Session
) -> None:
    """Solo owner/admin consulta el tema; staff queda fuera (§8.1)."""
    merchant_a, merchant_b = _world(db_session)

    login(support_client, STAFF_A)
    staff = support_client.get(f"/api/v1/merchants/{merchant_a}/support/notification-topic")
    assert staff.status_code == 404

    login(support_client, OWNER_A)
    first = support_client.get(f"/api/v1/merchants/{merchant_a}/support/notification-topic")
    assert first.status_code == 200
    topic = first.json()["topic"]
    assert topic.startswith("s-")
    # Sin URL pública configurada: la interfaz lo dice, no se inventa (§17.2).
    assert first.json()["server_url"] is None
    # Estable: segunda consulta devuelve el mismo tema.
    second = support_client.get(f"/api/v1/merchants/{merchant_a}/support/notification-topic")
    assert second.json()["topic"] == topic

    # Comercios distintos: temas distintos (el tema es la credencial).
    login(support_client, OWNER_B)
    other = support_client.get(f"/api/v1/merchants/{merchant_b}/support/notification-topic")
    assert other.status_code == 200
    assert other.json()["topic"] != topic


def test_un_fallo_permanente_no_reintenta_infinitamente(
    support_client: TestClient,
    db_session: Session,
    support_settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.services import email as email_service

    def _not_configured(*args: object, **kwargs: object) -> None:
        raise DomainError(503, "notification_not_configured", "Canal sin configurar")

    monkeypatch.setattr(email_service, "send_support_email", _not_configured)
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    _create_thread(support_client, merchant_a)

    run_due_notifications(db_session, support_settings)

    notification = db_session.scalar(
        select(SupportNotification).where(SupportNotification.channel == "email_platform")
    )
    assert notification is not None
    assert notification.status == "failed"
    assert notification.next_attempt_at is None


def test_configuracion_de_canales_incompleta_no_arranca() -> None:
    with pytest.raises(ValueError, match="SUPPORT_NTFY_ENABLED"):
        Settings(support_ntfy_enabled=True)
    with pytest.raises(ValueError, match="SUPPORT_TELEGRAM_ENABLED"):
        Settings(support_telegram_enabled=True)


def test_cifrado_de_telefono_con_tamper() -> None:
    settings = _settings()
    encrypted = encrypt_text(settings, "+34600111222")
    assert encrypted != "+34600111222"
    assert decrypt_text(settings, encrypted) == "+34600111222"
    with pytest.raises(DomainError):
        decrypt_text(settings, encrypted[:-4] + "AAAA")


def test_filtros_y_paginacion_del_buzon_de_plataforma(
    support_client: TestClient, db_session: Session
) -> None:
    merchant_a, _ = _world(db_session)
    login(support_client, OWNER_A)
    _create_thread(support_client, merchant_a, {**THREAD_BODY, "subject": "Consulta de puntos"})
    _create_thread(support_client, merchant_a, {**THREAD_BODY, "subject": "Fallo de NFC"})

    login(support_client, PLATFORM_EMAIL)
    filtered = support_client.get("/api/v1/platform/support/threads?q=NFC&limit=1&offset=0").json()
    assert filtered["total"] == 1
    assert filtered["items"][0]["subject"] == "Fallo de NFC"
    assert filtered["limit"] == 1
