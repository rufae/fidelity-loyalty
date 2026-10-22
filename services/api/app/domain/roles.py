"""Roles y permisos (AGENTS.md §8).

Regla de oro §8.2: la autorización se calcula **siempre** en backend a partir
de la sesión del usuario; nunca se confía en un `merchant_id` o `role`
enviado por el navegador.
"""

from enum import StrEnum
from typing import Final


class PlatformRole(StrEnum):
    """Administración global de la plataforma (§8.1)."""

    OWNER = "owner"
    ADMIN = "admin"


class MerchantRole(StrEnum):
    """Rol dentro de un comercio concreto (§8.1)."""

    OWNER = "owner"
    ADMIN = "admin"
    STAFF = "staff"
    VIEWER = "viewer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class MerchantStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"


#: Roles de comercio que pueden administrarlo (usuarios, programa, reseñas).
MERCHANT_ADMIN_ROLES: Final[frozenset[MerchantRole]] = frozenset(
    {MerchantRole.OWNER, MerchantRole.ADMIN}
)

#: Roles de comercio que pueden leer su información.
MERCHANT_READ_ROLES: Final[frozenset[MerchantRole]] = MERCHANT_ADMIN_ROLES | frozenset(
    {MerchantRole.STAFF, MerchantRole.VIEWER}
)

#: Roles que pueden operar tarjetas (acumular, canjear) — §8.1.
MERCHANT_OPERATOR_ROLES: Final[frozenset[MerchantRole]] = MERCHANT_ADMIN_ROLES | frozenset(
    {MerchantRole.STAFF}
)

MERCHANT_ROLE_VALUES: Final[frozenset[str]] = frozenset(role.value for role in MerchantRole)
PLATFORM_ROLE_VALUES: Final[frozenset[str]] = frozenset(role.value for role in PlatformRole)

#: Orden de jerarquía de roles de comercio, de menor a mayor rango (§8.1).
MERCHANT_ROLE_ORDER: Final[tuple[MerchantRole, ...]] = (
    MerchantRole.VIEWER,
    MerchantRole.STAFF,
    MerchantRole.ADMIN,
    MerchantRole.OWNER,
)


def role_rank(role: MerchantRole) -> int:
    """Rango numérico del rol: mayor = más privilegios (§8.1)."""
    return MERCHANT_ROLE_ORDER.index(role)
