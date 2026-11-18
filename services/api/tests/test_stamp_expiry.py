"""Caducidad opcional de sellos (decisión de compra #6, §7.7).

La regla es opcional, por programa y solo afecta a los `earn` futuros. El
vencimiento se materializa como un movimiento `expiry` auditable — el
`earn` histórico no se edita — y se aplica de forma perezosa antes de
operar y al leer las fichas, de modo que no se puede canjear con sellos
ya caducados.
"""

from datetime import UTC, datetime, timedelta

from app.domain.roles import MerchantRole
from app.models.ledger import LoyaltyTransaction, TransactionType
from app.models.user import utcnow
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_EMAIL,
    STAFF_EMAIL,
    add_member,
    create_merchant_with_owner,
    create_user,
    enroll_verified,
    login,
)
from .test_ledger import TERMS, _membership


def _world_with_rule(
    client: TestClient, db_session: Session, *, days: int | None = 30
) -> tuple[str, str, str, str]:
    """Comercio con programa (10 sellos = barra) y cliente registrado.

    Devuelve `(merchant_id, program_id, reward_id, public_token)`.
    """
    owner = create_user(db_session, OWNER_EMAIL)
    staff = create_user(db_session, STAFF_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Panaderia Central")
    add_member(db_session, staff, merchant, MerchantRole.STAFF)
    db_session.commit()
    login(client, OWNER_EMAIL)
    body: dict[str, object] = {"name": "Club del Pan", "terms": TERMS}
    if days is not None:
        body["stamps_expire_days"] = days
    program = client.post(f"/api/v1/merchants/{merchant.id}/programs", json=body).json()
    reward = client.post(
        f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/rewards",
        json={"name": "Barra gratis", "stamps_required": 10},
    ).json()
    client.post(f"/api/v1/merchants/{merchant.id}/programs/{program['id']}/publish")
    client.post("/api/v1/auth/logout")
    _, token = enroll_verified(
        client,
        db_session,
        merchant.slug,
        program["slug"],
        {
            "email": "cliente-caducidad@example.com",
            "display_name": "Cliente Caducidad",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    client.post("/api/v1/auth/logout")
    return str(merchant.id), str(program["id"]), str(reward["id"]), token


def _earn(client: TestClient, merchant_id: str, membership_id: str, key: str) -> None:
    login(client, STAFF_EMAIL)
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn",
        json={"quantity": 5, "idempotency_key": key},
    )
    assert response.status_code == 201, response.text
    client.post("/api/v1/auth/logout")


def _make_due(db_session: Session, membership_id: object) -> None:
    """Anticipo el vencimiento del lote más reciente (sin viajar en el tiempo)."""
    tx = db_session.scalars(
        select(LoyaltyTransaction)
        .where(
            LoyaltyTransaction.membership_id == membership_id,
            LoyaltyTransaction.transaction_type == TransactionType.EARN,
        )
        .order_by(LoyaltyTransaction.created_at.desc())
    ).first()
    assert tx is not None and tx.expires_at is not None
    tx.expires_at = utcnow() - timedelta(days=1)
    db_session.commit()


def _as_utc(value: datetime) -> datetime:
    """SQLite guarda sin zona horaria (§11.19): se interpreta como UTC."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def test_la_regla_de_caducidad_es_opcional_y_validada(
    client: TestClient, db_session: Session
) -> None:
    """Se puede crear con regla, sin regla y con valores fuera de rango."""
    owner = create_user(db_session, OWNER_EMAIL)
    merchant = create_merchant_with_owner(db_session, owner, name="Tienda Opcion")
    db_session.commit()
    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant.id}/programs"

    sin_regla = client.post(url, json={"name": "Sin regla", "terms": TERMS}).json()
    assert sin_regla["stamps_expire_days"] is None

    con_regla = client.post(
        url, json={"name": "Con regla", "terms": TERMS, "stamps_expire_days": 30}
    ).json()
    assert con_regla["stamps_expire_days"] == 30

    # Rangos duros (1..3650 días): ni un cero que no caduca nada ni un
    # plazo absurdo que el comercio no podrá explicar al cliente (§7.7).
    assert (
        client.post(url, json={"name": "Cero", "terms": TERMS, "stamps_expire_days": 0}).status_code
        == 422
    )
    assert (
        client.post(
            url, json={"name": "Absurdo", "terms": TERMS, "stamps_expire_days": 3651}
        ).status_code
        == 422
    )


def test_editar_la_regla_no_toca_los_lotes_emitidos(
    client: TestClient, db_session: Session
) -> None:
    """Omitir el campo la conserva; `null` la retira; los lotes no cambian."""
    merchant_id, program_id, _, token = _world_with_rule(client, db_session, days=30)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-edit-1")

    login(client, OWNER_EMAIL)
    url = f"/api/v1/merchants/{merchant_id}/programs/{program_id}"

    # Editar otro campo no cambia la regla (solo se aplica si viene).
    actualizado = client.patch(url, json={"name": "Club del Pan 2"})
    assert actualizado.status_code == 200
    assert actualizado.json()["stamps_expire_days"] == 30

    retirada = client.patch(url, json={"stamps_expire_days": None})
    assert retirada.status_code == 200
    assert retirada.json()["stamps_expire_days"] is None

    # El lote ya emitido conserva su fecha: retirar la regla no indulta
    # ni caduca sellos antiguos.
    tx = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EARN,
        )
    ).one()
    assert tx.expires_at is not None


def test_earn_registra_la_fecha_de_caducidad(client: TestClient, db_session: Session) -> None:
    """Con regla activa, el lote caduca exactamente a los N días."""
    merchant_id, _, _, token = _world_with_rule(client, db_session, days=30)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-earn-1")

    tx = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EARN,
        )
    ).one()
    assert tx.expires_at is not None
    espera = utcnow() + timedelta(days=30)
    margen = espera - _as_utc(tx.expires_at)
    assert timedelta(minutes=-1) <= margen <= timedelta(minutes=1)


def test_sin_regla_el_lote_no_caduca(client: TestClient, db_session: Session) -> None:
    """Sin regla, ningún lote lleva fecha: el comportamiento por defecto."""
    merchant_id, _, _, token = _world_with_rule(client, db_session, days=None)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-noregla-1")

    tx = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EARN,
        )
    ).one()
    assert tx.expires_at is None
    # Y una lectura no emite movimientos raros: el saldo sigue intacto.
    assert client.get(f"/api/v1/public/memberships/{token}").json()["stamps"] == 5
    expiries = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EXPIRY,
        )
    ).all()
    assert expiries == []


def test_los_sellos_vencidos_se_expiran_al_leer_la_ficha(
    client: TestClient, db_session: Session
) -> None:
    """La lectura materializa el `expiry`: saldo bajo y movimiento trazable."""
    merchant_id, _, _, token = _world_with_rule(client, db_session)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-leer-1")
    _make_due(db_session, membership.id)

    # Tarjeta pública del cliente: el saldo que ve ya excluye lo vencido.
    card = client.get(f"/api/v1/public/memberships/{token}")
    assert card.status_code == 200
    assert card.json()["stamps"] == 0

    db_session.refresh(membership)
    assert membership.stamps == 0
    expiry_rows = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EXPIRY,
        )
    ).all()
    assert [row.quantity for row in expiry_rows] == [-5]
    # El ledger sigue cuadrando con la caché (§7.3).
    total = sum(
        row.quantity
        for row in db_session.scalars(
            select(LoyaltyTransaction).where(LoyaltyTransaction.membership_id == membership.id)
        )
    )
    assert total == membership.stamps == 0


def test_no_se_puede_canjear_con_sellos_vencidos(client: TestClient, db_session: Session) -> None:
    """El canje aplica los vencidos primero y rechaza si ya no alcanza."""
    merchant_id, _, reward_id, token = _world_with_rule(client, db_session)
    membership = _membership(db_session, token)
    # 5 caducados + 5 frescos: con la regla aplicada solo quedan 5.
    _earn(client, merchant_id, str(membership.id), "caducidad-canje-1")
    _make_due(db_session, membership.id)
    _earn(client, merchant_id, str(membership.id), "caducidad-canje-2")

    login(client, STAFF_EMAIL)
    response = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership.id}/redeem",
        json={"reward_id": reward_id, "idempotency_key": "caducidad-canje-x"},
    )
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "insufficient_stamps"

    db_session.refresh(membership)
    assert membership.stamps == 5  # los 5 vencidos ya no sirven para canjear


def test_lecturas_repetidas_no_duplican_el_vencimiento(
    client: TestClient, db_session: Session
) -> None:
    """La caducidad es idempotente: tres lecturas, un solo movimiento."""
    merchant_id, _, _, token = _world_with_rule(client, db_session)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-idem-1")
    _make_due(db_session, membership.id)

    for _ in range(3):
        assert client.get(f"/api/v1/public/memberships/{token}").status_code == 200

    expiries = db_session.scalars(
        select(LoyaltyTransaction).where(
            LoyaltyTransaction.membership_id == membership.id,
            LoyaltyTransaction.transaction_type == TransactionType.EXPIRY,
        )
    ).all()
    assert len(expiries) == 1
    assert expiries[0].quantity == -5


def test_las_condiciones_de_caducidad_son_visibles_antes_del_alta(
    client: TestClient, db_session: Session
) -> None:
    """La página de alta y la tarjeta comunican la regla (§7.7, §13.4)."""
    merchant_id, program_id, _, token = _world_with_rule(client, db_session, days=45)

    public = client.get("/api/v1/public/programs/panaderia-central/club-del-pan")
    assert public.status_code == 200
    assert public.json()["stamps_expire_days"] == 45

    card = client.get(f"/api/v1/public/memberships/{token}")
    assert card.status_code == 200
    assert card.json()["stamps_expire_days"] == 45

    # Y el editor del comercio la ve para no cambiarla a ciegas.
    login(client, OWNER_EMAIL)
    detalle = client.get(f"/api/v1/merchants/{merchant_id}/programs/{program_id}")
    assert detalle.status_code == 200
    assert detalle.json()["stamps_expire_days"] == 45


def test_el_listado_de_clientes_tambien_aplica_la_caducidad(
    client: TestClient, db_session: Session
) -> None:
    """La lista de Clientes no enseña sellos vencidos como si valieran."""
    merchant_id, _, _, token = _world_with_rule(client, db_session)
    membership = _membership(db_session, token)
    _earn(client, merchant_id, str(membership.id), "caducidad-lista-1")
    _make_due(db_session, membership.id)

    login(client, OWNER_EMAIL)
    listing = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    assert listing.status_code == 200
    row = next(row for row in listing.json()["items"] if row["id"] == str(membership.id))
    assert row["stamps"] == 0
    db_session.refresh(membership)
    assert membership.stamps == 0
