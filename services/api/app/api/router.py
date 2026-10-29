"""Router versionado de la API (`/api/v1`)."""

from fastapi import APIRouter

from app.api import (
    auth,
    dashboard,
    go,
    loyalty,
    members,
    merchants,
    nfc,
    operations,
    passkit,
    platform,
    public,
    support,
    wallet,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(platform.router)
api_router.include_router(merchants.router)
api_router.include_router(loyalty.router)
api_router.include_router(public.router)
api_router.include_router(members.router)
api_router.include_router(operations.router)
api_router.include_router(wallet.router)
api_router.include_router(nfc.router)
api_router.include_router(dashboard.router)
api_router.include_router(support.merchant_router)
api_router.include_router(support.platform_router)
api_router.include_router(passkit.router)


#: Ruta corta pública de etiquetas (§12.8): vive en la raíz, no bajo /api/v1.
public_router = go.router
