"""Servicio de auditoría (§8.4): registra acciones sensibles sin PII extra."""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent

#: Lista permitida de claves que pueden entrar en `metadata` (§16.6).
METADATA_ALLOWLIST = frozenset(
    {"role", "previous_status", "new_status", "reason", "fields", "email_hash", "term_hash"}
)


def record_audit(
    session: Session,
    *,
    action: str,
    entity_type: str,
    actor_type: str = "user",
    actor_id: uuid.UUID | None = None,
    merchant_id: uuid.UUID | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> AuditEvent:
    """Añade un evento de auditoría. El filtrado de claves es exhaustivo."""
    safe_metadata = {k: v for k, v in (metadata or {}).items() if k in METADATA_ALLOWLIST}
    event = AuditEvent(
        merchant_id=merchant_id,
        actor_type=actor_type,
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        metadata_json=safe_metadata,
    )
    session.add(event)
    return event
