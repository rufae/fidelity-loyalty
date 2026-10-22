"""Fábrica de proveedores de Wallet (§6.6, ADR-0002)."""

from app.core.config import Settings
from app.integrations.wallet.apple import AppleWalletProvider
from app.integrations.wallet.base import WalletProvider
from app.integrations.wallet.google import GoogleWalletProvider
from app.integrations.wallet.simulated import SimulatedWalletProvider


def get_wallet_provider(settings: Settings) -> WalletProvider:
    """Selecciona el adaptador configurado. Por defecto: simulado (§17.2)."""
    if settings.wallet_provider == "apple":
        return AppleWalletProvider(settings)
    if settings.wallet_provider == "google":
        return GoogleWalletProvider(settings)
    return SimulatedWalletProvider()
