"""Esquemas de programas y recompensas (§12.4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.notices import PRIVACY_NOTICE_VERSION


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    terms: str | None = Field(default=None, max_length=4000)
    #: Sellos por visita o puntos por importe (§7.1, mejora de compra #9).
    program_type: str = Field(default="stamps", pattern="^(stamps|points)$")
    #: Caducidad opcional de sellos (§7.7): días hasta vencer; sin regla
    #: por defecto. Se muestra en el alta y en la tarjeta (§13.4).
    stamps_expire_days: int | None = Field(default=None, ge=1, le=3650)
    #: Regla del modo puntos (§7.6): puntos enteros por euro, redondeo
    #: hacia abajo en el backend. Obligatoria al publicar (no al crear).
    points_per_euro: int | None = Field(default=None, ge=1, le=1000)


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    terms: str | None = Field(default=None, max_length=4000)
    #: `null` explícito retira la regla; omitido la deja intacta (solo
    #: afecta a los `earn` futuros: los lotes emitidos conservan su fecha).
    stamps_expire_days: int | None = Field(default=None, ge=1, le=3650)
    points_per_euro: int | None = Field(default=None, ge=1, le=1000)


class RewardCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    #: Coste en sellos (modo stamps) o puntos (modo points). El tope deja
    #: margen a programas de puntos por importe sin permitir absurdos.
    stamps_required: int = Field(gt=0, le=10000)

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
    stamps_required: int | None = Field(default=None, gt=0, le=10000)
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
    #: Versión vigente del aviso de privacidad: el alta en mostrador la
    #: registra con el consentimiento del cliente (ADR-0006, §9.4).
    privacy_notice_version: int = PRIVACY_NOTICE_VERSION
    status: str
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    #: Regla opcional de caducidad (§7.7): días hasta vencer; `None` = sin
    #: caducidad. Visible para que el comercio sepa qué está ofreciendo.
    stamps_expire_days: int | None = None
    #: Regla del modo puntos (§7.6): puntos por euro (`None` = sin regla
    #: o programa de sellos).
    points_per_euro: int | None = None


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
    #: Caducidad de sellos si el comercio la define: la página de alta y
    #: la tarjeta la comunican antes del registro (§7.7, §13.4).
    stamps_expire_days: int | None = None
    #: Regla de puntos por euro si el programa es de puntos (§7.6): la
    #: página de alta la explica antes de registrar al cliente.
    points_per_euro: int | None = None
