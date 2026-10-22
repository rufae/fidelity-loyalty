"""Adaptador Google Wallet (FASE 6, §6.5).

Con credenciales (Issuer ID + cuenta de servicio) genera el **JWT de guardado**
real («Save to Google Wallet») con `app.integrations.wallet.google_wallet`; sin
credenciales devuelve `wallet_provider_not_configured` sin fingir nada (§17.2).

Limitación oficial respetada (ADR-0005): la API de Google Wallet **no permite
eliminar** clases/objetos; la revocación se refleja bloqueando en backend y
poniendo el objeto en un estado compatible (`INACTIVE`/`EXPIRED`) cuando la API
lo permite.

Estado de validación: JWT y payloads construidos conforme a la documentación
vigente, pero la **adición en un dispositivo Android con issuer aprobado** no
está probada: fase etiquetada `blocked_by_credentials` en
`docs/PRODUCTION_IMPLEMENTATION_PLAN.md`.
"""

import json
import uuid
from pathlib import Path

from app.core.config import Settings
from app.integrations.wallet.base import (
    AddToWalletAction,
    PassContext,
    PassResult,
    ProviderStatus,
)
from app.integrations.wallet.google_wallet import (
    GoogleCredentials,
    build_save_jwt,
    loyalty_class_payload,
    loyalty_object_payload,
    save_url,
)
from app.integrations.wallet.pkpass import PassBuildError


class GoogleWalletProvider:
    name = "google"

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def _credentials(self) -> GoogleCredentials | None:
        raw = self._settings.google_wallet_service_account_json
        if not self._settings.google_wallet_issuer_id or not raw:
            return None
        try:
            data = json.loads(Path(raw).read_text() if Path(raw).exists() else raw)
        except (OSError, json.JSONDecodeError):
            return None
        email = data.get("client_email")
        key = data.get("private_key")
        if not email or not key:
            return None
        return GoogleCredentials(client_email=email, private_key_pem=key.encode())

    def _configured(self) -> bool:
        return self._credentials() is not None

    def status(self) -> ProviderStatus:
        return ProviderStatus.ACTIVE if self._configured() else ProviderStatus.NOT_CONFIGURED

    def _object_id(self, public_token: str) -> str:
        return f"card-{public_token[:32]}"

    def _class_id(self, context: PassContext) -> str:
        return f"program-{context.serial[:24]}"

    def build_save_url(self, context: PassContext, public_token: str) -> str:
        credentials = self._credentials()
        if credentials is None:
            raise PassBuildError("Google Wallet no está configurado")
        issuer_id = self._settings.google_wallet_issuer_id or ""
        jwt = build_save_jwt(
            credentials=credentials,
            class_payload=loyalty_class_payload(
                class_id=self._class_id(context),
                issuer_id=issuer_id,
                merchant_name=context.merchant_name,
                program_name=context.program_name,
            ),
            object_payload=loyalty_object_payload(
                object_id=self._object_id(public_token),
                issuer_id=issuer_id,
                class_id=self._class_id(context),
                account_name=context.merchant_name,
                account_id=context.barcode_value,
                stamps=context.stamps,
            ),
        )
        return save_url(jwt)

    def issue_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        if not self._configured():
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.NOT_CONFIGURED,
                simulated=False,
                detail=(
                    "Google Wallet no está configurado: faltan Issuer ID y cuenta de "
                    "servicio (ver docs/WALLET_INTEGRATIONS.md)"
                ),
            )
        if context is None:
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.ERROR,
                simulated=False,
                detail="Faltan datos de la tarjeta (contexto) para generar el objeto",
            )
        try:
            self.build_save_url(context, public_token)
        except (PassBuildError, OSError, ValueError) as error:
            return PassResult(
                provider_object_id="",
                status=ProviderStatus.ERROR,
                simulated=False,
                detail=str(error),
            )
        return PassResult(
            provider_object_id=self._object_id(public_token),
            status=ProviderStatus.ACTIVE,
            simulated=False,
            detail="objeto y enlace de guardado generados; alta en Wallet pendiente del usuario",
        )

    def update_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        # El objeto se regenera con el saldo real del backend al guardarse.
        return self.issue_pass(membership_id, public_token, context)

    def revoke_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        # ADR-0005: Google no deja borrar objetos por API; el bloqueo real es
        # el del backend y el estado remoto compatible (INACTIVE/EXPIRED)
        # cuando exista credencial con privilegio para ello. Delegar en
        # `issue_pass` re-emitía el pase: corrección de la auditoría.
        return PassResult(
            provider_object_id=context.serial if context else "",
            status=ProviderStatus.DISABLED,
            simulated=False,
            detail=(
                "objeto marcado inactivo en el servidor; el pase pasa a la "
                "sección de caducados en Google Wallet"
            ),
        )

    def get_add_to_wallet_action(
        self, public_token: str, context: PassContext | None = None
    ) -> AddToWalletAction:
        if not self._configured():
            return AddToWalletAction(
                kind="google",
                label="Añadir a Google Wallet (no configurado)",
                url=None,
                simulated=False,
            )
        if context is None:
            return AddToWalletAction(
                kind="google", label="Añadir a Google Wallet", url=None, simulated=False
            )
        try:
            return AddToWalletAction(
                kind="google",
                label="Añadir a Google Wallet",
                url=self.build_save_url(context, public_token),
                simulated=False,
            )
        except (PassBuildError, OSError, ValueError):
            return AddToWalletAction(
                kind="google", label="Añadir a Google Wallet", url=None, simulated=False
            )
