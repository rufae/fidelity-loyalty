"""Proveedor de Wallet simulado (§17.2, ADR-0002).

Emite pases **ficticios** pero persistidos para poder desarrollar y probar el
flujo completo sin credenciales. Todo pase de este proveedor queda rotulado
como simulado en API e interfaz: nunca puede confundirse con un pase real.
"""

import uuid

from app.integrations.wallet.base import (
    AddToWalletAction,
    PassContext,
    PassResult,
    ProviderStatus,
)


class SimulatedWalletProvider:
    name = "simulated"

    def status(self) -> ProviderStatus:
        return ProviderStatus.TEST

    def issue_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        return PassResult(
            provider_object_id=f"sim.{membership_id.hex[:16]}",
            status=ProviderStatus.TEST,
            simulated=True,
            detail="Pase simulado: no existe en Apple Wallet ni en Google Wallet",
        )

    def update_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        return self.issue_pass(membership_id, public_token)

    def revoke_pass(
        self, membership_id: uuid.UUID, public_token: str, context: PassContext | None = None
    ) -> PassResult:
        return PassResult(
            provider_object_id=f"sim.{membership_id.hex[:16]}",
            status=ProviderStatus.DISABLED,
            simulated=True,
            detail="Pase simulado revocado",
        )

    def get_add_to_wallet_action(
        self, public_token: str, context: PassContext | None = None
    ) -> AddToWalletAction:
        return AddToWalletAction(
            kind="simulated",
            label="Wallet (SIMULADO — sin credenciales reales)",
            url=None,
            simulated=True,
        )
