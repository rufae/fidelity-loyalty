"""Cifrado SMTP (§16.2): nunca credenciales ni enlaces de un solo uso en claro.

Regresión de la auditoría de cierre (riesgo «SMTP sin cifrar»): la producción
exige cifrado al arrancar y el envío lo defiende también en caliente, con
verificación del certificado del servidor en ambos modos.
"""

import smtplib
import ssl
from email.message import EmailMessage

import pytest
from app.core.config import Settings
from app.domain.errors import DomainError
from app.services import email as email_service

_PROD_KWARGS = {
    "auth_session_secret": "x" * 32,
    "auth_bootstrap_email": "admin@example.com",
    "auth_bootstrap_password": "contrasena-larga-1234",
    "public_base_url": "https://fidelidad.example.com",
    "email_from": "tarjetas@fidelidad.example.com",
    "email_smtp_host": "smtp.example.com",
    # Credenciales de base propias: el `.env` local no debe filtrarse a la
    # construcción de configuración de producción en las pruebas.
    "database_url": "postgresql+psycopg://fidelity:clave-propia@db:5432/fidelity",
}


def _production(**overrides: object) -> Settings:
    return Settings(app_env="production", **_PROD_KWARGS, **overrides)  # type: ignore[arg-type]


def test_produccion_no_arranca_con_smtp_en_claro() -> None:
    """La validación de arranque bloquea SMTP sin STARTTLS ni SSL (fail-closed)."""
    with pytest.raises(ValueError, match="cifrado"):
        _production(email_smtp_starttls=False, email_smtp_ssl=False)


def test_produccion_acepta_starttls_o_ssl() -> None:
    assert _production().email_smtp_starttls is True
    assert _production(email_smtp_starttls=False, email_smtp_ssl=True).email_smtp_ssl is True


def test_envio_en_produccion_sin_cifrado_se_rechaza_en_caliente() -> None:
    """Defensa en profundidad: aunque un `.env` mal puesto lo permita, no se envía."""
    settings = _production()
    settings.email_smtp_starttls = False
    settings.email_smtp_ssl = False
    with pytest.raises(DomainError) as error:
        email_service.send_email(settings, "cliente@example.com", "Asunto", "Texto", "https://x/y")
    assert error.value.status_code == 503
    assert error.value.code == "email_delivery_not_configured"


def test_starttls_valida_el_certificado_del_servidor(monkeypatch: pytest.MonkeyPatch) -> None:
    """`starttls()` sin contexto NO verifica el servidor (MITM); debe ir con contexto."""
    captured: dict[str, object] = {}

    class _FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
            captured["host"] = host

        def __enter__(self) -> "_FakeSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: ssl.SSLContext | None = None) -> None:
            captured["context"] = context

        def send_message(self, message: object) -> None:
            captured["sent"] = True

    monkeypatch.setattr(smtplib, "SMTP", _FakeSMTP)
    settings = Settings(
        email_from="tarjetas@example.com",
        email_smtp_host="smtp.example.com",
        email_smtp_starttls=True,
        email_smtp_ssl=False,
    )
    email_service.send_email(settings, "cliente@example.com", "Asunto", "Texto", "https://x/y")

    context = captured.get("context")
    assert isinstance(context, ssl.SSLContext)
    assert context.check_hostname is True  # certificado verificado, no «unverified»
    assert captured.get("sent") is True


