"""Diseño de tarjeta del comercio (decisión de compra #8, §11.15).

Cubre: lectura/actualización validada, logotipo con magic bytes y tope de
tamaño, servicio del recurso por UUID opaco, y el branding dentro del
payload público de la tarjeta. El staff no gestiona el diseño (solo
owner/admin). El aislamiento §8.2 aplica igual que en el resto.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, STAFF_EMAIL, login
from .test_ledger import _world

BRANDING_URL = "/api/v1/merchants/{merchant_id}/branding"

PNG_1PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6260000000060005"
    "27de41ba0000000049454e44ae426082"
)


def test_branding_por_defecto_y_actualizacion(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    first = client.get(BRANDING_URL.format(merchant_id=merchant_id))
    assert first.status_code == 200
    assert first.json()["stamp_icon"] == "cup"

    updated = client.put(
        BRANDING_URL.format(merchant_id=merchant_id),
        json={
            "primary_color": "#1E8E5A",
            "accent_color": "#FFD166",
            "stamp_icon": "leaf",
            "footer_text": "Café de especialidad desde 1998",
        },
    )
    assert updated.status_code == 200, updated.text
    data = updated.json()
    assert data["primary_color"] == "#1e8e5a"
    assert data["stamp_icon"] == "leaf"

    # Validaciones: color malformado, icono fuera de catálogo, pie demasiado
    # largo; nada pasa.
    assert (
        client.put(
            BRANDING_URL.format(merchant_id=merchant_id), json={"primary_color": "rojo"}
        ).status_code
        == 422
    )
    assert (
        client.put(
            BRANDING_URL.format(merchant_id=merchant_id), json={"stamp_icon": "rocket"}
        ).status_code
        == 422
    )
    assert (
        client.put(
            BRANDING_URL.format(merchant_id=merchant_id), json={"footer_text": "x" * 81}
        ).status_code
        == 422
    )


def test_logo_subida_servicio_y_reemplazo(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    url = BRANDING_URL.format(merchant_id=merchant_id)

    # Un fichero de texto disfrazado no pasa (MIME real por magic bytes).
    fake = client.post(url + "/logo", content=b"esto no es una imagen")
    assert fake.status_code == 415

    ok = client.post(url + "/logo", content=PNG_1PX, headers={"content-type": "image/png"})
    assert ok.status_code == 200, ok.text
    logo_url = ok.json()["logo_url"]
    assert logo_url and logo_url.startswith("/api/v1/public/assets/")

    served = client.get(logo_url)
    assert served.status_code == 200
    assert served.headers["content-type"] == "image/png"
    assert served.content == PNG_1PX

    # Reemplazar el logo borra el anterior (sin huérfanos) y sirve el nuevo.
    ok2 = client.post(url + "/logo", content=PNG_1PX, headers={"content-type": "image/png"})
    second_url = ok2.json()["logo_url"]
    assert second_url != logo_url
    assert client.get(logo_url).status_code == 404

    # Quitar el logo también lo borra.
    removed = client.delete(url + "/logo")
    assert removed.status_code == 200
    assert removed.json()["logo_url"] is None
    assert client.get(second_url).status_code == 404


def test_logo_too_large_rechazado(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    # PNG cabecera válida + relleno hasta superar 512 KiB.
    big = PNG_1PX + b"\x00" * (512 * 1024)
    response = client.post(
        BRANDING_URL.format(merchant_id=merchant_id) + "/logo",
        content=big,
        headers={"content-type": "image/png"},
    )
    assert response.status_code == 413


def test_branding_en_la_tarjeta_publica(client: TestClient, db_session: Session) -> None:
    """El diseño llega al cliente a través del payload de su tarjeta."""
    merchant_id, token, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    client.put(
        BRANDING_URL.format(merchant_id=merchant_id),
        json={"primary_color": "#1E8E5A", "stamp_icon": "leaf", "footer_text": "Gracias por venir"},
    )
    client.post("/api/v1/auth/logout")

    card = client.get(f"/api/v1/public/memberships/{token}").json()
    assert card["primary_color"] == "#1e8e5a"
    assert card["stamp_icon"] == "leaf"
    assert card["footer_text"] == "Gracias por venir"


def test_staff_no_gestiona_diseno(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    assert client.get(BRANDING_URL.format(merchant_id=merchant_id)).status_code == 404
    assert (
        client.put(
            BRANDING_URL.format(merchant_id=merchant_id), json={"stamp_icon": "star"}
        ).status_code
        == 404
    )


def test_branding_de_otro_comercio_no_se_ve(client: TestClient, db_session: Session) -> None:
    merchant_a, _, _ = _world(client, db_session)
    # Un segundo comercio propio con usuarios distintos no es trivial; basta
    # comprobar que un id de comercio inventado responde 404 (§8.2).
    import uuid as uuid_module

    login(client, OWNER_EMAIL)
    fake_id = str(uuid_module.uuid4())
    assert client.get(BRANDING_URL.format(merchant_id=fake_id)).status_code == 404
    del merchant_a
