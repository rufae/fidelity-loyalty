"""Emisión de Google Wallet (FASE 6, §6.5): clase/objeto y «Save to Google Wallet».

Construye el **JWT de guardado** firmado (RS256 con la clave de la cuenta de
servicio) y los payloads de `loyaltyClass`/`loyaltyObject` conforme a la
documentación oficial:

- https://developers.google.com/wallet/retail/loyalty-cards
- https://developers.google.com/wallet/retail/loyalty-cards/overview/add-to-google-wallet-flow

Limitación documentada (ADR-0005): la API de Google Wallet **no permite
borrar** clases/objetos; la revocación se refleja poniendo el objeto en un
estado compatible (`INACTIVE`/`EXPIRED`) y bloqueando en backend.

La validación con issuer real y dispositivo Android queda etiquetada como
`blocked_by_credentials` en `docs/PRODUCTION_IMPLEMENTATION_PLAN.md`.
"""

import json
import time
from base64 import urlsafe_b64encode
from dataclasses import dataclass

from app.integrations.wallet.pkpass import PassBuildError

AUDIENCE = "https://walletobjects.google.com/"
JWT_TYPE = "savetowallet"


@dataclass(frozen=True)
class GoogleCredentials:
    """Credenciales de la cuenta de servicio (nunca se versionan, §16.1)."""

    client_email: str
    private_key_pem: bytes


def _b64url(data: bytes) -> str:
    return urlsafe_b64encode(data).rstrip(b"=").decode()


def loyalty_class_payload(
    *, class_id: str, issuer_id: str, merchant_name: str, program_name: str
) -> dict[str, object]:
    """Clase (plantilla) por comercio (ADR-0004)."""
    return {
        "id": f"{issuer_id}.{class_id}",
        "issuerName": merchant_name,
        "programName": program_name,
        "reviewStatus": "UNDER_REVIEW",
    }


def loyalty_object_payload(
    *,
    object_id: str,
    issuer_id: str,
    class_id: str,
    account_name: str,
    account_id: str,
    stamps: int,
    label: str = "Sellos",
) -> dict[str, object]:
    """Objeto por membresía: identidad mínima y saldo real del backend."""
    return {
        "id": f"{issuer_id}.{object_id}",
        "classId": f"{issuer_id}.{class_id}",
        "state": "ACTIVE",
        "accountName": account_name,
        "accountId": account_id,
        "barcode": {"type": "QR_CODE", "value": account_id},
        "loyaltyPoints": {"label": label, "balance": {"int": stamps}},
    }


def build_save_jwt(
    *,
    credentials: GoogleCredentials,
    class_payload: dict[str, object],
    object_payload: dict[str, object],
    origins: list[str] | None = None,
    now: int | None = None,
) -> str:
    """JWT «Save to Google Wallet» (RS256) con clase y objeto embebidos."""
    if not credentials.client_email or not credentials.private_key_pem:
        raise PassBuildError("Faltan credenciales de la cuenta de servicio de Google")

    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding, rsa

    key = serialization.load_pem_private_key(credentials.private_key_pem, password=None)
    if not isinstance(key, rsa.RSAPrivateKey):
        raise PassBuildError("La clave de la cuenta de servicio de Google no es RSA")
    issued_at = int(now if now is not None else time.time())
    inner_payload: dict[str, object] = {
        "loyaltyClasses": [class_payload],
        "loyaltyObjects": [object_payload],
        "saveLoyaltyObjects": {"id": object_payload["id"]},
    }
    if origins:
        inner_payload["origins"] = [{"origin": origin} for origin in origins]
    header = {"alg": "RS256", "typ": "JWT"}
    payload: dict[str, object] = {
        "iss": credentials.client_email,
        "aud": AUDIENCE,
        "typ": JWT_TYPE,
        "iat": issued_at,
        "payload": inner_payload,
    }
    signing_input = (
        f"{_b64url(json.dumps(header, separators=(',', ':')).encode())}."
        f"{_b64url(json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode())}"
    ).encode()
    signature: bytes = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return f"{signing_input.decode()}.{_b64url(signature)}"


def save_url(jwt: str) -> str:
    """Enlace oficial «Save to Google Wallet»."""
    return f"https://pay.google.com/gp/v/save/{jwt}"
