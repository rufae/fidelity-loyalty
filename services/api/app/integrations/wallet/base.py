"""Adaptador de Wallet (AGENTS.md §6.6, ADR-0002).

El dominio **no** conoce Apple ni Google: solo esta interfaz. Cada proveedor
expone su estado (`not_configured`/`test`/`active`/`error`/`disabled`) y sus
operaciones devuelven resultados estructurados que el servicio persiste.

Regla irrenunciable (§6.1): la fidelización **no depende** de Wallet. Si el
proveedor falla, el ledger sigue siendo la fuente de verdad y el error queda
visible y reintenable (§15).
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol
from uuid import UUID


class ProviderStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    TEST = "test"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass(frozen=True)
class PassContext:
    """Datos visibles del pase (los construye el servicio desde el ledger).

    El dominio sigue sin conocer a Apple ni Google: este contexto viaja por la
    interfaz para que cada proveedor construya su artefacto con la marca del
    comercio y el saldo **real** del backend.
    """

    merchant_name: str
    program_name: str
    stamps: int
    #: Identificador opaco que irá en el barcode (URL de la tarjeta web).
    barcode_value: str
    #: Serial estable del pase (por membresía).
    serial: str
    #: Token de autenticación del servicio web de Apple (PassKit, §6.4).
    authentication_token: str = ""
    #: Base del servicio web de Apple (PassKit, §6.4); vacío = pase estático.
    web_service_url: str | None = None
    base_url: str = ""


@dataclass(frozen=True)
class PassResult:
    """Resultado de emitir/actualizar un pase."""

    provider_object_id: str
    status: ProviderStatus
    simulated: bool
    detail: str | None = None


@dataclass(frozen=True)
class AddToWalletAction:
    """Acción que la interfaz del cliente puede ofrecer (botón «Añadir a Wallet»)."""

    kind: str  # "simulated" | "apple" | "google"
    label: str
    url: str | None = None
    simulated: bool = True


class WalletProvider(Protocol):
    """Interfaz conceptual (§6.6). La implementación real puede diferir.

    `context` es opcional por compatibilidad: los proveedores que generan
    artefactos reales (`.pkpass`, JWT de Google) lo necesitan para mostrar la
    marca del comercio y el saldo confirmado.
    """

    name: str

    def status(self) -> ProviderStatus: ...

    def issue_pass(
        self, membership_id: UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult: ...

    def update_pass(
        self, membership_id: UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult: ...

    def revoke_pass(
        self, membership_id: UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult: ...

    def get_add_to_wallet_action(
        self, public_token: str, context: PassContext | None = None
    ) -> AddToWalletAction: ...
