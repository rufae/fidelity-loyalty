"""Worker de avisos de soporte (Plan.md §11.6).

Hilo único y opt-in (`SUPPORT_WORKER_ENABLED=true`) que procesa el outbox de
`support_notifications` con reintentos. Al igual que el worker de Wallet, no
usa Redis ni Celery: PostgreSQL + un hilo bastan, y la reclamación de cada
aviso se hace con un `UPDATE` condicional para que varios nodos no lo envíen
dos veces.
"""

import logging
import threading

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_engine
from app.services.support_notifications import run_due_notifications

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None


def _loop(settings: Settings) -> None:
    while not _stop.is_set():
        try:
            with Session(bind=get_engine()) as session:
                processed = run_due_notifications(session, settings)
                session.commit()
            if processed:
                logger.info("support worker: %d avisos procesados", processed)
        except Exception:  # noqa: BLE001 — el worker nunca debe morir
            logger.exception("support worker: error procesando avisos")
        _stop.wait(settings.support_worker_poll_seconds)


def start_support_worker(settings: Settings) -> None:
    global _thread
    if not settings.support_worker_enabled or (_thread is not None and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(settings,), name="support-worker", daemon=True)
    _thread.start()
    logger.info("support worker: iniciado (cada %ss)", settings.support_worker_poll_seconds)


def stop_support_worker() -> None:
    _stop.set()
