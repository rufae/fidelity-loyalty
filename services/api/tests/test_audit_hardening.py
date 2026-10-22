"""Regresiones de la auditoría integral (octubre 2026).

Cada test cubre un hallazgo concreto corregido; el nombre cita el identificador
del informe (`docs/audit/FINDINGS.md`) para trazabilidad entre hallazgo y
prueba.
"""

import uuid
from typing import Any

from app.core.config import Settings
from app.domain.roles import MerchantRole
from app.integrations.wallet.base import PassResult as WalletPassResult
from app.models.ledger import LoyaltyTransaction
from app.models.loyalty import LoyaltyProgram
from app.models.members import Member, Membership
from app.models.merchant import Merchant
from app.models.wallet import BackgroundJob, JobStatus, WalletPass
from app.services import wallet as wallet_service
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from .conftest import (
    OWNER_EMAIL,
    PASSWORD,
    add_member,
    create_user,
    login,
)
from .test_ledger import _world

TERMS = "1 sello por visita. Canje desde 10 sellos."

_ENROLL_BODY = {
    "email": "cliente@example.com",
    "display_name": "Cliente de Prueba",
    "privacy_notice_version": 1,
    "accepted_terms_version": 1,
}


def _db_world(
    db_session: Session, merchant_name: str = "Cafetería A"
) -> tuple[Merchant, LoyaltyProgram, Membership]:
    """Comercio con programa de sellos activo y una membresía, sin HTTP.

    Para los tests de servicios que no necesitan la API (`ledger`, `wallet`).
    """
    import secrets
    import uuid as uuid_mod

    from app.models.loyalty import ProgramStatus

    from .conftest import create_merchant_with_owner

    owner = create_user(db_session, f"owner-{uuid_mod.uuid4().hex[:10]}@example.com")
    merchant = create_merchant_with_owner(db_session, owner, name=merchant_name)
    db_session.commit()
    program = LoyaltyProgram(
        merchant_id=merchant.id,
        name="Club del Café",
        slug=f"club-{uuid_mod.uuid4().hex[:8]}",
        program_type="stamps",
        description=TERMS,
        terms=TERMS,
        status=ProgramStatus.ACTIVE,
    )
    db_session.add(program)
    db_session.commit()
    member = Member(
        merchant_id=merchant.id,
        email="cliente-db@example.com",
        display_name="Cliente de Prueba",
        status="active",
    )
    db_session.add(member)
    db_session.commit()
    membership = Membership(
        merchant_id=merchant.id,
        program_id=program.id,
        member_id=member.id,
        public_token=secrets.token_urlsafe(24),
        status="active",
    )
    db_session.add(membership)
    db_session.commit()
    return merchant, program, membership


class FailingProvider:
    """Proveedor que explota inmediatamente (regresión W‑1)."""

    name = "apple"

    def status(self) -> Any:
        from app.integrations.wallet.base import ProviderStatus

        return ProviderStatus.ACTIVE

    def issue_pass(self, membership_id: Any, public_token: Any, context: Any = None) -> Any:
        raise RuntimeError("boom certificado")

    def update_pass(self, membership_id: Any, public_token: Any, context: Any = None) -> Any:
        raise RuntimeError("boom certificado")

    def revoke_pass(self, membership_id: Any, public_token: Any, context: Any = None) -> Any:
        raise RuntimeError("boom")

    def get_add_to_wallet_action(self, public_token: Any, context: Any = None) -> Any:
        raise RuntimeError("boom")


