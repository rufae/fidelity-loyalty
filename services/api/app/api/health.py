"""Endpoints de salud (sin prefijo versionado: los healthchecks de Docker los usan)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.core.config import Settings, get_settings
from app.db.session import DatabaseStatus, check_database

router = APIRouter(tags=["salud"])


def database_status() -> DatabaseStatus:
    """Separado de la ruta para poder sustituirlo en las pruebas."""
    return check_database()


@router.get("/health")
def health(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, str]:
    """Liveness: el proceso responde. No toca la base de datos."""
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/ready")
def ready(
    response: Response,
    settings: Annotated[Settings, Depends(get_settings)],
    status: Annotated[DatabaseStatus, Depends(database_status)],
) -> dict[str, str]:
    """Readiness: solo `ready` si la base de datos responde (503 si no)."""
    payload = {
        "status": "ready" if status.reachable else "not_ready",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "database": "ok" if status.reachable else "unavailable",
        "wallet_provider": settings.wallet_provider,
    }
    if not status.reachable:
        response.status_code = 503
    return payload
