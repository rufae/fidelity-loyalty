"""Integración contra **PostgreSQL real** (§19.2, tasks2 §19.2).

SQLite no valida la semántica de bloqueo ni la concurrencia de fila que usa
el canje. Esta suite corre contra una base `localai_fidelity_pgtest` (se crea
si no existe) y nunca toca la base de datos del entorno.

Ejecución:

    uv run pytest -m pg

La URL se toma de `PG_TEST_URL` si está definida; si no, se deriva del
`DATABASE_URL` del `.env` de la raíz (el mismo PostgreSQL del entorno local,
con una base de pruebas propia que se crea sola).
"""

import os
import pathlib
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from app.db.base import Base
from app.domain.errors import DomainError
from app.models.ledger import LoyaltyTransaction
from app.models.loyalty import LoyaltyProgram
from app.models.members import Member, Membership
from app.services import ledger as ledger_service
from app.services import lifecycle
from app.services import members as members_service
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


def _admin_url() -> str:
    """`PG_TEST_URL` explícita o el `DATABASE_URL` del `.env` de la raíz."""
    override = os.environ.get("PG_TEST_URL")
    if override:
        return override
    root_env = pathlib.Path(__file__).resolve().parents[3] / ".env"
    if root_env.exists():
        for line in root_env.read_text().splitlines():
            if line.startswith("DATABASE_URL="):
                url = line.split("=", 1)[1].strip()
                return url.rsplit("/", 1)[0] + "/postgres"
    return "postgresql+psycopg://localai:localai@localhost:5434/postgres"


ADMIN_URL = _admin_url()
TEST_DB = "localai_fidelity_pgtest"

pytestmark = pytest.mark.pg


def _test_url() -> str:
    return ADMIN_URL.rsplit("/", 1)[0] + f"/{TEST_DB}"


@pytest.fixture(scope="module")
def pg_engine() -> Iterator[Engine]:
    try:
        admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
        with admin.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :db"), {"db": TEST_DB}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
        admin.dispose()
    except Exception as error:  # noqa: BLE001 — sin PostgreSQL no hay suite
        pytest.skip(f"PostgreSQL no disponible para la suite pg: {error}")
    engine = create_engine(_test_url(), pool_size=10, max_overflow=10)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture()
def pg_session(pg_engine: Engine) -> Iterator[Session]:
    with Session(pg_engine) as session:
        yield session


def _world(session: Session) -> Membership:
    """Comercio, programa y membresía con 10 sellos listos para canjear."""
    member = Member(merchant_id=uuid.uuid4(), email="cliente@example.com", display_name="Cliente")
    session.add(member)
    session.flush()
    program = LoyaltyProgram(
        merchant_id=member.merchant_id,
        name="Club",
        slug="club",
        status="active",
        terms="1 sello por visita",
    )
    session.add(program)
    session.flush()
    membership = Membership(
        merchant_id=member.merchant_id,
        program_id=program.id,
        member_id=member.id,
        public_token=members_service.new_public_token(),
        stamps=10,
    )
    session.add(membership)
    session.commit()
    return membership


def test_dos_canjes_concurrentes_sin_doble_gasto(pg_engine: Engine, pg_session: Session) -> None:
    """§7.4/§16.4: dos canjes simultáneos → uno aceptado y uno rechazado."""
    from app.models.loyalty import ProgramReward

    membership = _world(pg_session)
    reward = ProgramReward(
        program_id=membership.program_id,
        name="Café gratis",
        stamps_required=10,
        status="active",
    )
    pg_session.add(reward)
    pg_session.commit()
    membership_id, reward_id = membership.id, reward.id

    def redeem(key: str) -> tuple[int, str]:
        with Session(pg_engine) as session:
            reward_row = session.get(ProgramReward, reward_id)
            assert reward_row is not None
            try:
                result = ledger_service.redeem(
                    session,
                    membership_id,
                    membership.merchant_id,
                    reward_row,
                    idempotency_key=key,
                    actor_user_id=None,
                )
                session.commit()
                return 201, result.membership.status
            except DomainError as error:
                session.rollback()
                return error.status_code, error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(redeem, ["pg-canje-a", "pg-canje-b"]))

    codigos = sorted(code for code, _ in resultados)
    assert codigos == [201, 409]  # exactamente uno efectivo
    assert "insufficient_stamps" in {detail for _, detail in resultados}


