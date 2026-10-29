"""Factory de la aplicación FastAPI (AGENTS.md §10.3, §12.1)."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.responses import Response as StarletteResponse

from app.api.health import router as health_router
from app.api.router import api_router, public_router
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging, new_request_id, request_id_var
from app.db.session import get_session
from app.services.auth import bootstrap_platform_owner

logger = logging.getLogger(__name__)

# Cabeceras mínimas de navegador (§16.7). La CSP completa y el resto del
# checklist llegan en la FASE 12; aquí se sienta la costumbre desde el día 1.
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cache-Control": "no-store",
    # HSTS (§16.7): sin TLS válido el navegador podría degradar a HTTP en la
    # primera visita. Dos años con subdominios, como recomienda OWASP.
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains",
}

#: Mutaciones que aceptan cuerpo vacío (acción idempotente sin payload).
JSON_EXEMPT_PATHS = frozenset({"/api/v1/auth/logout"})

#: Rutas del servicio web de Apple (PassKit, §6.4): Apple no envía
#: `Content-Type` en todas sus peticiones ni `Origin` (no es un navegador).
PASSKIT_PREFIXES = ("/api/v1/devices/", "/api/v1/passes/", "/api/v1/log")


def _origin_allowed(origin: str, request: Request, settings: Settings) -> bool:
    """¿El `Origin` de la petición coincide con el host servido? (§16.2)."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(origin)
    except ValueError:
        return False
    if not parsed.netloc:
        return False
    host = (request.headers.get("host") or request.url.netloc or "").lower()
    forwarded = (request.headers.get("x-forwarded-host") or "").lower()
    base = (settings.public_base_url or "").strip()
    allowed = {host, forwarded}
    if base:
        allowed.add(urlparse(base).netloc.lower())
    if parsed.netloc.lower() in allowed:
        # En producción no se admite degradar a HTTP aunque el host coincida.
        return not (settings.is_production and parsed.scheme != "https")
    # Desarrollo sin `PUBLIC_BASE_URL`: el proxy interno de Next reescribe el
    # Host y no hay dominio público que proteger. Un origen bucle-local (el
    # que usa `npm run dev` y las E2E) se admite solo fuera de producción.
    return (
        not base
        and not settings.is_production
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    )


def _bootstrap_users() -> None:
    """Semilla idempotente del primer administrador (§8.3, sin admin/admin)."""
    settings = get_settings()
    if not settings.bootstrap_configured:
        logger.warning(
            "sin_usuarios_semilla "
            "configura AUTH_BOOTSTRAP_EMAIL y AUTH_BOOTSTRAP_PASSWORD para crear "
            "el primer administrador de plataforma"
        )
        return
    from sqlalchemy.exc import SQLAlchemyError

    session = next(get_session())
    try:
        created = bootstrap_platform_owner(session, settings)
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        logger.exception("bootstrap_fallido")
        return
    finally:
        session.close()
    if created:
        logger.info("administrador_inicial_creado")


def _start_wallet_worker() -> None:
    """Arranca el worker de trabajos Wallet si está habilitado (§15)."""
    from app.workers.runner import start_wallet_worker

    start_wallet_worker(get_settings())


def _start_support_worker() -> None:
    """Arranca el worker de avisos de soporte si está habilitado (Plan.md §11)."""
    from app.workers.support_runner import start_support_worker

    start_support_worker(get_settings())


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    # Documentación OpenAPI: solo fuera de producción (§12.1 y §16.2).
    expose_docs = not settings.is_production
    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "API de LocalAI Fidelity: programas de fidelización, tarjetas Wallet, "
            "etiquetas NFC/QR y enlaces de reseñas. "
            + ("Documentación OpenAPI en `/docs`." if expose_docs else "")
        ),
        openapi_url=f"{settings.api_prefix}/openapi.json" if expose_docs else None,
        docs_url="/docs" if expose_docs else None,
        redoc_url="/redoc" if expose_docs else None,
        on_startup=[_bootstrap_users, _start_wallet_worker, _start_support_worker],
    )

    @application.middleware("http")
    async def correlation_and_headers(
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        """Correlation ID por petición + cabeceras de seguridad en toda respuesta."""
        request_id = new_request_id(request.headers.get("X-Request-ID"))
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        return response

    @application.middleware("http")
    async def require_json_body(
        request: Request,
        call_next: Callable[[Request], Awaitable[StarletteResponse]],
    ) -> StarletteResponse:
        """Defensa en profundidad anti-CSRF (§16.2, corrección de la auditoría).

        La cookie es `SameSite=Lax`, así que un formulario cruzado ya no envía
        sesión. Este middleware añade dos capas:

        1. **Origen**: si la petición trae `Origin` y no coincide con el host
           servido (ni con `PUBLIC_BASE_URL`), se rechaza con 403. Cubre
           navegadores sin SameSite y peticiones same-site de subdominios.
        2. **JSON obligatorio** en las mutaciones, con o sin cuerpo: un
           `<form>` HTML no puede mute la API ni siquiera sin payload.
        """
        if request.method in {"POST", "PUT", "PATCH", "DELETE"} and (
            request.url.path.startswith("/api/v1") or request.url.path.startswith("/go/")
        ):
            settings = get_settings()
            origin = request.headers.get("origin")
            if origin and not _origin_allowed(origin, request, settings):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "origin_not_allowed",
                            "message": "Origen no permitido",
                            "request_id": getattr(request.state, "request_id", "-"),
                        }
                    },
                )
            # Hay cuerpo si trae `Content-Length` o `Transfer-Encoding:
            # chunked` (así un `<form>` con cuerpo no puede colarse sin
            # `application/json`; las acciones sin payload siguen pasando).
            has_body = (
                request.headers.get("content-length")
                not in (
                    None,
                    "0",
                )
                or "chunked" in request.headers.get("transfer-encoding", "").lower()
            )
            if (
                request.method in {"POST", "PUT", "PATCH"}
                and request.url.path.startswith("/api/v1")
                and request.url.path not in JSON_EXEMPT_PATHS
                and not request.url.path.startswith(PASSKIT_PREFIXES)
                and has_body
            ):
                content_type = request.headers.get("content-type", "")
                if "application/json" not in content_type:
                    return JSONResponse(
                        status_code=415,
                        content={
                            "error": {
                                "code": "unsupported_media_type",
                                "message": "Las mutaciones de la API requieren application/json",
                                "request_id": getattr(request.state, "request_id", "-"),
                            }
                        },
                    )
        return await call_next(request)

    @application.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:
        """Nunca se expone un stack trace al cliente (§12.1, §23)."""
        request_id = getattr(request.state, "request_id", "-")
        logger.exception("unhandled_error request_id=%s", request_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "internal_error",
                    "message": "Error interno del servidor",
                    "request_id": request_id,
                }
            },
        )

    # Salud sin prefijo (healthchecks de Docker) + API versionada.
    application.include_router(health_router)
    application.include_router(api_router, prefix=settings.api_prefix)
    # /go/{slug} en la raíz: es la URL que lleva impresa la etiqueta NFC (§12.8).
    application.include_router(public_router)

    logger.info(
        "application_started environment=%s version=%s wallet_provider=%s",
        settings.app_env,
        settings.app_version,
        settings.wallet_provider,
    )
    return application


app = create_app()
