"""Construcción de URLs públicas: siempre absolutas (§14.1, §5.2).

Un QR que contiene una ruta relativa (`/go/{slug}`) no abre nada al escanearlo
con un móvil: el lector muestra el texto tal cual. Por eso todo contenido que
sale en un QR o se programa en una etiqueta NFC debe ser una **URL completa**.

La base pública se resuelve en este orden:

1. `PUBLIC_BASE_URL` (autoridad canónica del despliegue; la recomendada).
2. Cabeceras `X-Forwarded-Host` / `X-Forwarded-Proto` del proxy inverso.
3. La base de la propia petición (útil en desarrollo directo contra la API).
"""

from fastapi import Request

from app.core.config import Settings


def resolve_public_base(request: Request, settings: Settings) -> str:
    """Devuelve la base pública (`https://dominio`, sin barra final)."""
    if settings.public_base_url:
        return settings.public_base_url.rstrip("/")
    forwarded_host = request.headers.get("x-forwarded-host")
    if forwarded_host:
        proto = request.headers.get("x-forwarded-proto", "http")
        return f"{proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


def absolute_url(path: str, base: str) -> str:
    """Une una ruta (`/go/slug`) a una base pública, sin duplicar barras."""
    return f"{base}/{path.lstrip('/')}"