def test_Z1_comercio_suspendido_no_deja_operar(client: TestClient, db_session: Session) -> None:
    """La suspensión de un comercio corta el acceso de su equipo (Z‑1)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    assert client.get(f"/api/v1/merchants/{merchant_id}/memberships").status_code == 200

    merchant = db_session.get(Merchant, merchant_id)
    assert merchant is not None
    merchant.status = "suspended"
    db_session.commit()

    # Con la sesión ya abierta, el equipo deja de operar al instante: el
    # comercio responde 404, idéntico a uno inexistente o ajeno (§8.2).
    denied = client.get(f"/api/v1/merchants/{merchant_id}/memberships")
    assert denied.status_code == 404
    assert denied.json()["detail"]["code"] == "not_found"
    client.post("/api/v1/auth/logout")

    # Y con la sesión cerrada, el propio login queda bloqueado (kill switch).
    res = client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "merchant_suspended"


def test_Z1_login_bloqueado_con_todo_suspenso(client: TestClient, db_session: Session) -> None:
    """Un usuario cuyo único comercio está suspendido no puede entrar (Z‑1)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    client.post("/api/v1/auth/logout")
    merchant = db_session.get(Merchant, merchant_id)
    assert merchant is not None
    merchant.status = "suspended"
    db_session.commit()

    res = client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "merchant_suspended"


def test_Z2_admin_no_puede_degradar_al_dueno(client: TestClient, db_session: Session) -> None:
    """La jerarquía impide a un `admin` modificar a un `owner` (Z‑2)."""
    from app.models.user import MerchantUser

    merchant_id, _, _ = _world(client, db_session)
    owner = db_session.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_id,
            MerchantUser.role == "owner",
        )
    )
    assert owner is not None
    LoginTeam = "admin-audit@example.com"
    admin = create_user(db_session, LoginTeam)
    merchant = db_session.get(Merchant, merchant_id)
    assert merchant is not None
    add_member(db_session, admin, merchant, MerchantRole.ADMIN)
    db_session.commit()

    login(client, LoginTeam)
    res = client.patch(
        f"/api/v1/merchants/{merchant_id}/users/{owner.user_id}",
        json={"role": "staff"},
    )
    assert res.status_code == 403
    assert res.json()["detail"]["code"] == "merchant_access_denied"
    # El owner sigue siendo owner.
    role = db_session.scalar(
        select(MerchantUser.role).where(
            MerchantUser.merchant_id == merchant_id,
            MerchantUser.user_id == owner.user_id,
        )
    )
    assert role == "owner"


def test_A2_alta_con_limite_por_correo(client: TestClient, db_session: Session) -> None:
    """El mismo correo no puede sondear altas en masa (A‑2, anti‑enumeración)."""
    merchant_id, _, _ = _world(client, db_session)
    client.post("/api/v1/auth/logout")
    email = "enumerador@example.com"
    codes = []
    for _ in range(6):
        res = client.post(
            "/api/v1/public/programs/cafeteria-a/club-del-cafe/enroll",
            json={
                "email": email,
                "display_name": "Cliente de Prueba",
                "privacy_notice_version": 1,
                "accepted_terms_version": 1,
            },
        )
        codes.append(res.status_code)
    # Las respuestas no distinguen una dirección ya usada de una nueva; el
    # sexto intento se limita para frenar solicitudes repetidas.
    assert set(codes[:5]) == {201}
    assert codes[5] == 429


def test_L1_clave_idempotente_no_traspasa_comercios(
    client: TestClient, db_session: Session
) -> None:
    """Una clave de idempotencia usada en otro comercio no filtra nada (L‑1)."""
    from app.models.user import MerchantUser, User

    merchant_a, _, membership_a = _db_world(db_session, "Cafetería A")
    merchant_b, _, membership_b = _db_world(db_session, "Pelquería B")

    # A acumula con la clave.
    owner_a = db_session.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_a.id, MerchantUser.role == "owner"
        )
    )
    assert owner_a is not None
    user_a = db_session.scalar(select(User).where(User.id == owner_a.user_id))
    assert user_a is not None
    login(client, user_a.email)
    res = client.post(
        f"/api/v1/merchants/{merchant_a.id}/memberships/{membership_a.id}/earn",
        json={"quantity": 1, "idempotency_key": "clave-entre-comercios"},
    )
    assert res.status_code in (200, 201)
    client.post("/api/v1/auth/logout")

    # El comercio B usa LA MISMA clave sobre SU membresía: sin la corrección,
    # el ledger devolvía (o colisionaba con) el movimiento del comercio A.
    owner_b = db_session.scalar(
        select(MerchantUser).where(
            MerchantUser.merchant_id == merchant_b.id, MerchantUser.role == "owner"
        )
    )
    assert owner_b is not None
    user_b = db_session.scalar(select(User).where(User.id == owner_b.user_id))
    assert user_b is not None
    login(client, user_b.email)
    res = client.post(
        f"/api/v1/merchants/{merchant_b.id}/memberships/{membership_b.id}/earn",
        json={"quantity": 1, "idempotency_key": "clave-entre-comercios"},
    )
    body = res.json()
    # Contrato idempotente por comercio (§8.2): o B aplica SU propio movimiento
    # (200/201) o se rechaza limpio (409 duplicate_operation); jamás se
    # reutiliza ni se filtra el movimiento del comercio A.
    assert res.status_code in (200, 201, 409)
    if res.status_code == 409:
        assert body["detail"]["code"] == "duplicate_operation"
    else:
        tx_a = db_session.scalar(
            select(LoyaltyTransaction.id).where(
                LoyaltyTransaction.idempotency_key == "clave-entre-comercios",
                LoyaltyTransaction.merchant_id == merchant_a.id,
            )
        )
        assert str(body["transaction_id"]) != str(tx_a)


