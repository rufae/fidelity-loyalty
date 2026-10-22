"""Esquemas de programas y recompensas (§12.4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    terms: str | None = Field(default=None, max_length=4000)
    program_type: str = Field(default="stamps", pattern="^stamps$")


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    terms: str | None = Field(default=None, max_length=4000)


class RewardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    stamps_required: int = Field(gt=0, le=100)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("el nombre no puede estar vacío")
        return stripped


class RewardUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    stamps_required: int | None = Field(default=None, gt=0, le=100)
    status: str | None = Field(default=None, pattern="^(active|inactive)$")


class RewardOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    program_id: UUID
    name: str
    description: str | None = None
    stamps_required: int
    status: str
    created_at: datetime
    updated_at: datetime


class ProgramOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    name: str
    slug: str
    program_type: str
    description: str | None = None
    terms: str | None = None
    terms_version: int
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class ProgramDetailOut(ProgramOut):
    rewards: list[RewardOut] = []


class PublicRewardOut(BaseModel):
    """Lo mínimo visible para un cliente potencial (sin IDs internos)."""

    name: str
    description: str | None = None
    stamps_required: int


class PublicProgramOut(BaseModel):
    """Datos públicos de la página de alta (§13.4): sin datos privados."""

    merchant_name: str
    merchant_slug: str
    program_name: str
    program_slug: str
    program_type: str
    description: str | None = None
    terms: str | None = None
    terms_version: int
    rewards: list[PublicRewardOut] = []
    enrollment_open: bool
    #: Versión del aviso de privacidad que se muestra en el alta (ADR-0006).
    privacy_notice_version: int = 1
