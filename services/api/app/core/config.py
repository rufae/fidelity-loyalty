"""Configuración tipada del backend, leída del entorno y de `.env` (AGENTS.md §16.1)."""

import ipaddress
from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

#: Valores de desarrollo publicados en `.env.example` (no son secretos: están
#: en el propio repositorio). Producción los rechaza para no arrancar jamás
#: con credenciales conocidas.
_KNOWN_DEV_SESSION_SECRET = "desarrollo-local-sin-secreto-real"
_KNOWN_DEV_BOOTSTRAP_PASSWORD = "contrasena-de-desarrollo-1234"

Environment = Literal["development", "test", "production"]


class Settings(BaseSettings):
    """Variables de entorno del backend.

    Ningún valor de este fichero es un secreto real: los secretos (certificados
    Wallet, claves de cuenta de servicio, firmas de sesión) llegan por entorno
    y nunca se versionan (§16.1).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "LocalAI Fidelity API"
    app_version: str = "0.1.0"
    app_env: Environment = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"

    # Base pública canónica del despliegue (§14.1). Se usa para generar URLs
    # **absolutas** en los QR y en los enlaces que se programan en etiquetas
    # NFC: una ruta relativa en un QR no abre nada al escanearla con un móvil.
    # Ej.: `http://localhost:8100` en la LAN o `https://fidelidad.dominio`
    # en producción. Vacío → se resuelve con las cabeceras del proxy o con la
    # base de la petición (ver `app/core/urls.py`).
    public_base_url: str = ""
    #: Decisión explícita de servicio solo privado (§14.1): permite que
    #: PUBLIC_BASE_URL sea un host privado en producción.
    allow_private_public_base_url: bool = False

    # Puerto 5434 reservado para este proyecto (ADR-0002): en docker-compose se
    # sobreescribe a `db:5432`.
    database_url: str = "postgresql+psycopg://localai:localai@localhost:5434/localai_fidelity"

    # Autenticación (§8.3, §16.2). **No existe interruptor para desactivarla**:
    # la plataforma guarda datos de clientes de comercios. En producción el
    # arranque falla sin secreto (fail-closed); en desarrollo se genera uno
    # efímero por proceso si falta.
    auth_session_secret: str | None = None
    auth_session_ttl_seconds: int = 604800
    auth_login_max_attempts: int = 5
    auth_login_window_seconds: int = 300
    # Pimienta para la huella de emails en la auditoría de login (§8.1 de la
    # auditoría): sin ella la huella es un SHA-256 reversible por diccionario
    # sobre el espacio pequeño de correos de un negocio. Vacío = modo antiguo.
    auth_email_hash_pepper: str = ""
    # Usuario inicial de la plataforma: solo se crea si la tabla de usuarios
    # está vacía (semilla idempotente, nunca un admin/admin por defecto §8.3).
    auth_bootstrap_email: str | None = None
    auth_bootstrap_password: str | None = None

    # Correo transaccional requerido para verificar altas y recuperar tarjetas.
    email_from: str | None = None
    email_smtp_host: str | None = None
    email_smtp_port: int = 587
    email_smtp_username: str | None = None
    email_smtp_password: str | None = None
    email_smtp_starttls: bool = True
    email_smtp_ssl: bool = False
    email_smtp_timeout_seconds: int = 10

    # Soporte B2B (Plan.md §11): buzón interno + avisos por email/ntfy/Telegram.
    # Todas las capas externas son opt-in y, si fallan, la conversación sigue
    # viva en el panel: los avisos nunca son la fuente de verdad.
    support_email_enabled: bool = True
    #: Correo privado del propietario de la plataforma. Nunca se muestra al comercio.
    support_notification_email: str | None = None
    #: Remitente genérico del soporte; si falta se usa EMAIL_FROM.
    support_from_email: str | None = None
    support_ntfy_enabled: bool = False
    support_ntfy_base_url: str | None = None
    support_ntfy_topic: str | None = None
    support_ntfy_token: str | None = None
    #: URL del servidor ntfy **publicada** para que los comercios se
    #: suscriban desde su móvil. Si falta, los avisos al comercio solo son
    #: entregables desde la red interna (§18.2: la exposición se decide
    #: explícitamente).
    support_ntfy_public_url: str | None = None
    support_telegram_enabled: bool = False
    support_telegram_bot_token: str | None = None
    support_telegram_chat_id: str | None = None
    support_worker_enabled: bool = False
    support_worker_poll_seconds: int = 15
    support_notification_max_attempts: int = 5
    support_notification_backoff_seconds: int = 30
    #: Clave para cifrar teléfonos de solicitud de llamada (§12.2 de Plan.md).
    support_phone_encryption_key: str | None = None
    support_thread_rate_limit_per_day: int = 5
    support_message_rate_limit_per_day: int = 20
    support_callback_rate_limit_per_day: int = 3
    support_message_max_length: int = 4000

    # Adaptador de Wallet (§6.6, ADR-0002). Por defecto SIMULADO: el producto
    # completo funciona sin credenciales Apple/Google y la UI lo rotula como
    # tal para no confundirlo con una tarjeta emitida de verdad (§17.2).
    wallet_provider: Literal["simulated", "apple", "google"] = "simulated"

    # FASE 7/8: credenciales reales. Vacías por defecto → proveedor
    # `not_configured` (§6.4, §6.5). Nunca se versionan (§16.1).
    # Trabajos Wallet (§15): reintentos con backoff y dead-letter. El worker
    # es opt-in (WALLET_WORKER_ENABLED) para no interferir con las pruebas.
    wallet_job_max_attempts: int = 5
    wallet_job_backoff_seconds: int = 30
    wallet_worker_enabled: bool = False
    wallet_worker_poll_seconds: int = 15

    apple_pass_type_identifier: str | None = None
    apple_team_identifier: str | None = None
    apple_pass_cert_path: str | None = None
    apple_pass_key_path: str | None = None
    apple_pass_cert_password: str | None = None
    apple_wwdr_cert_path: str | None = None
    google_wallet_issuer_id: str | None = None
    google_wallet_service_account_json: str | None = None

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def bootstrap_configured(self) -> bool:
        return bool(self.auth_bootstrap_email and self.auth_bootstrap_password)

    @model_validator(mode="after")
    def _production_requires_auth(self) -> "Settings":
        """Fail-closed: producción sin autenticación configurada no arranca (§16.2)."""
        if self.is_production:
            if not self.auth_session_secret:
                raise ValueError(
                    "AUTH_SESSION_SECRET es obligatorio en producción: sin él, "
                    "una sesión forjada abriría la plataforma."
                )
            if not self.bootstrap_configured:
                raise ValueError(
                    "AUTH_BOOTSTRAP_EMAIL y AUTH_BOOTSTRAP_PASSWORD son obligatorios "
                    "en producción para poder crear el primer administrador."
                )
        if self.auth_bootstrap_password and len(self.auth_bootstrap_password) < 12:
            raise ValueError("AUTH_BOOTSTRAP_PASSWORD debe tener al menos 12 caracteres.")
        if self.email_smtp_timeout_seconds < 1:
            raise ValueError("EMAIL_SMTP_TIMEOUT_SECONDS debe ser al menos 1.")
        return self

    @model_validator(mode="after")
    def _production_requires_public_url(self) -> "Settings":
        """Producción exige una base pública utilizable por móviles ajenos (§14.1).

        Las etiquetas NFC se escanean con teléfonos normales: una URL de
        `localhost`, de red privada o de tailnet no les sirve. Si decides
        explícitamente un servicio solo privado, admítelo con
        `ALLOW_PRIVATE_PUBLIC_BASE_URL=true` (decisión documentada).
        """
        if not self.is_production:
            return self
        base = (self.public_base_url or "").strip()
        if not base:
            raise ValueError(
                "PUBLIC_BASE_URL es obligatoria en producción: los QR y las URLs NFC "
                "se generan con ella."
            )
        if not base.startswith("https://"):
            raise ValueError(
                "PUBLIC_BASE_URL debe ser https:// en producción (la cookie de sesión "
                "es Secure y las etiquetas se abren en móviles)."
            )
        if not self.allow_private_public_base_url:
            host = base.removeprefix("https://").split("/")[0].split(":")[0].lower()
            privada = host in {"localhost", "::1"} or host.endswith((".local", ".ts.net"))
            if not privada:
                try:
                    privada = not ipaddress.ip_address(host).is_global
                except ValueError:
                    privada = False  # nombre de dominio: se da por público
            if privada:
                raise ValueError(
                    f"PUBLIC_BASE_URL apunta a un host privado ({host}): los clientes "
                    "del comercio no podrían abrir las etiquetas NFC. Usa un dominio "
                    "público o marca ALLOW_PRIVATE_PUBLIC_BASE_URL=true si decides un "
                    "servicio solo privado."
                )
        return self

    @model_validator(mode="after")
    def _wallet_provider_config(self) -> "Settings":
        """No se puede «activar» un proveedor Wallet a medias (§17.4).

        En **producción**, si se elige `apple` o `google` deben estar todas sus
        variables: se informa de **cuáles faltan** (nunca de sus valores). En
        desarrollo se permite seleccionarlos sin credenciales y el proveedor se
        declara `not_configured` de forma honesta (§17.2).
        """
        if not self.is_production:
            return self
        if self.wallet_provider == "apple":
            faltan = [
                nombre
                for nombre, valor in {
                    "APPLE_PASS_TYPE_IDENTIFIER": self.apple_pass_type_identifier,
                    "APPLE_TEAM_IDENTIFIER": self.apple_team_identifier,
                    "APPLE_PASS_CERT_PATH": self.apple_pass_cert_path,
                    "APPLE_PASS_KEY_PATH": self.apple_pass_key_path,
                }.items()
                if not valor
            ]
            if faltan:
                raise ValueError("WALLET_PROVIDER=apple requiere: " + ", ".join(faltan))
        if self.wallet_provider == "google":
            faltan = [
                nombre
                for nombre, valor in {
                    "GOOGLE_WALLET_ISSUER_ID": self.google_wallet_issuer_id,
                    "GOOGLE_WALLET_SERVICE_ACCOUNT_JSON": self.google_wallet_service_account_json,
                }.items()
                if not valor
            ]
            if faltan:
                raise ValueError("WALLET_PROVIDER=google requiere: " + ", ".join(faltan))
        return self

    @model_validator(mode="after")
    def _support_channels_config(self) -> "Settings":
        """Un canal de aviso no se «activa» a medias: exige sus variables (§17.4).

        Si un canal está habilitado pero incompleto, falla al arrancar y se
        informa de **qué variable falta**, nunca de su valor (§16.1).
        """
        if self.support_ntfy_enabled and not (
            self.support_ntfy_base_url and self.support_ntfy_topic
        ):
            raise ValueError(
                "SUPPORT_NTFY_ENABLED=true requiere SUPPORT_NTFY_BASE_URL y SUPPORT_NTFY_TOPIC"
            )
        if self.support_telegram_enabled and not (
            self.support_telegram_bot_token and self.support_telegram_chat_id
        ):
            raise ValueError(
                "SUPPORT_TELEGRAM_ENABLED=true requiere SUPPORT_TELEGRAM_BOT_TOKEN y "
                "SUPPORT_TELEGRAM_CHAT_ID"
            )
        if self.support_worker_poll_seconds < 1:
            raise ValueError("SUPPORT_WORKER_POLL_SECONDS debe ser al menos 1.")
        if self.support_notification_max_attempts < 1:
            raise ValueError("SUPPORT_NOTIFICATION_MAX_ATTEMPTS debe ser al menos 1.")
        return self

    @model_validator(mode="after")
    def _production_requires_email(self) -> "Settings":
        """El acceso seguro a las tarjetas requiere correo transaccional en producción."""
        if not self.is_production:
            return self
        missing_mail = [
            name
            for name, value in {
                "EMAIL_FROM": self.email_from,
                "EMAIL_SMTP_HOST": self.email_smtp_host,
            }.items()
            if not value
        ]
        if missing_mail:
            raise ValueError(
                "La verificación de correo requiere configurar: " + ", ".join(missing_mail)
            )
        # Nunca credenciales ni enlaces de un solo uso en claro (§16.2): sin
        # STARTTLS o SSL, la API no arranca en producción.
        if not (self.email_smtp_ssl or self.email_smtp_starttls):
            raise ValueError(
                "El SMTP en producción exige cifrado: EMAIL_SMTP_SSL=true o "
                "EMAIL_SMTP_STARTTLS=true."
            )
        return self

    @model_validator(mode="after")
    def _production_rejects_known_dev_credentials(self) -> "Settings":
        """Producción no arranca con los valores de ejemplo de `.env.example`.

        Son públicos (están en el repositorio): copiarlos a un despliegue real
        equivale a no tener credenciales. Se informa del **nombre** de la
        variable, nunca de su valor.
        """
        if not self.is_production:
            return self
        if self.auth_session_secret == _KNOWN_DEV_SESSION_SECRET:
            raise ValueError(
                "AUTH_SESSION_SECRET usa el valor de ejemplo público de .env.example: "
                "genera uno propio (openssl rand -hex 32)."
            )
        if self.auth_bootstrap_password == _KNOWN_DEV_BOOTSTRAP_PASSWORD:
            raise ValueError(
                "AUTH_BOOTSTRAP_PASSWORD usa el valor de ejemplo público de .env.example: "
                "genera uno propio."
            )
        if "localai:localai@" in self.database_url:
            raise ValueError(
                "DATABASE_URL usa el usuario y la contraseña de ejemplo de .env.example: "
                "define credenciales propias de producción."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Instancia única por proceso (las pruebas pueden invalidarla con `cache_clear`)."""
    return Settings()
