"""JWT «Save to Google Wallet» (FASE 6) con clave de prueba.

Valida estructura, firma RS256 y claims con una cuenta de servicio generada en
la propia prueba. La validación con issuer aprobado y dispositivo Android
queda bloqueada por credenciales (§19.5).
"""

import json
from base64 import urlsafe_b64decode

import pytest
from app.integrations.wallet.google_wallet import (
    AUDIENCE,
    GoogleCredentials,
    build_save_jwt,
    loyalty_class_payload,
    loyalty_object_payload,
    save_url,
)
from app.integrations.wallet.pkpass import PassBuildError
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
CREDS = GoogleCredentials(
    client_email="cuenta@proyecto.iam.gserviceaccount.com",
    private_key_pem=KEY.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ),
)
CLASS = loyalty_class_payload(
    class_id="program-1", issuer_id="12345", merchant_name="Cafetería Norte", program_name="Club"
)
OBJECT = loyalty_object_payload(
    object_id="card-1",
    issuer_id="12345",
    class_id="program-1",
    account_name="Cafetería Norte",
    account_id="https://fidelidad.test/card/token-opaco",
    stamps=7,
)


def _part(segment: str) -> bytes:
    return urlsafe_b64decode(segment + "=" * (-len(segment) % 4))


def test_jwt_firmado_con_los_claims_esperados() -> None:
    jwt = build_save_jwt(credentials=CREDS, class_payload=CLASS, object_payload=OBJECT)
    header_b64, payload_b64, signature_b64 = jwt.split(".")

    header = json.loads(_part(header_b64))
    assert header == {"alg": "RS256", "typ": "JWT"}

    # La firma RS256 es válida con la clave pública de la cuenta de servicio.
    KEY.public_key().verify(
        _part(signature_b64),
        f"{header_b64}.{payload_b64}".encode(),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )

    payload = json.loads(_part(payload_b64))
    assert payload["iss"] == CREDS.client_email
    assert payload["aud"] == AUDIENCE
    assert payload["typ"] == "savetowallet"
    inner = payload["payload"]
    assert inner["loyaltyClasses"][0]["programName"] == "Club"
    assert inner["loyaltyObjects"][0]["loyaltyPoints"]["balance"]["int"] == 7
    # El barcode lleva el identificador opaco, nunca el email del cliente.
    assert "token-opaco" in inner["loyaltyObjects"][0]["barcode"]["value"]
    assert "cuenta@" not in json.dumps(inner["loyaltyObjects"])


def test_url_de_guardado_es_la_oficial() -> None:
    jwt = build_save_jwt(credentials=CREDS, class_payload=CLASS, object_payload=OBJECT)
    assert save_url(jwt).startswith("https://pay.google.com/gp/v/save/")


def test_sin_credenciales_no_se_genera_nada() -> None:
    with pytest.raises(PassBuildError):
        build_save_jwt(
            credentials=GoogleCredentials(client_email="", private_key_pem=b""),
            class_payload=CLASS,
            object_payload=OBJECT,
        )
