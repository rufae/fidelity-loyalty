"""Pruebas de etiquetas NFC/QR y del módulo de Google Reviews (FASE 9/10).

Incluye las pruebas de **cumplimiento de política** (§4.2): el módulo de
reseñas no puede incentivar, filtrar por satisfacción ni vincularse a
recompensas.
"""

import uuid

import pytest
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
from .test_ledger import _membership, _world

REVIEW_URL = "https://g.page/r/ejemplo/review"


def _merchant(client: TestClient, db_session: Session) -> uuid.UUID:
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Cafetería A")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    assert merchant.id is not None
    return merchant.id


def test_etiqueta_de_alta_abre_el_programa(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)  # programa ya publicado
    login(client, OWNER_EMAIL)
    program_id = client.get(f"/api/v1/merchants/{merchant_id}/programs").json()[0]["id"]

    creada = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "loyalty_signup", "label": "Mostrador", "program_id": program_id},
    )

    assert creada.status_code == 201, creada.text
    tag = creada.json()
    assert tag["tag_type"] == "loyalty_signup"
    assert tag["destination_url"] == "/p/cafeteria-a/club-del-cafe"
    # §5.2: la URL corta no contiene datos personales ni IDs internos.
    assert "cliente" not in tag["public_slug"]
    assert len(tag["public_slug"]) == 16

    redirect = client.get(f"/go/{tag['public_slug']}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "/p/cafeteria-a/club-del-cafe"


def test_etiqueta_nfc_compartida_lleva_a_recuperar_tarjetas(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    creada = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "member_card_access", "label": "Recuperar mi tarjeta"},
    )

    assert creada.status_code == 201, creada.text
    tag = creada.json()
    assert tag["destination_url"] == "/my-card/cafeteria-a"
    assert (
        client.get(f"/go/{tag['public_slug']}", follow_redirects=False).headers["location"]
        == "/my-card/cafeteria-a"
    )


def test_etiqueta_de_reseñas_requiere_destino_verificado(
    client: TestClient, db_session: Session
) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)

    sin_destino = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    )
    assert sin_destino.status_code == 422

    guardado = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    assert guardado.status_code == 200
    assert guardado.json()["verification_status"] == "unverified"

    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()
    # Sin verificar todavía no se redirige (§4.1: nada de afirmar «oficial»).
    sin_verificar = client.get(f"/go/{tag['public_slug']}", follow_redirects=False)
    assert sin_verificar.status_code == 404
    assert sin_verificar.json()["detail"]["code"] == "review_destination_not_verified"

    verificado = client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    assert verificado.json()["verification_status"] == "verified"

    redirect = client.get(f"/go/{tag['public_slug']}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == REVIEW_URL


def test_cambiar_el_enlace_pierde_la_verificacion(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")

    cambiado = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination",
        json={"review_url": "https://maps.app.goo.gl/otro"},
    )

    assert cambiado.json()["verification_status"] == "unverified"
    assert cambiado.json()["verified_at"] is None


def test_url_de_reseñas_no_oficial_se_rechaza(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)

    response = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination",
        json={"review_url": "javascript:alert(1)"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "invalid_review_url"


def test_no_hay_open_redirect(client: TestClient, db_session: Session) -> None:
    """§12.8: `/go/{slug}` no acepta destinos libres por parámetros."""
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()

    respuesta = client.get(
        f"/go/{tag['public_slug']}?url=https://atacante.ejemplo",
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    assert respuesta.headers["location"] == REVIEW_URL  # nunca el parámetro


def test_no_filtrado_por_satisfaccion(client: TestClient, db_session: Session) -> None:
    """§4.2: el mismo destino para todos, con cualquier parámetro o ninguno."""
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()
    base = f"/go/{tag['public_slug']}"

    sin_params = client.get(base, follow_redirects=False)
    insatisfecho = client.get(f"{base}?satisfaction=low&survey_answer=1", follow_redirects=False)

    assert sin_params.headers["location"] == insatisfecho.headers["location"] == REVIEW_URL


def test_no_se_puede_crear_una_etiqueta_con_incentivo(
    client: TestClient, db_session: Session
) -> None:
    """§4.2: el esquema **prohíbe** campos de recompensa en etiquetas de reseñas."""
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )

    respuesta = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "google_review", "reward_id": str(uuid.uuid4()), "incentive": "5% dto."},
    )

    assert respuesta.status_code == 422  # campos desconocidos: rechazados


