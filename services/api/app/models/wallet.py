"""Pases Wallet y trabajos en segundo plano (§11.9, §11.18, §15).

- `wallet_passes`: estado del pase **por proveedor**, separado del estado del
  programa (§11.19). Los metadatos no guardan secretos ni tokens.
- `background_jobs`: emisión/actualización como trabajo con estado, reintentos
  limitados y error visible en el panel (§15). Ninguna llamada externa lenta
  se hace dentro de una petición web.
"""

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, Integer, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class JobStatus:
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    #: Recuperable: esperando la próxima tentativa (backoff, §15).
    RETRYING = "retrying"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WalletPass(Base):
    __tablename__ = "wallet_passes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    provider: Mapped[str] = mapped_column(String(20))
    provider_object_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending")
    #: `true` si el pase es ficticio (proveedor simulado, §17.2).
    simulated: Mapped[int] = mapped_column(Integer, default=1)
    last_issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    last_error_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    #: Metadatos no sensibles del proveedor (§6.4): para Apple guarda el
    #: `authentication_token` del servicio web de actualización. Nunca se
    #: expone en la API del comercio ni llega al frontend.
    provider_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PassDeviceRegistration(Base):
    """Dispositivo registrado para recibir pases actualizados (PassKit §6.4).

    Un pase solo se actualiza si el dispositivo está registrado; el backend
    responde a las consultas de Apple y sirve el pase reconstruido con el
    saldo real del ledger.
    """

    __tablename__ = "pass_device_registrations"
    __table_args__ = (UniqueConstraint("device_id", "serial", name="uq_pass_device_serial"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[str] = mapped_column(String(120), index=True)
    pass_type_id: Mapped[str] = mapped_column(String(120))
    serial: Mapped[str] = mapped_column(String(64), index=True)
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    push_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class BackgroundJob(Base):
    __tablename__ = "background_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_type: Mapped[str] = mapped_column(String(40), index=True)
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default=JobStatus.QUEUED)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    #: Reintentos con backoff (§15): cuándo vuelve a intentarse un fallo
    #: recuperable antes de pasar a dead-letter (`failed`).
    next_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    #: Reintentos manuales desde el panel (§15, corrección de la auditoría):
    # separados de `attempts` para no perder la señal de observabilidad.
    manual_retries: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(120), nullable=True, unique=True)
    error_code: Mapped[str | None] = mapped_column(String(60), nullable=True)
    error_detail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
