"""Endpoints públicos de la página de alta (§12.5, §13.4).

Son los únicos endpoints sin sesión. Deben exponer lo mínimo: condiciones,
recompensas y estado de apertura. Nunca datos de clientes ni IDs internos.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import DbSession
from app.core.config import Settings, get_settings
from app.schemas.loyalty import PublicProgramOut
from app.services import loyalty as loyalty_service

router = APIRouter(prefix="/public", tags=["público"])


class PublicRateLimiter:
    """Límite sencillo por IP para el tráfico público (§13.4, antiabuso)."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float) -> bool:
        import time as _time

        moment = now or _time.monotonic()
        window_start = moment - self._window
        hits = [h for h in self._hits.get(key, []) if h >= window_start]
        hits.append(moment)
        self._hits[key] = hits
        return len(hits) <= self._max

    def reset(self) -> None:
        self._hits.clear()


#: Escrituras públicas (alta de clientes): límite estricto por IP.
#: 60/min tolera una ráfaga real en mostrador y sigue frenando el abuso.
public_limiter = PublicRateLimiter(max_requests=60)

#: Anti-enumeración del alta (§8.2): mismo email, mismo programa. Impide
#: descubrir en masa qué correos están apuntados (la verificación por correo
#: sería el cierre definitivo, decisión del propietario).
enroll_limiter = PublicRateLimiter(max_requests=5, window_seconds=300)
card_access_limiter = PublicRateLimiter(max_requests=5, window_seconds=300)

#: Lecturas públicas (página de alta, tarjeta, QR): límite generoso.
#: La tarjeta se **sondea** para reflejar sellos y cambios de estado sin
#: recargar (varios dispositivos pueden compartir IP tras el NAT del local);
#: 300/min acota un cliente desbocado sin bloquear a nadie legítimo.
public_read_limiter = PublicRateLimiter(max_requests=300)


def check_public_rate(request: Request) -> None:
    from fastapi import HTTPException

    ip = request.client.host if request.client else "unknown"
    if not public_limiter.allow(ip, 0):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones")


def check_public_read_rate(request: Request) -> None:
    from fastapi import HTTPException

    ip = request.client.host if request.client else "unknown"
    if not public_read_limiter.allow(ip, 0):
        raise HTTPException(status_code=429, detail="Demasiadas peticiones")


@router.get("/programs/{merchant_slug}/{program_slug}", response_model=PublicProgramOut)
def get_public_program(
    merchant_slug: str,
    program_slug: str,
    session: DbSession,
    request: Request,
    _: Annotated[None, Depends(check_public_read_rate)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> PublicProgramOut:
    """Condiciones y recompensas visibles para un cliente potencial."""
    payload = loyalty_service.public_program_payload(session, merchant_slug, program_slug)
    if not payload["enrollment_open"] and settings.is_production:
        # En desarrollo se muestra para poder diseñar la página; en producción
        # un programa no activo no se publica.
        payload["enrollment_open"] = False
    return PublicProgramOut(**payload)  # type: ignore[arg-type]