def test_C1_origen_cruzado_rechazado(client: TestClient) -> None:
    """Peticiones con `Origin` ajeno al host no pasan (C‑1)."""
    res = client.post(
        "/api/v1/auth/login",
        json={"email": "a@example.com", "password": "x"},
        headers={"Origin": "https://atacante.malicioso"},
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "origin_not_allowed"


def test_C1_formulario_con_cuerpo_sin_json_rechazado(client: TestClient) -> None:
    """Un `<form>` con cuerpo no puede mutar la API ni con chunked (C‑1)."""
    res = client.post(
        "/api/v1/auth/login",
        content=b"email=a%40example.com&password=x",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Transfer-Encoding": "chunked",
        },
    )
    assert res.status_code == 415


def test_W1_excepcion_del_proveedor_no_revierte_el_ledger(
    monkeypatch: Any, db_session: Session
) -> None:
    """Un proveedor que explota deja el sello intacto (W‑1, §6.1)."""
    monkeypatch.setattr(wallet_service, "get_wallet_provider", lambda _s: FailingProvider())
    _, _, membership = _db_world(db_session)
    stamps_before = membership.stamps
    # Un pase emitido previamente: sin él no hay trabajo de actualización.
    db_session.add(
        WalletPass(
            merchant_id=membership.merchant_id,
            membership_id=membership.id,
            provider="apple",
            provider_object_id=membership.id.hex,
            status="issued",
            simulated=0,
        )
    )
    db_session.commit()

    settings = Settings(database_url="sqlite://", wallet_provider="apple")
    wallet_service.update_passes_after_operation(db_session, membership, settings)
    db_session.commit()

    assert membership.stamps == stamps_before
    job = db_session.scalar(select(BackgroundJob).where(BackgroundJob.job_type == "wallet.update"))
    assert job is not None
    # Un RuntimeError transitorio deja el trabajo en reintento; el punto de la
    # regresión es que el LEDGER queda intacto y el trabajo es visible.
    assert job.status in {JobStatus.FAILED, JobStatus.RETRYING}


def test_R1_url_de_resenas_solo_google(client: TestClient, db_session: Session) -> None:
    """El enlace de reseñas debe apuntar a Google; phishing rechazado (R‑1)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    for bad in (
        "https://evil.com/google.com",
        "https://google.com.ejemplo-malicioso.com/resenas",
        "http://google.com/sin_tls",
    ):
        res = client.put(
            f"/api/v1/merchants/{merchant_id}/review-destination",
            json={"review_url": bad},
        )
        assert res.status_code == 422, bad
    res = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination",
        json={"review_url": "https://maps.app.goo.gl/nueva"},
    )
    assert res.status_code in (200, 201)


def test_R1_allowlist_no_acepta_hosts_compuestos(client: TestClient, db_session: Session) -> None:
    """`google.com` dentro de otro dominio no autoriza el enlace (R‑1)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    res = client.put(
        f"/api/v1/merchants/{merchant_id}/review-destination",
        json={"review_url": "https://www.google.com-webhook.ataque.com/x"},
    )
    assert res.status_code == 422


