"""Esquemas Pydantic de autenticación (§12.3)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.domain.roles import MerchantRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class PasswordChangeRequest(BaseModel):
    """Cambio de contraseña del usuario autenticado (§8.3)."""

    current_password: str = Field(min_length=1, max_length=256)
    # Requisito mínimo común: 10 caracteres; el hash Argon2id hace el resto.
    new_password: str = Field(min_length=10, max_length=256)


class MerchantMembership(BaseModel):
    """Pertenece a la respuesta de sesión: el navegador nunca la envía como prueba."""

    merchant_id: UUID
    merchant_name: str
    merchant_slug: str
    merchant_status: str
    role: MerchantRole


class SessionUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    display_name: str
    platform_role: str | None = None
    last_login_at: datetime | None = None


class SessionPayload(BaseModel):
    """Respuesta de `/auth/login` y `/auth/me` (nunca incluye hashes ni tokens)."""

    user: SessionUser
    merchants: list[MerchantMembership] = []
