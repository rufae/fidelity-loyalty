"""Esquemas de miembros y membresías (§12.5, §13.4)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EnrollRequest(BaseModel):
    """Alta pública (ADR-0006): nombre completo y email obligatorios.

    El marketing sigue siendo **opcional** y separado del alta (§9.4); el
    aviso de privacidad se acepta con su versión y queda registrado.
    """

    email: EmailStr
    display_name: str = Field(min_length=2, max_length=120)
    #: Versión de las condiciones que el cliente acepta (visible en la página).
    accepted_terms_version: int = Field(ge=1)
    #: Versión del aviso de privacidad mostrado en el alta (ADR-0006).
    privacy_notice_version: int = Field(ge=1)
    #: Consentimiento de comunicaciones: **opcional** y separado del alta (§9.4).
    marketing_consent: bool = False


class EnrollResponse(BaseModel):
    """Confirmación que no revela si el correo ya existía."""

    message: str


class EmailActionIn(BaseModel):
    token: str = Field(min_length=32, max_length=128)


class CardAccessRequest(BaseModel):
    email: EmailStr


class CardAccessOut(BaseModel):
    token: str
    merchant_name: str
    merchant_slug: str
    program_id: str
    program_name: str
    stamps: int


class PublicRewardStatus(BaseModel):
    name: str
    stamps_required: int
    earned: bool


class PublicMembershipOut(BaseModel):
    """Tarjeta web del cliente (fallback sin Wallet, §6.7)."""

    merchant_name: str
    program_name: str
    program_type: str
    stamps: int
    status: str
    rewards: list[PublicRewardStatus] = []
    wallet_options: list[str] = []
    simulated_wallet: bool = True


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str | None = None
    display_name: str | None = None
    status: str
    created_at: datetime


class MembershipOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    member_id: UUID
    program_id: UUID
    public_token: str
    status: str
    stamps: int
    joined_at: datetime
    #: Nombre del programa: permite elegir la promoción correcta en el
    #: mostrador cuando el cliente tiene más de una tarjeta (§13.5).
    program_name: str | None = None
    #: Identidad mínima del cliente para buscarlo en el mostrador (§13.5:
    # permiso + auditoría). Nunca viaja en rutas públicas ni en el QR.
    member_name: str | None = None
    member_email: str | None = None
    #: Ciclo de vida (ADR-0005): motivo y fecha del último cambio de estado.
    status_reason: str | None = None
    status_changed_at: datetime | None = None
    deletion_requested_at: datetime | None = None
    anonymized_at: datetime | None = None
