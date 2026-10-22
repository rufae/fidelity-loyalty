"""Logging de proceso y correlation ID por petición (AGENTS.md §12.1, §16.6)."""

import logging
import sys
import uuid
from contextvars import ContextVar

# correlation id visible en todos los logs de la petición y en la respuesta.
request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


def configure_logging(level: str) -> None:
    """Formato único `mensaje clave=valor` para poder filtrar en el servidor."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s %(args)s")
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


def new_request_id(incoming: str | None) -> str:
    """Reutiliza la cabecera entrante si es saneable; si no, genera una nueva.

    No se confía en el valor del cliente tal cual: se limita en longitud y
    caracteres para que no contamine los logs.
    """
    if incoming:
        cleaned = "".join(ch for ch in incoming if ch.isalnum() or ch in "-_")[:64]
        if cleaned:
            return cleaned
    return uuid.uuid4().hex
