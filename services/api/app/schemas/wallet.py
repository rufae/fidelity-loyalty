"""Esquemas de Wallet (§12.6, §15)."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PassOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    status: str
    simulated: bool
    provider_object_id: str | None = None
    last_error_code: str | None = None
    last_error_detail: str | None = None
    job_id: uuid.UUID | None = None
    job_status: str | None = None


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_type: str
    status: str
    attempts: int
    error_code: str | None = None
    error_detail: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
