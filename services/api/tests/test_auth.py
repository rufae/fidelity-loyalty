"""Pruebas de autenticación: login, cookie, rate limiting y invalidación (FASE 2)."""

import pytest
from app.core.config import Settings
from app.core.security import SESSION_COOKIE_NAME, hash_password, verify_password
from app.domain.errors import DomainError
from app.models.audit import AuditEvent
from app.models.user import UserSession
from app.services.auth import change_password
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, PASSWORD, PLATFORM_EMAIL, create_user, login


def test_login_ok_fija_cookie_httponly_y_devuelve_usuario(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session, OWNER_EMAIL)
    db_session.commit()

    response = client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["user"]["email"] == OWNER_EMAIL
    assert payload["merchants"] == []

    cookie = response.cookies.get(SESSION_COOKIE_NAME)
    assert cookie
    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    # Desarrollo (no HTTPS): no se exige `Secure` todavía; en producción sí (§16.7).
    assert "Secure" not in set_cookie


def test_login_con_password_incorrecto_responde_401_sin_cookie(
    client: TestClient, db_session: Session
) -> None:
    create_user(db_session, OWNER_EMAIL)
    db_session.commit()

    response = client.post(
        "/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": "otra-password"}
    )

    assert response.status_code == 401
    assert response.json()["detail"]["code"] == "invalid_credentials"
    assert SESSION_COOKIE_NAME not in response.cookies


def test_login_email_inexistente_respuesta_identica_a_password_mala(
    client: TestClient,
) -> None:
    """No se puede averiguar qué emails existen probando contraseñas (§8.2)."""
    existente = client.post(
        "/api/v1/auth/login", json={"email": "no-existe@example.com", "password": "mala"}
    )
    response = client.post(
        "/api/v1/auth/login", json={"email": "tampoco@example.com", "password": "mala"}
    )
    assert existente.status_code == response.status_code == 401
    assert existente.json() == response.json()


def test_rate_limit_tras_5_fallos_responde_429(client: TestClient, db_session: Session) -> None:
    create_user(db_session, OWNER_EMAIL)
    db_session.commit()

    for _ in range(5):
        client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": "mala"})
    blocked = client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})

    assert blocked.status_code == 429
    assert blocked.json()["detail"]["code"] == "login_rate_limited"
    assert int(blocked.headers["Retry-After"]) >= 1


def test_logout_revoca_la_sesion_en_servidor(client: TestClient, db_session: Session) -> None:
    create_user(db_session, OWNER_EMAIL)
    db_session.commit()
    login(client, OWNER_EMAIL)
    assert client.get("/api/v1/auth/me").status_code == 200

    client.post("/api/v1/auth/logout")

    assert client.get("/api/v1/auth/me").status_code == 401


def test_sesion_invalidada_directamente_en_bd_deja_de_funcionar(
    client: TestClient, db_session: Session
) -> None:
    """Las sesiones son invalidables desde el servidor (§8.3)."""
    user = create_user(db_session, OWNER_EMAIL)
    db_session.commit()
    login(client, OWNER_EMAIL)

    for row in db_session.scalars(select(UserSession).where(UserSession.user_id == user.id)):
        row.revoked_at = row.expires_at
    db_session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401


def test_cambiar_password_revoca_las_sesiones(client: TestClient, db_session: Session) -> None:
    user = create_user(db_session, OWNER_EMAIL)
    db_session.commit()
    login(client, OWNER_EMAIL)

    change_password(db_session, user, "password-nuevo-largo-123")
    db_session.commit()

    assert client.get("/api/v1/auth/me").status_code == 401
    assert verify_password(user.password_hash, "password-nuevo-largo-123")


def test_me_sin_sesion_responde_401(client: TestClient) -> None:
    assert client.get("/api/v1/auth/me").status_code == 401


def test_mutaciones_exigen_json_content_type(client: TestClient) -> None:
    """Defensa anti-CSRF en profundidad: sin cookie el resultado ya sería 401."""
    response = client.post(
        "/api/v1/platform/merchants",
        content="nombre=X",
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 415
    assert response.json()["error"]["code"] == "unsupported_media_type"


def test_login_registra_auditoria_de_exito_y_fallo(client: TestClient, db_session: Session) -> None:
    create_user(db_session, OWNER_EMAIL)
    db_session.commit()
    client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": "mala"})
    client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})

    actions = [event.action for event in db_session.scalars(select(AuditEvent)).all()]
    assert "auth.login.failed" in actions
    assert "auth.login.success" in actions
    # El email del intento fallido se audita como hash, nunca en claro (§16.6).
    failed = db_session.scalars(
        select(AuditEvent).where(AuditEvent.action == "auth.login.failed")
    ).one()
    assert "email" not in failed.metadata_json
    assert "email_hash" in failed.metadata_json


def test_produccion_sin_secreto_no_arranca() -> None:
    """Fail-closed: producción sin AUTH_SESSION_SECRET no puede arrancar (§16.2)."""
    with pytest.raises(ValueError, match="AUTH_SESSION_SECRET"):
        Settings.model_validate(
            {
                "app_env": "production",
                "auth_bootstrap_email": "admin@example.com",
                "auth_bootstrap_password": "contrasena-larga-123",
            }
        )


def test_bootstrap_password_corta_se_rechaza() -> None:
    with pytest.raises(ValueError, match="12 caracteres"):
        Settings.model_validate(
            {"auth_bootstrap_email": "admin@example.com", "auth_bootstrap_password": "corta"}
        )


def test_hash_distinto_por_usuario_mismo_password() -> None:
    """Argon2id aplica sal propia: dos hashes iguales delatarían ausencia de sal."""
    assert hash_password(PASSWORD) != hash_password(PASSWORD)


def test_plataforma_no_devuelve_hashes(client: TestClient, db_session: Session) -> None:
    create_user(db_session, PLATFORM_EMAIL)
    db_session.commit()
    login(client, PLATFORM_EMAIL)

    response = client.get("/api/v1/auth/me")

    body = response.text
    assert "password_hash" not in body
    assert "argon2" not in body


def test_error_de_dominio_lleva_code_legible() -> None:
    error = DomainError(404, "not_found", "Comercio no encontrado")
    assert error.status_code == 404
    assert error.detail["code"] == "not_found"  # type: ignore[index]
