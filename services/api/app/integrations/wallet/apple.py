"""Adaptador Apple Wallet (FASE 5, §6.4).

Cuando hay credenciales (Pass Type ID + certificado + clave privada + WWDR)
genera un `.pkpass` **real** con `app.integrations.wallet.pkpass` y lo sirve
el endpoint público de descarga; sin credenciales devuelve
`wallet_provider_not_configured` sin fingir nada (§17.2).

Estado de validación: el pase se construye y firma conforme a la
documentación oficial, pero la **instalación en un iPhone con credenciales de
producción** no está probada: fase etiquetada `blocked_by_credentials` en
`docs/PRODUCTION_IMPLEMENTATION_PLAN.md`.

Referencias (vigentes a comprobar antes de producción):
https://developer.apple.com/documentation/walletpasses
"""

import logging
import uuid
from pathlib import Path

from app.core.config import Settings
from app.integrations.wallet.base import (
    AddToWalletAction,
    PassContext,
    PassResult,
    ProviderStatus,
)
from app.integrations.wallet.pkpass import (
    CryptographySigner,
    PassBuildError,
    PassCard,
    build_pkpass,
)

logger = logging.getLogger(__name__)


class AppleWalletProvider:
    name = "apple"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _configured(self) -> bool:
        return bool(
            self._settings.apple_pass_type_identifier
            and self._settings.apple_team_identifier
            and self._settings.apple_pass_cert_path
            and self._settings.apple_pass_key_path
        )

    def status(self) -> ProviderStatus:
        return ProviderStatus.ACTIVE if self._configured() else ProviderStatus.NOT_CONFIGURED

    def _card(self, context: PassContext) -> PassCard:
        return PassCard(
            merchant_name=context.merchant_name,
            program_name=context.program_name,
            serial=context.serial,
            pass_type_identifier=self._settings.apple_pass_type_identifier or "",
            team_identifier=self._settings.apple_team_identifier or "",
            organization_name=context.merchant_name,
            authentication_token=context.authentication_token or context.serial,
            # El QR del pase lleva el token opaco de la tarjeta, nunca el UUID
            # interno de la base de datos (§9.3, corrección de la auditoría).
            barcode_value=context.barcode_value,
            web_service_url=context.web_service_url,
            label="Sellos",
            stamps=context.stamps,
        )

    def build_pass(self, context: PassContext) -> bytes:
        """Construye y firma el `.pkpass` de la membresía."""
        if not self._configured():
            raise PassBuildError("Apple Wallet no está configurado")
        wwdr = self._settings.apple_wwdr_cert_path
        signer = CryptographySigner(
            certificate_pem=Path(self._settings.apple_pass_cert_path or "").read_bytes(),
            private_key_pem=Path(self._settings.apple_pass_key_path or "").read_bytes(),
            wwdr_pem=Path(wwdr).read_bytes() if wwdr else None,
            password=(
                self._settings.apple_pass_cert_password.encode()
                if self._settings.apple_pass_cert_password
                else None
            ),
        )
        return build_pkpass(self._card(context), signer)

    def issue_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        if not self._configured():
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.NOT_CONFIGURED,
                simulated=False,
                detail=(
                    "Apple Wallet no está configurado: faltan credenciales de Pass Type ID "
                    "(ver docs/WALLET_INTEGRATIONS.md)"
                ),
            )
        if context is None:
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.ERROR,
                simulated=False,
                detail="Faltan datos del pase (contexto) para generar el .pkpass",
            )
        try:
            self.build_pass(context)
        except PassBuildError as error:
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.ERROR,
                simulated=False,
                detail=str(error),
            )
        except OSError as error:
            # Sin la ruta del fichero en el detalle: revela topología de
            # secretos (§23 de AGENTS.md). El log del servidor la conserva.
            logger.warning(
                "apple: no se pudo leer el material criptográfico (%s)",
                type(error).__name__,
            )
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.ERROR,
                simulated=False,
                detail="No se pudo leer el material criptográfico de Apple Wallet",
            )
        # Pase generado y firmado. La instalación en el dispositivo la realiza
        # el usuario; el servidor no puede confirmarla (ADR-0005).
        return PassResult(
            provider_object_id=context.serial,
            status=ProviderStatus.ACTIVE,
            simulated=False,
            detail="pase .pkpass generado y firmado; instalación pendiente del usuario",
        )

    def update_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        # El pase se reconstruye con el saldo actual; con `webServiceURL` el
        # dispositivo lo descarga por el servicio web de Apple (§6.4).
        result = self.issue_pass(membership_id, public_token, context)
        if result.status == ProviderStatus.ACTIVE:
            return PassResult(
                provider_object_id=result.provider_object_id,
                status=ProviderStatus.ACTIVE,
                simulated=False,
                detail="pase actualizado; el dispositivo lo descarga vía servicio web",
            )
        return result

    def revoke_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        # ADR-0005: Apple admite marcar el pase como anulado (el borrado del
        # dispositivo depende del usuario). Delegar en `issue_pass` re-emitía
        # el pase y lo marcaba como activo: corrección de la auditoría.
        return PassResult(
            provider_object_id=context.serial if context else "",
            status=ProviderStatus.DISABLED,
            simulated=False,
            detail=(
                "pase invalidado en el servidor; el dispositivo lo retira al "
                "sincronizar (el borrado manual depende del usuario)"
            ),
        )

    def get_add_to_wallet_action(
        self, public_token: str, context: PassContext | None = None
    ) -> AddToWalletAction:
        if not self._configured():
            return AddToWalletAction(
                kind="apple",
                label="Añadir a Apple Wallet (no configurado)",
                url=None,
                simulated=False,
            )
        return AddToWalletAction(
            kind="apple",
            label="Añadir a Apple Wallet",
            url=f"/api/v1/public/memberships/{public_token}/apple-pass",
            simulated=False,
        )