def test_ssl_directo_tambien_verifica_certificado(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class _FakeSSL:
        def __init__(
            self, host: str, port: int, timeout: int | None = None, context: object = None
        ) -> None:
            captured["context"] = context

        def __enter__(self) -> "_FakeSSL":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def login(self, user: str, password: str) -> None:
            captured["login"] = user

        def send_message(self, message: object) -> None:
            captured["sent"] = True

    monkeypatch.setattr(smtplib, "SMTP_SSL", _FakeSSL)
    settings = Settings(
        email_from="tarjetas@example.com",
        email_smtp_host="smtp.example.com",
        email_smtp_starttls=False,
        email_smtp_ssl=True,
        email_smtp_username="usuario",
        email_smtp_password="secreto",
    )
    email_service.send_email(settings, "cliente@example.com", "Asunto", "Texto", "https://x/y")

    context = captured.get("context")
    assert isinstance(context, ssl.SSLContext)
    assert context.check_hostname is True
    assert captured.get("sent") is True


def test_sin_configurar_falla_explicitamente() -> None:
    """Sin SMTP configurado la acción responde 503 con error de dominio legible."""
    settings = Settings(email_from=None, email_smtp_host=None)
    with pytest.raises(DomainError) as error:
        email_service.send_email(settings, "cliente@example.com", "Asunto", "Texto", "https://x/y")
    assert error.value.status_code == 503
    assert error.value.code == "email_delivery_not_configured"
    with pytest.raises(DomainError):
        email_service.ensure_email_configured(settings)


def test_mensaje_en_claro_no_lleva_enlace_si_falla(monkeypatch: pytest.MonkeyPatch) -> None:
    """Si el transporte falla, el error de dominio no filtra el enlace (§16.6)."""

    def _boom(*args: object, **kwargs: object) -> None:
        raise smtplib.SMTPException("554 relay denied")

    monkeypatch.setattr(smtplib, "SMTP", _boom)
    settings = Settings(email_from="a@example.com", email_smtp_host="smtp.example.com")
    with pytest.raises(DomainError) as error:
        email_service.send_email(
            settings, "cliente@example.com", "Asunto", "Texto", "https://x/secretotoken123"
        )
    assert error.value.status_code == 503
    detalle = error.value.detail
    assert isinstance(detalle, dict)
    assert "secretotoken123" not in str(detalle.get("message", ""))


def test_el_correo_tiene_diseno_de_marca_y_fallback_plano(monkeypatch: pytest.MonkeyPatch) -> None:
    """HTML sobrio con la identidad, sin recursos externos y texto plano usable."""
    captured: dict[str, EmailMessage] = {}

    class _CaptureSMTP:
        def __init__(self, host: str, port: int, timeout: int | None = None) -> None:
            pass

        def __enter__(self) -> "_CaptureSMTP":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def starttls(self, context: ssl.SSLContext | None = None) -> None:
            pass

        def send_message(self, message: EmailMessage) -> None:
            captured["message"] = message

    monkeypatch.setattr(smtplib, "SMTP", _CaptureSMTP)
    settings = Settings(
        email_from="tarjetas@example.com",
        email_smtp_host="smtp.example.com",
        email_smtp_starttls=True,
        email_smtp_ssl=False,
    )
    email_service.send_email(
        settings,
        "cliente@example.com",
        "Confirma tu correo",
        "Confirma que controlas este correo.",
        "https://fid.example.com/card/verify?token=abc123xyz",
        cta_label="Confirmar mi correo",
        merchant_name="Cafetería Norte",
    )

    message = captured["message"]
    html_part = message.get_body(preferencelist=("html",))
    plain_part = message.get_body(preferencelist=("plain",))
    assert html_part is not None and plain_part is not None
    html = html_part.get_content()
    plain = plain_part.get_content()

    # Diseño: manda el comercio (cabecera y «De» visible) y la plataforma
    # firma el pie; botón de acción y colores de la identidad.
    assert "Cafetería Norte" in html
    assert "Programa cedido por" in html and "LocalAI Fidelity" in html
    assert "#6c5ce7" in html and "#1a135c" in html
    assert "Confirmar mi correo" in html
    assert str(message["From"]).startswith("=?utf-8?") or "Cafetería Norte" in str(message["From"])
    assert "tarjetas@example.com" in str(message["From"])
    assert 'href="https://fid.example.com/card/verify?token=abc123xyz"' in html
    # Sin recursos externos (los clientes de correo los bloquean): ni imágenes
    # ni hojas de estilo remotas ni fuentes de terceros.
    assert "<img" not in html
    assert "http://cdn" not in html
    assert "@import" not in html
    # El texto plano lleva comercio, enlace completo y el aviso de ignorar.
    assert "Cafetería Norte" in plain
    assert "https://fid.example.com/card/verify?token=abc123xyz" in plain
    assert "Programa cedido por LocalAI Fidelity" in plain
    assert "ignora este mensaje" in plain
