"""Ruta corta pública `/go/{public_slug}` (§12.8, §4.4).

Comportamiento (obligatorio):
- Resuelve **solo** al destino guardado del tag: nunca acepta `?url=` ni
  ningún parámetro de destino (sin *open redirect*).
- Ignora los parámetros de la petición: no hay filtro por satisfacción,
  historial ni identidad (§4.2).
- Una etiqueta desactivada responde `410` con una página neutral, sin
  redirigir (§14.3).
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from starlette.responses import Response

from app.api.deps import DbSession
from app.domain.errors import DomainError
from app.services import nfc as nfc_service

router = APIRouter(tags=["redirect"])

_DISABLED_PAGE = """<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Etiqueta desactivada</title></head>
<body style="font-family: system-ui, sans-serif; margin: 3rem; color:#334155">
  <h1>Esta etiqueta está desactivada</h1>
  <p>El propietario del establecimiento ha desactivado este enlace.</p>
</body></html>"""


@router.get("/go/{public_slug}", response_class=Response)
def go(public_slug: str, request: Request, session: DbSession) -> Response:  # noqa: ARG001
    """Abre el destino del tag y registra el clic como métrica mínima."""
    try:
        _tag, url = nfc_service.resolve_redirect(session, public_slug)
    except DomainError as exc:
        if exc.code == "tag_disabled":
            # §14.3: página neutral en lugar de redirigir.
            return HTMLResponse(_DISABLED_PAGE, status_code=410)
        raise
    session.commit()
    # 302: el navegador muestra el destino real del comercio (§4.4).
    return RedirectResponse(url=url, status_code=302)
