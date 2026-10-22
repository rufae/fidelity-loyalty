"""Validación de configuración de producción (§14.3, §17.4).

Producción no arranca con una base pública inutilizable por móviles ni con un
proveedor Wallet «activado» a medias. Se informa de las **variables faltantes**
por su nombre, nunca de sus valores.
"""

from typing import Literal, TypedDict

import pytest
from app.core.config import Settings


def test_produccion_exige_public_base_url() -> None:
    with pytest.raises(ValueError, match="PUBLIC_BASE_URL"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
        )


def test_produccion_rechaza_localhost_y_red_privada() -> None:
    with pytest.raises(ValueError, match="host privado"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
            public_base_url="https://localhost:8100",
        )
    with pytest.raises(ValueError, match="host privado"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
            public_base_url="https://10.0.0.1",
        )
    with pytest.raises(ValueError, match="host privado"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
            public_base_url="https://fidelidad.local",
        )


def test_produccion_rechaza_http() -> None:
    with pytest.raises(ValueError, match="https"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
            public_base_url="http://fidelidad.example.com",
        )


def test_servicio_solo_privado_es_decision_explicita() -> None:
    settings = Settings(
        app_env="production",
        auth_session_secret="x" * 32,
        auth_bootstrap_email="admin@example.com",
        auth_bootstrap_password="contrasena-larga-1234",
        public_base_url="https://fidelidad.local",
        allow_private_public_base_url=True,
        email_from="tarjetas@example.com",
        email_smtp_host="smtp.example.com",
        database_url="postgresql+psycopg://fidelity:clave-propia@db:5432/fidelity",
    )
    assert settings.allow_private_public_base_url is True


def test_produccion_con_dominio_publico_valido() -> None:
    settings = Settings(
        app_env="production",
        auth_session_secret="x" * 32,
        auth_bootstrap_email="admin@example.com",
        auth_bootstrap_password="contrasena-larga-1234",
        public_base_url="https://fidelidad.example.com",
        email_from="tarjetas@example.com",
        email_smtp_host="smtp.example.com",
        database_url="postgresql+psycopg://fidelity:clave-propia@db:5432/fidelity",
    )
    assert settings.public_base_url == "https://fidelidad.example.com"


class _ProdSettings(TypedDict):
    app_env: Literal["production"]
    auth_session_secret: str
    auth_bootstrap_email: str
    auth_bootstrap_password: str
    public_base_url: str
    email_from: str
    email_smtp_host: str
    database_url: str


PROD: _ProdSettings = {
    "app_env": "production",
    "auth_session_secret": "x" * 32,
    "auth_bootstrap_email": "admin@example.com",
    "auth_bootstrap_password": "contrasena-larga-1234",
    "public_base_url": "https://fidelidad.example.com",
    "email_from": "tarjetas@example.com",
    "email_smtp_host": "smtp.example.com",
    "database_url": "postgresql+psycopg://fidelity:clave-propia@db:5432/fidelity",
}


def _prod(**overrides: object) -> Settings:
    """Settings de producción con overrides por palabra clave (tipado en las pruebas)."""
    values: dict[str, object] = {**PROD, **overrides}
    # Merge parcial del TypedDict: el esquema estricto lo valida el propio Settings.
    return Settings(**values)  # type: ignore[arg-type]


def test_apple_a_medias_no_arranca_en_produccion() -> None:
    with pytest.raises(ValueError, match="APPLE_PASS_KEY_PATH"):
        Settings(
            **PROD,
            wallet_provider="apple",
            apple_pass_type_identifier="pass.com.ejemplo",
            apple_team_identifier="TEAM1",
            apple_pass_cert_path="/secrets/cert.pem",
        )


def test_google_a_medias_no_arranca_en_produccion() -> None:
    with pytest.raises(ValueError, match="GOOGLE_WALLET_ISSUER_ID"):
        Settings(**PROD, wallet_provider="google")


def test_produccion_exige_correo_transaccional() -> None:
    with pytest.raises(ValueError, match="EMAIL_FROM.*EMAIL_SMTP_HOST"):
        Settings(
            app_env="production",
            auth_session_secret="x" * 32,
            auth_bootstrap_email="admin@example.com",
            auth_bootstrap_password="contrasena-larga-1234",
            public_base_url="https://fidelidad.example.com",
        )


def test_en_desarrollo_puede_seleccionar_apple_sin_credenciales() -> None:
    # El proveedor queda `not_configured` y así se muestra (§17.2).
    settings = Settings(wallet_provider="apple")
    assert settings.wallet_provider == "apple"


def test_desarrollo_sin_credenciales_sigue_funcionando() -> None:
    settings = Settings()
    assert settings.wallet_provider == "simulated"
    assert settings.public_base_url == ""


def test_produccion_rechaza_la_session_secret_de_ejemplo() -> None:
    """El valor público de `.env.example` no puede ser el de producción."""
    with pytest.raises(ValueError, match="AUTH_SESSION_SECRET"):
        _prod(auth_session_secret="desarrollo-local-sin-secreto-real")


def test_produccion_rechaza_el_password_bootstrap_de_ejemplo() -> None:
    with pytest.raises(ValueError, match="AUTH_BOOTSTRAP_PASSWORD"):
        _prod(auth_bootstrap_password="contrasena-de-desarrollo-1234")


def test_produccion_rechaza_la_base_de_datos_de_ejemplo() -> None:
    """`localai:localai` es de .env.example: producción exige credenciales propias."""
    with pytest.raises(ValueError, match="DATABASE_URL"):
        _prod(database_url="postgresql+psycopg://localai:localai@db:5432/localai_fidelity")


def test_produccion_con_credenciales_propias_arranca() -> None:
    settings = _prod(
        auth_session_secret="e" * 40,
        auth_bootstrap_password="otra-clave-de-produccion-9012",
        database_url="postgresql+psycopg://fidelity:clave-propia@db:5432/fidelity",
    )
    assert settings.is_production
