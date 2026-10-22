"""Worker de trabajos Wallet (§15).

Hilo único que retoma los `background_jobs` en `queued`/`retrying` cuando
llega su `next_attempt_at`. Es **opt-in** (`WALLET_WORKER_ENABLED=true` en el
despliegue): las pruebas lo tienen apagado y ejecutan `run_due_jobs` de forma
explícita. Sin Redis ni Celery: PostgreSQL + un hilo bastan para un proceso
(ADR/limitación documentada en `docs/ARCHITECTURE.md`).
"""

import logging
import threading

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import get_engine
from app.services.wallet import run_due_jobs

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None


def _loop(settings: Settings) -> None:
    from datetime import timedelta  # noqa: F401  (evita import circular en arranque)

    while not _stop.is_set():
        try:
            with Session(bind=get_engine()) as session:
                processed = run_due_jobs(session, settings)
                session.commit()
            if processed:
                logger.info("wallet worker: %d trabajos procesados", processed)
        except Exception:  # noqa: BLE001 — el worker nunca debe morir
            logger.exception("wallet worker: error procesando trabajos")
        _stop.wait(settings.wallet_worker_poll_seconds)


def start_wallet_worker(settings: Settings) -> None:
    """Arranca el hilo worker una sola vez (idempotente)."""
    global _thread
    if not settings.wallet_worker_enabled or (_thread is not None and _thread.is_alive()):
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, args=(settings,), name="wallet-worker", daemon=True)
    _thread.start()
    logger.info("wallet worker: iniciado (cada %ss)", settings.wallet_worker_poll_seconds)


def stop_wallet_worker() -> None:
    _stop.set()
