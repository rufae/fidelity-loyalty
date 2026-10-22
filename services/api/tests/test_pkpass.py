"""Generación del `.pkpass` de Apple (FASE 5) con certificado de prueba.

La firma real usa el certificado del Pass Type ID; aquí se valida el pipeline
completo (pass.json + manifest + firma PKCS7 + zip) con un certificado
autofirmado generado en la propia prueba. La validación en iPhone con
credenciales de producción queda bloqueada por credenciales (§19.5).
"""

import io
import json
import zipfile
from datetime import UTC, datetime, timedelta

from app.integrations.wallet.pkpass import (
    CryptographySigner,
    PassBuildError,
    PassCard,
    StaticSigner,
    build_pkpass,
    pass_json,
)
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs7
from cryptography.x509.oid import NameOID

CARD = PassCard(
    merchant_name="Cafetería Norte",
    program_name="Club del Café",
    serial="abc123serial",
    pass_type_identifier="pass.com.localai.fidelity",
    team_identifier="TEAM123456",
    organization_name="Cafetería Norte",
    authentication_token="0123456789abcdef",
    barcode_value="https://fidelity.example.com/card/320d7c2a19160de9",
    stamps=7,
)


def _signer() -> CryptographySigner:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Pass Type ID: prueba")])
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.now(UTC) - timedelta(days=1))
        .not_valid_after(datetime.now(UTC) + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    return CryptographySigner(
        certificate_pem=cert.public_bytes(serialization.Encoding.PEM),
        private_key_pem=key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        ),
    )


def test_el_pkpass_es_un_zip_completo_y_firmado() -> None:
    data = build_pkpass(CARD, _signer())

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = set(archive.namelist())
        assert {"pass.json", "manifest.json", "signature", "icon.png"} <= names
        manifest = json.loads(archive.read("manifest.json"))
        # El manifest lista la huella SHA-1 de cada recurso incluido.
        assert "pass.json" in manifest and "icon.png" in manifest
        # La firma PKCS7 detached existe y contiene certificados.
        signature = archive.read("signature")
        assert len(signature) > 100
        signer_certs = pkcs7.load_der_pkcs7_certificates(signature)
        assert signer_certs  # el certificado del firmante está embebido


def test_el_pass_json_no_contiene_datos_personales() -> None:
    payload = pass_json(CARD)
    blob = json.dumps(payload)
    assert "cliente@example.com" not in blob
    assert "Cliente" not in blob
    barcode = payload["barcode"]
    assert isinstance(barcode, dict)
    # Corrección de auditoría (§9.3): el QR del pase lleva el token opaco de
    # la tarjeta, NO el UUID interno de la base de datos.
    assert barcode["message"] == CARD.barcode_value
    assert CARD.serial not in barcode["message"]


def test_falta_configuracion_no_genera_pase() -> None:
    import pytest

    with pytest.raises(PassBuildError):
        build_pkpass(
            PassCard(
                merchant_name="X",
                program_name="Y",
                serial="s",
                pass_type_identifier="",
                team_identifier="T",
                organization_name="X",
                authentication_token="0123456789abcdef",
                barcode_value="https://fidelity.example.com/card/s",
            ),
            StaticSigner(_signer()),
        )
    with pytest.raises(PassBuildError):
        build_pkpass(
            PassCard(
                merchant_name="X",
                program_name="Y",
                serial="s",
                pass_type_identifier="p",
                team_identifier="T",
                organization_name="X",
                authentication_token="corto",
                barcode_value="https://fidelity.example.com/card/s",
            ),
            StaticSigner(_signer()),
        )
