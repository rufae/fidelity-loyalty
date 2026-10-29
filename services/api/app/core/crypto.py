"""Cifrado de datos sensibles de soporte (§16.1, §12.2 de Plan.md).

El teléfono de una solicitud de llamada es un dato personal. Se guarda
cifrado con Fernet y una clave derivada de la configuración del servidor:
nunca en claro en base de datos, logs, correos ni notificaciones push.

La clave usa `SUPPORT_PHONE_ENCRYPTION_KEY` y, si no está definida, la clave
de sesión. Sin material de clave **no se cifra nada**: es mejor fallar
explícitamente que guardar un teléfono protegido con una clave inventada.
"""

import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import Settings
from app.domain.errors import DomainError

_KEY_CONTEXT = b"localai-fidelity-support-phone-v1"


def _fernet(settings: Settings) -> Fernet:
    material = settings.support_phone_encryption_key or settings.auth_session_secret
    if not material:
        raise DomainError(
            500,
            "support_phone_key_missing",
            "Falta la clave para proteger el teléfono de soporte.",
        )
    digest = hashlib.sha256(_KEY_CONTEXT + material.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_text(settings: Settings, plaintext: str) -> str:
    """Cifra texto corto para almacenarlo en una columna String."""
    return _fernet(settings).encrypt(plaintext.encode()).decode()


def decrypt_text(settings: Settings, ciphertext: str) -> str:
    """Descifra texto almacenado; un valor manipulado falla sin filtrar nada."""
    try:
        return _fernet(settings).decrypt(ciphertext.encode()).decode()
    except InvalidToken as exc:
        raise DomainError(
            500,
            "support_phone_decrypt_failed",
            "No se pudo leer el dato protegido.",
        ) from exc
