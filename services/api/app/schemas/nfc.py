"""Esquemas de etiquetas NFC/QR y destinos de reseñas (§12.8).

`extra="forbid"` es intencionado en la creación de etiquetas: un campo como
`reward_id` o `incentive` en una etiqueta de reseñas debe ser un **error**, no
un dato ignorado (§4.2: ninguna vinculación recompensa↔reseña).
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ReviewDestinationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    review_url: str = Field(min_length=10, max_length=500)


class ReviewDestinationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    provider: str
    review_url: str
    verification_status: str
    verified_at: datetime | None = None
    updated_at: datetime


class NfcTagCreate(BaseModel):
    """Alta de etiqueta. Sin campos de incentivo: no existe esa opción (§4.2)."""

    model_config = ConfigDict(extra="forbid")

    tag_type: str = Field(pattern="^(loyalty_signup|google_review|counter|member_card_access)$")
    label: str | None = Field(default=None, max_length=120)
    #: Para `loyalty_signup` y `counter`: programa al que se asocia la etiqueta.
    program_id: UUID | None = None


class NfcTagUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, max_length=120)
    status: str | None = Field(default=None, pattern="^(active|disabled)$")


class NfcTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tag_type: str
    public_slug: str
    status: str
    label: str | None = None
    destination_url: str | None = None
    #: URL **absoluta** que se escribe en la etiqueta NFC y se imprime en el QR.
    short_url: str | None = None
    created_at: datetime
    updated_at: datetime


class NfcStatsOut(BaseModel):
    """Métricas nombradas con precisión (§4.4, §12.9): clics, no reseñas.

    `counter_clicks` son **usos del atajo de mostrador** por el personal:
    informan de la adopción, no de la actividad de los clientes.
    """

    loyalty_signup_clicks: int = 0
    review_link_clicks: int = 0
    counter_clicks: int = 0
    member_card_access_clicks: int = 0
    total_clicks: int = 0
    tags_active: int = 0
