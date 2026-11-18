"""Esquemas del módulo de soporte B2B (Plan.md §8–§9).

Los datos de entrada usan `extra="forbid"`: un campo desconocido debe ser un
error, no algo que el backend guarde sin querer. El teléfono de llamada solo
se acepta con consentimiento explícito y nunca se devuelve al comercio.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

_CATEGORY_PATTERN = "^(technical|billing|program|nfc|wallet|other)$"
_CONTACT_PATTERN = "^(in_app|email|phone)$"
_STATUS_PATTERN = "^(open|waiting_platform|waiting_merchant|resolved|closed)$"
_PRIORITY_PATTERN = "^(normal|high)$"
_CALLBACK_STATUS_PATTERN = "^(requested|called|cancelled)$"
_PHONE_PATTERN = r"^\+?[0-9][0-9 ().-]{5,31}$"


class SupportThreadCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str = Field(min_length=3, max_length=120)
    category: str = Field(default="other", pattern=_CATEGORY_PATTERN)
    body: str = Field(min_length=1, max_length=4000)
    preferred_contact: str = Field(default="in_app", pattern=_CONTACT_PATTERN)
    callback_phone: str | None = Field(
        default=None, min_length=6, max_length=32, pattern=_PHONE_PATTERN
    )
    callback_availability: str | None = Field(default=None, max_length=160)
    callback_consent: bool = False

    @model_validator(mode="after")
    def _callback_requires_consent(self) -> "SupportThreadCreate":
        if self.callback_phone and not self.callback_consent:
            raise ValueError("callback_consent es obligatorio para solicitar una llamada")
        return self


class SupportMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    body: str = Field(min_length=1, max_length=4000)


class SupportCallbackRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    phone: str = Field(min_length=6, max_length=32, pattern=_PHONE_PATTERN)
    availability: str | None = Field(default=None, max_length=160)
    consent: bool = False

    @model_validator(mode="after")
    def _consent_required(self) -> "SupportCallbackRequestCreate":
        if not self.consent:
            raise ValueError("consent es obligatorio para solicitar una llamada")
        return self


class SupportThreadUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str | None = Field(default=None, pattern=_STATUS_PATTERN)
    priority: str | None = Field(default=None, pattern=_PRIORITY_PATTERN)


class SupportCallbackRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: str
    availability: str | None = None
    requested_at: datetime
    handled_at: datetime | None = None
    #: Solo la administración de plataforma recibe el teléfono (§12.2).
    phone: str | None = None


class SupportMessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    thread_id: UUID
    author_type: str
    author_user_id: UUID | None = None
    author_display_name: str
    body: str
    created_at: datetime
    read_by_merchant_at: datetime | None = None
    read_by_platform_at: datetime | None = None


class SupportThreadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    merchant_name: str | None = None
    created_by_user_id: UUID
    created_by_display_name: str
    subject: str
    category: str
    status: str
    priority: str
    preferred_contact: str
    last_message_at: datetime
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    unread_for_viewer: int = 0
    has_callback_request: bool = False


class SupportThreadDetailOut(SupportThreadOut):
    messages: list[SupportMessageOut] = Field(default_factory=list)
    callback_request: SupportCallbackRequestOut | None = None
    notifications: list["SupportNotificationOut"] = Field(default_factory=list)


class SupportNotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    channel: str
    status: str
    attempts: int
    manual_retries: int
    next_attempt_at: datetime | None = None
    error_code: str | None = None
    sent_at: datetime | None = None
    created_at: datetime


class SupportThreadPageOut(BaseModel):
    items: list[SupportThreadOut]
    total: int
    limit: int
    offset: int


class SupportUnreadOut(BaseModel):
    count: int


class SupportNotificationTopicOut(BaseModel):
    """Tema ntfy del comercio (avisos push de soporte, Plan.md §11.3).

    `server_url` solo se entrega si el servidor está **publicado**
    (`SUPPORT_NTFY_PUBLIC_URL`): sin él, el comercio no puede suscribirse
    desde su móvil y la interfaz lo dice sin prometer.
    """

    topic: str
    server_url: str | None = None
