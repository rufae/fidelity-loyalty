"""Esquemas Pydantic de comercios (§12.2, §11.2)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.roles import MerchantRole, MerchantStatus


class MerchantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    legal_name: str | None = Field(default=None, max_length=160)
    timezone: str = Field(default="Europe/Madrid", max_length=60)
    country_code: str = Field(default="ES", min_length=2, max_length=2)
    default_locale: str = Field(default="es", max_length=10)
    #: email y contraseña del propietario; solo se usa si el usuario no existe.
    owner_email: EmailStr
    owner_password: str = Field(min_length=12, max_length=256)
    owner_display_name: str = Field(default="Propietario", max_length=120)


class MerchantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    legal_name: str | None = Field(default=None, max_length=160)
    timezone: str | None = Field(default=None, max_length=60)


class MerchantPlanUpdate(BaseModel):
    """Asignación de plan: solo la administración de plataforma (§22)."""

    plan: str = Field(pattern="^(basic|plus|max)$")


class MerchantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    legal_name: str | None = None
    status: MerchantStatus
    timezone: str
    country_code: str
    default_locale: str
    plan: str = "basic"
    created_at: datetime
    updated_at: datetime


class LocationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str | None = Field(default=None, max_length=255)


class LocationStatusUpdate(BaseModel):
    status: str = Field(pattern="^(active|inactive)$")


class LocationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    address: str | None = None
    status: str
    created_at: datetime


class PlanUsageOut(BaseModel):
    """Uso real del plan del comercio: cifras de la base de datos."""

    plan: str
    plan_name: str
    max_locations: int
    locations: int
    max_active_programs: int
    active_programs: int
    max_staff: int
    staff: int


class MerchantUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    display_name: str = Field(max_length=120, default="Usuario")
    role: MerchantRole


class MerchantUserUpdate(BaseModel):
    role: MerchantRole | None = None
    status: str | None = None
    display_name: str | None = Field(default=None, max_length=120)


class MerchantUserOut(BaseModel):
    id: UUID
    user_id: UUID
    email: str
    display_name: str
    role: MerchantRole
    status: str
    created_at: datetime
