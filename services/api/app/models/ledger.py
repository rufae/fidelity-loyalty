"""Libro de movimientos (ledger) y canjes (AGENTS.md §7.3, §7.4, §11.10, §11.11).

Reglas:
- El saldo **se deriva** del ledger: `membership.stamps` es solo una caché
  reconciliable (§7.3).
- Nunca se edita ni borra un movimiento: los errores se corrigen con
  `adjustment` o `reversal` auditables.
- `idempotency_key` es única: una petición repetida no puede otorgar sellos
  dos veces (§16.4).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.user import utcnow


class TransactionType:
    EARN = "earn"
    REDEEM = "redeem"
    ADJUSTMENT = "adjustment"
    REVERSAL = "reversal"


class LoyaltyTransaction(Base):
    __tablename__ = "loyalty_transactions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    program_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    transaction_type: Mapped[str] = mapped_column(String(20))
    #: Cantidad con signo: `earn` positivo, `redeem` negativo (§7.3).
    quantity: Mapped[int] = mapped_column(Integer)
    reward_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="staff")
    #: Obligatoria en `earn`/`redeem`: única en toda la tabla (§16.4).
    idempotency_key: Mapped[str] = mapped_column(String(120), unique=True)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    related_transaction_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class RewardRedemption(Base):
    __tablename__ = "reward_redemptions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    merchant_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    membership_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    reward_id: Mapped[uuid.UUID] = mapped_column(Uuid, index=True)
    transaction_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("loyalty_transactions.id"))
    status: Mapped[str] = mapped_column(String(20), default="completed")
    redeemed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    redeemed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    notes: Mapped[str | None] = mapped_column(String(255), nullable=True)
