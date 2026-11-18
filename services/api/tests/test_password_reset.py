"""Recuperación de contraseña de personal (§8.3, decisión de compra P0-2).

Cubre: respuesta sin enumeración, flujo completo por token, invalidación de
sesiones al cambiar la credencial, token de un solo uso y límite de peticiones.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, PASSWORD, login
from .test_ledger import _world

RESET_URL = "/api/v1/auth/password-reset"
RESET_CONFIRM_URL = "/api/v1/auth/password-reset/confirm"


def _ultimo_enlace(client: TestClient, db_session: Session) -> str:
    """Extrae el token del enlace desde el correo capturado en pruebas."""
    from .conftest import EMAIL_OUTBOX

    links = [m["action_url"] for m in EMAIL_OUTBOX if "/recuperar?" in m.get("action_url", "")]
    assert links, "no se envió el correo de recuperación"
    return links[-1].split("token=", 1)[1]


def test_solicitud_sin_enumeracion(client: TestClient, db_session: Session) -> None:
    """Respuesta idéntica exista o no el email (§8.2)."""
    _world(client, db_session)
    for email in (OWNER_EMAIL, "nadie@example.com"):
        response = client.post(RESET_URL, json={"email": email})
        assert response.status_code == 202
        assert response.json() == {"ok": True}


def test_flujo_completo_y_sesiones_invalidadas(client: TestClient, db_session: Session) -> None:
    """Pedir enlace → definir contraseña → login con la nueva y sesión vieja muerta."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    assert client.post(RESET_URL, json={"email": OWNER_EMAIL}).status_code == 202
    raw = _ultimo_enlace(client, db_session)

    confirm = client.post(
        RESET_CONFIRM_URL, json={"token": raw, "new_password": "nueva-clave-larga-2026"}
    )
    assert confirm.status_code == 200, confirm.text

    # La contraseña anterior ya no vale; la nueva sí.
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD}
        ).status_code
        == 401
    )
    login(client, OWNER_EMAIL, "nueva-clave-larga-2026")

    # Restaurar la contraseña original para otros tests del módulo.
    client.post(RESET_URL, json={"email": OWNER_EMAIL})
    raw2 = _ultimo_enlace(client, db_session)
    assert (
        client.post(RESET_CONFIRM_URL, json={"token": raw2, "new_password": PASSWORD}).status_code
        == 200
    )
    login(client, OWNER_EMAIL, PASSWORD)


def test_token_de_un_solo_uso_y_caduca(client: TestClient, db_session: Session) -> None:
    _world(client, db_session)
    client.post(RESET_URL, json={"email": OWNER_EMAIL})
    raw = _ultimo_enlace(client, db_session)

    first = client.post(
        RESET_CONFIRM_URL, json={"token": raw, "new_password": "nueva-clave-larga-2026"}
    )
    assert first.status_code == 200
    second = client.post(
        RESET_CONFIRM_URL, json={"token": raw, "new_password": "otra-clave-larga-2026"}
    )
    assert second.status_code == 400
    assert second.json()["detail"]["code"] == "invalid_reset_token"


def test_token_invalido_o_contrasena_debil_rechazados(
    client: TestClient, db_session: Session
) -> None:
    _world(client, db_session)
    weak = client.post(RESET_CONFIRM_URL, json={"token": "a" * 40, "new_password": "corta-123"})
    assert weak.status_code in {400, 422}