def test_earn_concurrente_con_la_misma_clave_no_duplica(
    pg_engine: Engine, pg_session: Session
) -> None:
    """§16.4: la idempotencia está en la restricción de la BD, no solo en código."""
    membership = _world(pg_session)
    membership_id = membership.id

    def earn() -> tuple[int, bool]:
        with Session(pg_engine) as session:
            result = ledger_service.earn(
                session,
                membership_id,
                membership.merchant_id,
                quantity=1,
                idempotency_key="pg-earn-misma-clave",
                actor_user_id=None,
            )
            session.commit()
            return 201, result.already_applied

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: earn(), range(2)))

    aplicados = [applied for _, applied in resultados].count(False)
    assert aplicados == 1  # una sola aplicación real
    with Session(pg_engine) as session:
        movimientos = (
            session.query(LoyaltyTransaction).filter_by(membership_id=membership_id).count()
        )
        assert movimientos == 1


def test_revocar_en_carrera_con_earn_deja_estado_consistente(
    pg_engine: Engine, pg_session: Session
) -> None:
    """§10.3: la revocación bloquea en backend sin corromper el ledger."""
    membership = _world(pg_session)
    membership_id = membership.id

    def revoke() -> str:
        with Session(pg_engine) as session:
            row = session.get(Membership, membership_id)
            assert row is not None
            lifecycle.revoke(session, row, actor_id=None, reason="carrera")
            session.commit()
            return row.status

    def earn() -> tuple[int, str]:
        with Session(pg_engine) as session:
            try:
                ledger_service.earn(
                    session,
                    membership_id,
                    membership.merchant_id,
                    quantity=1,
                    idempotency_key="pg-carrera-earn",
                    actor_user_id=None,
                )
                session.commit()
                return 201, "ok"
            except DomainError as error:
                session.rollback()
                return error.status_code, error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        futuro_revocar = pool.submit(revoke)
        futuro_earn = pool.submit(earn)
        assert futuro_revocar.result() == "revoked"
        codigo, detalle = futuro_earn.result()

    # El earn o entra antes de la revocación (201) o queda bloqueado (409/403);
    # lo que no puede ocurrir es un saldo inconsistente con la revocación.
    assert (codigo, detalle) in {
        (201, "ok"),
        (403, "membership_inactive"),
        (409, "membership_revoked"),
    }
    with Session(pg_engine) as session:
        row = session.get(Membership, membership_id)
        assert row is not None and row.status == "revoked"


def test_consumo_concurrente_de_enlace_de_un_solo_uso(
    pg_engine: Engine, pg_session: Session
) -> None:
    """§16.4: dos canjes simultáneos del MISMO enlace → un solo ganador.

    Regresión de la auditoría: el consumo se hace con `UPDATE ... WHERE
    used_at IS NULL` (una sola sentencia atómica). Con el patrón anterior
    (leer y luego escribir) ambas peticiones leían el token como no usado y
    los dos ganaban.
    """
    from app.models.card_access import MemberEmailToken  # noqa: F401 — tablas registradas
    from app.models.merchant import Merchant
    from app.services import card_access as card_access_service

    merchant = Merchant(
        name="Cafetería Carrera",
        slug=f"cafe-carrera-{uuid.uuid4().hex[:8]}",
    )
    pg_session.add(merchant)
    pg_session.flush()
    member = Member(
        merchant_id=merchant.id,
        email="carrera@example.com",
        display_name="Cliente Carrera",
    )
    pg_session.add(member)
    pg_session.commit()
    raw = card_access_service.issue_email_token(
        pg_session, member, merchant.id, "email_verification"
    )
    pg_session.commit()

    def consume() -> tuple[int, str]:
        with Session(pg_engine) as session:
            try:
                card_access_service.consume_email_token(session, raw, "email_verification")
                session.commit()
                return 200, "ok"
            except DomainError as error:
                session.rollback()
                return error.status_code, error.code

    with ThreadPoolExecutor(max_workers=2) as pool:
        resultados = list(pool.map(lambda _: consume(), range(2)))

    assert sorted(code for code, _ in resultados) == [200, 400]
    assert "invalid_or_expired_link" in {detail for _, detail in resultados}