def test_metrica_se_llama_clic_y_no_reseñas(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()

    client.get(f"/go/{tag['public_slug']}")
    client.get(f"/go/{tag['public_slug']}")

    stats = client.get(f"/api/v1/merchants/{merchant_id}/nfc/stats").json()
    assert stats["review_link_clicks"] == 2
    assert "reviews_received" not in stats  # §4.4, §12.9
    assert "rating" not in stats


def test_etiqueta_desactivada_no_redirige(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()

    client.patch(
        f"/api/v1/merchants/{merchant_id}/nfc-tags/{tag['id']}", json={"status": "disabled"}
    )
    respuesta = client.get(f"/go/{tag['public_slug']}", follow_redirects=False)

    # §14.3: página neutral, sin redirigir.
    assert respuesta.status_code == 410
    assert "desactivada" in respuesta.text


def test_staff_no_gestiona_etiquetas(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, STAFF_EMAIL)

    assert client.get(f"/api/v1/merchants/{merchant_id}/nfc-tags").status_code == 404
    assert (
        client.post(
            f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
        ).status_code
        == 404
    )


def test_no_gestionar_etiquetas_de_otro_comercio(client: TestClient, db_session: Session) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": REVIEW_URL}
    )
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()

    owner_b = create_user(db_session, "owner-b@example.com")
    merchant_b = create_merchant_with_owner(db_session, owner_b, name="Bar B")
    db_session.commit()
    client.post("/api/v1/auth/logout")
    login(client, "owner-b@example.com")

    lectura = client.get(f"/api/v1/merchants/{merchant_b.id}/nfc-tags")
    edicion = client.patch(
        f"/api/v1/merchants/{merchant_b.id}/nfc-tags/{tag['id']}", json={"status": "disabled"}
    )

    assert lectura.status_code == 200 and lectura.json() == []
    assert edicion.status_code == 404


def test_qr_de_etiqueta_es_svg_sin_pii(client: TestClient, db_session: Session) -> None:
    merchant_id, token, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    program_id = client.get(f"/api/v1/merchants/{merchant_id}/programs").json()[0]["id"]
    tag = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "loyalty_signup", "program_id": program_id},
    ).json()

    qr = client.get(f"/api/v1/merchants/{merchant_id}/nfc-tags/{tag['id']}/qr")

    assert qr.status_code == 200
    assert qr.headers["content-type"] == "image/svg+xml"
    membership = _membership(db_session, token)
    assert membership.public_token not in qr.text  # el QR de la etiqueta no es la tarjeta
    # El contenido del QR debe ser una URL ABSOLUTA: con `/go/{slug}` a secas el
    # móvil muestra el texto al escanearlo y no abre la etiqueta (regresión real).
    content = qr.headers["X-QR-Content"]
    assert content.startswith("http")
    assert content.endswith(f"/go/{tag['public_slug']}")
    # La URL que se escribe en la etiqueta NFC coincide con la del QR.
    assert tag["short_url"] == content


def test_qr_de_etiqueta_usa_la_base_publica_configurada(
    client: TestClient, db_session: Session
) -> None:
    from app.core.config import Settings, get_settings
    from app.main import app

    merchant_id, _token, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    program_id = client.get(f"/api/v1/merchants/{merchant_id}/programs").json()[0]["id"]
    app.dependency_overrides[get_settings] = lambda: Settings(
        public_base_url="https://fidelidad.test"
    )
    try:
        tag = client.post(
            f"/api/v1/merchants/{merchant_id}/nfc-tags",
            json={"tag_type": "loyalty_signup", "program_id": program_id},
        ).json()
        qr = client.get(f"/api/v1/merchants/{merchant_id}/nfc-tags/{tag['id']}/qr")
        assert qr.headers["X-QR-Content"] == f"https://fidelidad.test/go/{tag['public_slug']}"
        assert tag["short_url"] == f"https://fidelidad.test/go/{tag['public_slug']}"
    finally:
        app.dependency_overrides.pop(get_settings, None)


@pytest.mark.parametrize("url", ["http://insecure.example/review", "ftp://x.example/review"])
def test_solo_https_para_reseñas(client: TestClient, db_session: Session, url: str) -> None:
    merchant_id = _merchant(client, db_session)
    login(client, OWNER_EMAIL)
    response = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination", json={"review_url": url}
    )
    assert response.status_code == 422
