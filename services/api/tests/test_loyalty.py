"""Pruebas de programas de fidelización y recompensas (FASE 3)."""

import uuid

from app.domain.roles import MerchantRole
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_EMAIL,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    login,
)

TERMS = "1 sello por visita. Canje desde 10 sellos."


def _setup(db_session: Session) -> uuid.UUID:
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    assert merchant.id is not None
    return merchant.id


def test_crear_programa_en_borrador_con_slug(client: TestClient, db_session: Session) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club del Café", "description": "Sellos por visita"},
    )

    assert response.status_code == 201, response.text
    payload = response.json()
    assert payload["status"] == "draft"
    assert payload["slug"] == "club-del-cafe"
    assert payload["program_type"] == "stamps"
    assert payload["rewards"] == []


def test_staff_no_puede_crear_programas(client: TestClient, db_session: Session) -> None:
    merchant_id = _setup(db_session)
    login(client, STAFF_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/programs", json={"name": "Club del Café"}
    )

    assert response.status_code == 404  # sin gestión: mismo código que inexistente


def test_otro_comercio_no_ve_tus_programas(client: TestClient, db_session: Session) -> None:
    from app.models.merchant import Merchant

    merchant_id = _setup(db_session)
    otro_owner = create_user(db_session, "otro@example.com")
    otro = create_merchant_with_owner(db_session, otro_owner, name="Cafetería B")
    db_session.commit()
    login(client, "otro@example.com")

    listado = client.get(f"/api/v1/merchants/{otro.id}/programs")
    ajeno = client.get(f"/api/v1/merchants/{merchant_id}/programs")

    assert listado.status_code == 200 and listado.json() == []
    assert ajeno.status_code == 404
    assert db_session.get(Merchant, merchant_id) is not None


def test_publicar_exige_condiciones_visibles(client: TestClient, db_session: Session) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs", json={"name": "Club del Café"}
    ).json()

    respuesta = client.post(f"/api/v1/merchants/{merchant_id}/programs/{program['id']}/publish")

    assert respuesta.status_code == 422
    assert respuesta.json()["detail"]["code"] == "program_terms_required"


def test_publicar_pausar_y_archivar(client: TestClient, db_session: Session) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club del Café", "terms": TERMS},
    ).json()
    base = f"/api/v1/merchants/{merchant_id}/programs/{program['id']}"

    publicado = client.post(f"{base}/publish")
    assert publicado.status_code == 200
    assert publicado.json()["status"] == "active"
    assert publicado.json()["published_at"] is not None

    pausado = client.post(f"{base}/pause")
    assert pausado.json()["status"] == "paused"

    # Pausar dos veces no puede funcionar.
    assert client.post(f"{base}/pause").status_code == 409

    reactivado = client.post(f"{base}/publish")
    assert reactivado.json()["status"] == "active"

    archivado = client.post(f"{base}/archive")
    assert archivado.json()["status"] == "archived"
    assert client.post(f"{base}/archive").status_code == 409


def test_editar_condiciones_incrementa_terms_version(
    client: TestClient, db_session: Session
) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs", json={"name": "Club", "terms": TERMS}
    ).json()

    respuesta = client.patch(
        f"/api/v1/merchants/{merchant_id}/programs/{program['id']}",
        json={"terms": f"{TERMS} Nuevo texto."},
    )

    assert respuesta.status_code == 200
    assert respuesta.json()["terms_version"] == 2


def test_recompensas_crud_y_validacion(client: TestClient, db_session: Session) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(f"/api/v1/merchants/{merchant_id}/programs", json={"name": "Club"}).json()
    base = f"/api/v1/merchants/{merchant_id}/programs/{program['id']}"

    invalida = client.post(f"{base}/rewards", json={"name": "Café gratis", "stamps_required": 0})
    assert invalida.status_code == 422

    creada = client.post(
        f"{base}/rewards",
        json={
            "name": "Café gratis",
            "description": "Un café alcanzar 10 sellos",
            "stamps_required": 10,
        },
    )
    assert creada.status_code == 201, creada.text
    reward_id = creada.json()["id"]

    listada = client.get(f"{base}/rewards")
    assert [r["name"] for r in listada.json()] == ["Café gratis"]

    editada = client.patch(f"{base}/rewards/{reward_id}", json={"stamps_required": 8})
    assert editada.json()["stamps_required"] == 8

    # Una recompensa de otro programa no se puede tocar.
    otro_programa = client.post(f"/api/v1/merchants/{merchant_id}/programs", json={"name": "Otro"})
    ajena = client.patch(
        f"/api/v1/merchants/{otro_programa.json()['id']}/rewards/{reward_id}",
        json={"stamps_required": 1},
    )
    assert ajena.status_code == 404


def test_pagina_publica_muestra_condiciones_y_estado(
    client: TestClient, db_session: Session
) -> None:
    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club del Café", "terms": TERMS},
    ).json()
    client.post(
        f"/api/v1/merchants/{merchant_id}/programs/{program['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 10},
    )

    sin_publicar = client.get("/api/v1/public/programs/cafeteria-a/club-del-cafe")
    assert sin_publicar.status_code == 200
    assert sin_publicar.json()["enrollment_open"] is False
    # La página pública nunca expone IDs internos (§13.4).
    assert "id" not in sin_publicar.text

    client.post(f"/api/v1/merchants/{merchant_id}/programs/{program['id']}/publish")

    publicado = client.get("/api/v1/public/programs/cafeteria-a/club-del-cafe")
    assert publicado.json()["enrollment_open"] is True
    assert publicado.json()["merchant_name"] == "Cafetería A"
    assert publicado.json()["rewards"][0]["stamps_required"] == 10


def test_pagina_publica_desconocida_responde_404(client: TestClient) -> None:
    assert client.get("/api/v1/public/programs/no-existe/tampoco").status_code == 404


def test_las_acciones_quedan_audiadas(client: TestClient, db_session: Session) -> None:
    from app.models.audit import AuditEvent

    merchant_id = _setup(db_session)
    login(client, OWNER_EMAIL)
    program = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club", "terms": TERMS},
    ).json()
    client.post(f"/api/v1/merchants/{merchant_id}/programs/{program['id']}/publish")

    actions = {e.action for e in db_session.query(AuditEvent).all()}
    assert {"program.created", "program.published"} <= actions
