"""Firma y verificación del token de sesión (§8.3).

Formato de la cookie: `<session_id>.<hmac_sha256(session_id)>`

- `session_id` es aleatorio (256 bits) y vive en la tabla `sessions`: permite
  **invalidar** una sesión concretamente (logout, robo, cambio de contraseña)
  sin tener que rotar el secreto global.
- La firma detecta cookies manipuladas sin tocar la base de datos.
- El secreto sale del entorno (`AUTH_SESSION_SECRET`). En desarrollo, si no
  existe, se genera uno efímero por proceso: las sesiones mueren al reiniciar,
  que es el comportamiento esperado sin configuración.
"""

import hashlib
import hmac
import secrets

from app.core.config import Settings

_SEPARATOR = "."


_EPHEMERAL_SECRET: str | None = None


def get_session_secret(settings: Settings) -> str:
    """Secreto efectivo: el configurado o uno efímero por proceso en desarrollo."""
    global _EPHEMERAL_SECRET
    if settings.auth_session_secret:
        return settings.auth_session_secret
    if _EPHEMERAL_SECRET is None:
        _EPHEMERAL_SECRET = secrets.token_hex(32)
    return _EPHEMERAL_SECRET


def new_session_id() -> str:
    return secrets.token_hex(32)


def sign_session_id(session_id: str, secret: str) -> str:
    digest = hmac.new(secret.encode(), session_id.encode(), hashlib.sha256).hexdigest()
    return f"{session_id}{_SEPARATOR}{digest}"


def verify_session_token(token: str, secret: str) -> str | None:
    """Devuelve el `session_id` si la firma es válida; `None` en cualquier fallo."""
    session_id, _, signature = token.partition(_SEPARATOR)
    if not session_id or not signature:
        return None
    expected = sign_session_id(session_id, secret)
    if not hmac.compare_digest(expected, f"{session_id}{_SEPARATOR}{signature}"):
        return None
    return session_id