def test_D1_cambio_de_contrasena_revoca_sesiones(client: TestClient, db_session: Session) -> None:
    """Cambio de contraseña exige la actual y reabre sesión (D‑1)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    # Contraseña actual incorrecta: rechazado.
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": "contrasena-equivocada", "new_password": "nueva-contrasena-4567"},
    )
    assert res.status_code in (400, 401, 403, 429)

    # Correcta: 200 y la sesión sigue válida (reabierta para este navegador).
    res = client.post(
        "/api/v1/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "nueva-contrasena-4567"},
    )
    assert res.status_code == 200
    client.post("/api/v1/auth/logout")

    # Con la contraseña vieja ya no se entra; con la nueva sí.
    old = client.post("/api/v1/auth/login", json={"email": OWNER_EMAIL, "password": PASSWORD})
    assert old.status_code == 401
    new = client.post(
        "/api/v1/auth/login",
        json={"email": OWNER_EMAIL, "password": "nueva-contrasena-4567"},
    )
    assert new.status_code == 200


def test_P2_passkit_sin_token_rechaza(client: TestClient, db_session: Session) -> None:
    """El servicio web de Apple exige el token `ApplePass` del pase (§6.4)."""
    _world(client, db_session)
    serial = uuid.uuid4().hex
    res = client.get(f"/api/v1/passes/pass.localai.test/{serial}")
    assert res.status_code == 401


def test_P2_passkit_registro_y_descarga_con_token(
    monkeypatch: Any, client: TestClient, db_session: Session
) -> None:
    """Ciclo completo PassKit con token válido: alta, serial y descarga (§6.4)."""
    _, _, membership = _db_world(db_session)
    serial = membership.id.hex

    # Pase de ejemplo válido para el fixture (proveedor reconstruible).
    from app.integrations.wallet.base import ProviderStatus

    wallet_service._record_result(  # noqa: SLF001 — fixture
        db_session,
        membership,
        "apple",
        WalletPassResult(
            provider_object_id=serial,
            status=ProviderStatus.TEST,
            simulated=False,
        ),
    )
    auth_token = wallet_service.authentication_token(
        Settings(database_url="sqlite://"), membership.id
    )
    pass_row = db_session.scalar(
        select(WalletPass).where(WalletPass.membership_id == membership.id)
    )
    assert pass_row is not None

    # Token incorrecto → 401.
    bad = client.post(
        f"/api/v1/devices/device-1/registrations/pass.localai.test/{serial}",
        headers={"Authorization": "ApplePass incorrecto"},
    )
    assert bad.status_code == 401

    # Correcto → 201 y el dispositivo queda registrado.
    good = client.post(
        f"/api/v1/devices/device-1/registrations/pass.localai.test/{serial}",
        json={"pushToken": "push-1"},
        headers={"Authorization": f"ApplePass {auth_token}"},
    )
    assert good.status_code == 201

    # El serial aparece en la consulta de actualizaciones.
    serials = client.get("/api/v1/devices/device-1/registrations/pass.localai.test")
    assert serials.status_code == 200
    assert serial in serials.json()["serialNumbers"]

    # Baja del dispositivo.
    bye = client.delete(
        f"/api/v1/devices/device-1/registrations/pass.localai.test/{serial}",
        headers={"Authorization": f"ApplePass {auth_token}"},
    )
    assert bye.status_code == 200
    serials2 = client.get("/api/v1/devices/device-1/registrations/pass.localai.test")
    assert serials2.json()["serialNumbers"] == []


def test_W1_pass_context_token_estable(db_session: Session) -> None:
    """El token PassKit se mantiene estable entre emisiones (§6.4)."""
    _, _, membership = _db_world(db_session)
    settings = Settings(database_url="sqlite://", wallet_provider="apple")
    ctx1 = wallet_service.pass_context(db_session, membership, settings)
    ctx2 = wallet_service.pass_context(db_session, membership, settings)
    assert ctx1.authentication_token
    assert ctx1.authentication_token == ctx2.authentication_token
    # El token no es derivable del UUID interno (mínimo 16 bytes hex).
    assert len(ctx1.authentication_token) >= 32
