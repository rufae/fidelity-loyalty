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
    #: Reservado y aceptado por compatibilidad: el alta pública ya no lo
    #: solicita porque el MVP no tiene canal de envío (§9.6); se reactivará
    #: junto con el canal, su prueba de opt-in y la baja.
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
    #: Condición de caducidad del programa si la define (§7.7): la
    #: tarjeta la muestra junto al saldo para no prometer sellos que
    #: vencerán sin avisar.
    stamps_expire_days: int | None = None
    rewards: list[PublicRewardStatus] = []
    wallet_options: list[str] = []
    simulated_wallet: bool = True
    #: Registro propio del cliente (§2, transparencia): total de visitas y
    #: última. Solo agregados, sin importes ni detalle (§9.3).
    total_visits: int = 0
    last_visit_at: str | None = None
    #: Diseño del comercio (decisión #8): presentación, nunca lógica.
    primary_color: str = "#5b48d6"
    accent_color: str = "#f7bd4b"
    stamp_icon: str = "cup"
    footer_text: str | None = None
    logo_url: str | None = None


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
    #: Tipo del programa (§7.1): para rotular «sellos» o «puntos» en el
    #: mostrador sin cargar el programa entero en cada fila.
    program_type: str | None = None
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
    #: Premio al alcance (mejora «Premio listo»): nombre de la recompensa
    #: más cercana, sellos que faltan y si ya es canjeable ahora. Derivado
    #: siempre del ledger y del catálogo activo del programa, nunca local.
    next_reward_name: str | None = None
    next_reward_remaining: int | None = None
    reward_ready: bool = False


class MembershipPage(BaseModel):
    """Página del listado de tarjetas (§12.1: colecciones paginadas).

    Los contadores globales llegan en la misma respuesta para que la cabecera
    de la pantalla rotule **totales reales** de la base de datos aunque solo
    se pinte una página. `ready` cuenta tarjetas con recompensa activa ya
    alcanzable (insignia «Premio listo»), con el mismo filtro que `items`.
    """

    items: list[MembershipOut]
    total: int
    active: int
    suspended: int
    ready: int


class MemberUpdateIn(BaseModel):
    """Edición de datos mínimos del cliente (decisión de compra #9).

    Solo lo que el comercio necesita corregir: nombre y correo. Cambiar el
    correo lo deja **sin verificar** (ADR-0006): nadie puede apropiarse de la
    identidad verificada de otro solo editando el campo.
    """

    model_config = ConfigDict(extra="forbid")

    display_name: str | None = Field(default=None, min_length=2, max_length=120)
    email: EmailStr | None = None


class ManualEnrollIn(BaseModel):
    """Alta en mostrador (ADR-0006 revisado): email **opcional**.

    El personal da de alta al cliente en el local con datos mínimos. Con el
    email la identidad queda asociada (sin verificar: el cliente podría no
    controlar ese buzón todavía); sin email la tarjeta es recuperable por su
    enlace/código, que solo muestra el mostrador o el propio cliente.
    """

    model_config = ConfigDict(extra="forbid")

    program_id: UUID
    display_name: str = Field(min_length=2, max_length=120)
    email: EmailStr | None = None
    #: Consistencia de consentimientos: misma regla que el alta pública.
    accepted_terms_version: int = Field(ge=1)
    privacy_notice_version: int = Field(ge=1)


class ManualEnrollOut(BaseModel):
    """Resultado del alta en mostrador: tarjeta lista para usar al instante."""

    membership: MembershipOut
    #: False cuando el cliente ya tenía tarjeta en ese programa: se muestra la
    #: suya en lugar de crear una duplicada (idempotencia de mostrador).
    created: bool
