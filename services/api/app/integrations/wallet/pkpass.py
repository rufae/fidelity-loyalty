"""Generación de `.pkpass` de Apple Wallet (FASE 5, §6.4).

Construye el paquete conforme a la documentación oficial de Wallet Passes:

- `pass.json` (storeCard de fidelización) con serial estable por membresía.
- `manifest.json` con la huella SHA-1 de cada recurso.
- `signature`: PKCS7 *detached* del manifest, firmado con el certificado del
  **Pass Type ID** e incluyendo el intermedio **WWDR** de Apple.
- Recursos gráficos (`icon.png` obligatorio).

La **firma** se abstrae (`PkpassSigner`): en producción usa el certificado y
la clave privada del comercio/plataforma (nunca en Git, §16.1); en pruebas se
inyecta un firmante con un certificado generado al vuelo. La validación final
(del pase en un iPhone con credenciales reales) queda etiquetada como
`blocked_by_credentials` en `docs/PRODUCTION_IMPLEMENTATION_PLAN.md`.

Referencias:
https://developer.apple.com/documentation/walletpasses
"""

import hashlib
import io
import json
import zipfile
from base64 import b64decode
from dataclasses import dataclass
from typing import Protocol

# PNG mínimo válido (icono por defecto si el comercio no sube recursos).
_DEFAULT_ICON_PNG = b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQ"
    "AAAABJRU5ErkJggg=="
)


@dataclass(frozen=True)
class PassCard:
    """Datos visibles del pase; nunca incluye email ni nombre del cliente."""

    merchant_name: str
    program_name: str
    serial: str
    pass_type_identifier: str
    team_identifier: str
    organization_name: str
    authentication_token: str
    #: Valor del QR del pase: la URL absoluta de la tarjeta web con el token
    #: opaco (§5.2, §6.3). Nunca el `serial` (UUID interno de base de datos).
    barcode_value: str
    web_service_url: str | None = None
    label: str = "Sellos"
    stamps: int = 0
    logo_text: str | None = None
    background_color: str = "rgb(108, 92, 231)"


class PkpassSigner(Protocol):
    """Devuelve la firma PKCS7 (detached) del manifest."""

    def sign(self, manifest: bytes) -> bytes: ...


@dataclass
class StaticSigner:
    """Firmante inyectado (pruebas con certificado propio)."""

    _sign: "PkpassSigner"  # delegado

    def sign(self, manifest: bytes) -> bytes:
        return self._sign.sign(manifest)


@dataclass
class PassBuildError(Exception):
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def pass_json(card: PassCard) -> dict[str, object]:
    """Cuerpo del pase (storeCard) con barcode opaco (§5.2, §6.3)."""
    payload: dict[str, object] = {
        "formatVersion": 1,
        "passTypeIdentifier": card.pass_type_identifier,
        "teamIdentifier": card.team_identifier,
        "organizationName": card.organization_name,
        "serialNumber": card.serial,
        "logoText": card.logo_text or card.merchant_name,
        "description": f"Tarjeta de fidelización de {card.merchant_name}",
        "foregroundColor": "rgb(255,255,255)",
        "backgroundColor": card.background_color,
        "barcode": {
            "format": "PKBarcodeFormatQR",
            # El token opaco de la tarjeta, no el UUID interno de la BD
            # (§9.3): el personal escanea esto y el backend resuelve la
            # membresía por `public_token`.
            "message": card.barcode_value,
            "messageEncoding": "iso-8859-1",
        },
        "storeCard": {
            "primaryFields": [
                {"key": "program", "label": "PROGRAMA", "value": card.program_name},
                {"key": "stamps", "label": card.label.upper(), "value": str(card.stamps)},
            ]
        },
    }
    if card.web_service_url:
        # Servicio web de actualización (PassKit, §6.4): sin esto el pase es
        # estático y los sellos mostrados nunca cambian.
        payload["webServiceURL"] = card.web_service_url
        payload["authenticationToken"] = card.authentication_token
    return payload


def _manifest(files: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha1(content).hexdigest() for name, content in files.items()}


def build_pkpass(
    card: PassCard,
    signer: PkpassSigner,
    *,
    images: dict[str, bytes] | None = None,
    extra_files: dict[str, bytes] | None = None,
) -> bytes:
    """Devuelve el `.pkpass` (zip) listo para servir con `application/vnd.apple.pkpass`."""
    if not card.pass_type_identifier or not card.team_identifier:
        raise PassBuildError("Faltan Pass Type Identifier o Team Identifier")
    if len(card.authentication_token) < 16:
        raise PassBuildError("El authenticationToken del pase es demasiado corto")

    resources: dict[str, bytes] = {"icon.png": _DEFAULT_ICON_PNG, **(images or {})}
    files: dict[str, bytes] = {
        "pass.json": json.dumps(pass_json(card), ensure_ascii=False).encode(),
        **{name: content for name, content in resources.items()},
        **(extra_files or {}),
    }
    manifest_bytes = json.dumps(_manifest(files), sort_keys=True).encode()
    signature = signer.sign(manifest_bytes)
    if not signature:
        raise PassBuildError("La firma del pase está vacía")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("manifest.json", manifest_bytes)
        archive.writestr("signature", signature)
    return buffer.getvalue()


@dataclass
class CryptographySigner:
    """Firmante real PKCS7 con `cryptography` (certificado Pass Type ID)."""

    certificate_pem: bytes
    private_key_pem: bytes
    wwdr_pem: bytes | None = None
    password: bytes | None = None

    def sign(self, manifest: bytes) -> bytes:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec, rsa
        from cryptography.hazmat.primitives.serialization import pkcs7

        cert = x509.load_pem_x509_certificate(self.certificate_pem)
        key = serialization.load_pem_private_key(self.private_key_pem, password=self.password)
        if not isinstance(key, (rsa.RSAPrivateKey, ec.EllipticCurvePrivateKey)):
            raise PassBuildError("La clave privada del Pass Type ID no es RSA ni EC")
        builder = (
            pkcs7.PKCS7SignatureBuilder().set_data(manifest).add_signer(cert, key, hashes.SHA256())
        )
        if self.wwdr_pem:
            builder = builder.add_certificate(x509.load_pem_x509_certificate(self.wwdr_pem))
        signature: bytes = builder.sign(
            serialization.Encoding.DER, [pkcs7.PKCS7Options.DetachedSignature]
        )
        return signature
