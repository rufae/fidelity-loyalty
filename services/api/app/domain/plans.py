"""Planes comerciales del producto (Plan.md §22, tasks.md §1).

El catálogo vive aquí para que límites y precios tengan **una sola fuente de
verdad** visible también públicamente (la página de precios la sirve la API).
Los precios son la estimación de partida y se pueden revisar; el código no
los trata como constantes de dominio, solo como datos del catálogo.

Reglas de límites (§3.3: nada oculto):
- `max_locations`: tiendas que el comercio puede tener dadas de alta.
- `max_active_programs`: programas de fidelización **en vivo** (activos)
  simultáneos. Los borradores y en pausa no consumen límite.
- `max_staff`: cuentas de **personal** (staff/admin) activas; el propietario
  no cuenta. Los clientes (membresías) son ilimitados en todos los planes:
  el límite es de estructura, no de éxito del comercio.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Plan:
    code: str
    name: str
    tagline: str
    #: Euros al mes (IVA no incluido), facturación mensual.
    price_month_eur: int
    #: Euros al mes con facturación anual (10 meses: 2 gratis).
    price_year_eur: int
    max_locations: int
    max_active_programs: int
    #: Cuentas de personal activas, sin contar al propietario.
    max_staff: int


BASIC = Plan(
    code="basic",
    name="Básico",
    tagline="Un local que empieza con fidelización",
    price_month_eur=19,
    price_year_eur=190,
    max_locations=1,
    max_active_programs=1,
    max_staff=2,
)

PLUS = Plan(
    code="plus",
    name="Plus",
    tagline="Varias tiendas o varios programas",
    price_month_eur=45,
    price_year_eur=450,
    max_locations=3,
    max_active_programs=3,
    max_staff=6,
)

MAX = Plan(
    code="max",
    name="Max",
    tagline="Grupos y franquicias",
    price_month_eur=95,
    price_year_eur=950,
    max_locations=10,
    max_active_programs=6,
    max_staff=15,
)

BY_CODE: dict[str, Plan] = {p.code: p for p in (BASIC, PLUS, MAX)}
DEFAULT_CODE = BASIC.code


def get(code: str | None) -> Plan:
    """Plan por código; desconocido → Básico (fail-soft, §26.3)."""
    return BY_CODE.get(code or DEFAULT_CODE, BY_CODE[DEFAULT_CODE])


def catalog() -> list[Plan]:
    """Planes en orden de presentación (de menor a mayor)."""
    return [BASIC, PLUS, MAX]
