"""Etiquetas de mostrador (ADR-0008): atajo del personal por programa.

- La etiqueta abre las operaciones con el programa preseleccionado.
- **Nunca** suma sellos por sí sola: requiere sesión del comercio.
- Sus clics se cuentan como usos de mostrador, separados de altas y reseñas.
- Regresión: los clics de las etiquetas de **alta** también se registran
  (antes quedaban siempre a cero en las estadísticas).
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, login
from .test_ledger import _world


def _program_id(client: TestClient, merchant_id: uuid.UUID) -> str:
    login(client, OWNER_EMAIL)
    programs = client.get(f"/api/v1/merchants/{merchant_id}/programs").json()
    assert programs, "el comercio de prueba debe tener un programa"
    return str(programs[0]["id"])


def _create_tag(client: TestClient, merchant_id: uuid.UUID, program_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "counter", "label": "Caja: café", "program_id": program_id},
    )
    assert response.status_code == 201, response.text
    body: dict[str, object] = response.json()
    return body


def test_la_etiqueta_de_mostrador_apunta_a_operaciones_con_programa(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    program_id = _program_id(client, merchant_id)

    tag = _create_tag(client, merchant_id, program_id)

    assert tag["tag_type"] == "counter"
    assert tag["destination_url"] == f"/merchants/{merchant_id}/operations?program={program_id}"
    short = str(tag["short_url"])
    assert short.startswith("http") and short.endswith(f"/go/{tag['public_slug']}")


def test_la_etiqueta_de_mostrador_necesita_programa(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "counter", "label": "Sin programa"},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "program_required"


def test_el_slug_redirige_al_atajo_y_cuenta_uso_de_mostrador(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    program_id = _program_id(client, merchant_id)
    tag = _create_tag(client, merchant_id, program_id)

    response = client.get(f"/go/{tag['public_slug']}", follow_redirects=False)

    assert response.status_code == 302
    assert response.headers["location"] == (
        f"/merchants/{merchant_id}/operations?program={program_id}"
    )

    stats = client.get(f"/api/v1/merchants/{merchant_id}/nfc/stats").json()
    assert stats["counter_clicks"] == 1
    assert stats["total_clicks"] == 1
    # Un uso de mostrador no se confunde con un alta ni con una reseña.
    assert stats["loyalty_signup_clicks"] == 0
    assert stats["review_link_clicks"] == 0


def test_una_etiqueta_de_mostrador_desactivada_responde_410(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    program_id = _program_id(client, merchant_id)
    tag = _create_tag(client, merchant_id, program_id)
    client.patch(
        f"/api/v1/merchants/{merchant_id}/nfc-tags/{tag['id']}", json={"status": "disabled"}
    )

    response = client.get(f"/go/{tag['public_slug']}")

    assert response.status_code == 410


def test_regresion_los_clics_de_alta_ya_se_registran(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    program_id = _program_id(client, merchant_id)
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "loyalty_signup", "label": "Entrada", "program_id": program_id},
    )
    assert response.status_code == 201
    slug = response.json()["public_slug"]

    click = client.get(f"/go/{slug}", follow_redirects=False)

    assert click.status_code == 302
    stats = client.get(f"/api/v1/merchants/{merchant_id}/nfc/stats").json()
    assert stats["loyalty_signup_clicks"] == 1
    assert stats["counter_clicks"] == 0


def test_el_tipo_de_etiqueta_invalido_sigue_rechazandose(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    response = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={"tag_type": "otra_cosa", "label": "X"},
    )

    assert response.status_code == 422
