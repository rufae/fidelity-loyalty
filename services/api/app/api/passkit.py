"""Servicio web de Apple Wallet para actualizar pases (PassKit, §6.4).

Apple consulta estos endpoints desde los dispositivos para registrar un pase,
preguntar qué pases cambiaron y descargar la versión actualizada. Sin este
servicio, un pase emitido es estático: los sellos que muestra nunca cambian.

Reglas:
- La autenticación es el `authenticationToken` de cada pase (cabecera
  `Authorization: ApplePass <token>`), nunca la cookie de sesión.
- El pase servido se **reconstruye** con el saldo real del ledger: el backend
  es la fuente de verdad (§6.1).
- Sin proveedor Apple configurado no hay pases que servir: 404 honesto.
- El `serialNumber` del pase es `membership.id.hex`; el QR del pase lleva el
  token opaco de la tarjeta (§9.3).
"""

import hmac
import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.integrations.wallet import get_wallet_provider
from app.models.members import Membership
from app.models.wallet import PassDeviceRegistration, WalletPass
from app.services import wallet as wallet_service
from app.services.audit import record_audit

logger = logging.getLogger(__name__)

# El prefijo global `/api/v1` lo aplica `main.py` al incluir el router; los
# caminos finales son `/api/v1/devices/...` y `/api/v1/passes/...`, que son
# los que PassKit concatena a `webServiceURL = PUBLIC_BASE_URL + "/api/v1"`.

router = APIRouter(tags=["passkit"])

DbSession = Annotated[Session, Depends(get_session)]


def _unauthorized() -> Response:
    return Response(status_code=401)


def _pass_by_serial(session: Session, serial: str) -> WalletPass | None:
    return session.scalar(
        select(WalletPass).where(
            WalletPass.provider == "apple", WalletPass.provider_object_id == serial
        )
    )


def _authenticated(
    session: Session, serial: str, settings: Settings, authorization: str | None
) -> WalletPass | None:
    """Valida el `ApplePass <token>` del pase; devuelve None si no autoriza.

    El token esperado es el HMAC determinista del pase (§6.4), independiente
    de metadatos en base de datos: no se puede adivinar ni apadrinar con un
    valor persistido obsoleto.
    """
    if not authorization or not authorization.startswith("ApplePass "):
        return None
    token = authorization.removeprefix("ApplePass ").strip()
    wallet_pass = _pass_by_serial(session, serial)
    if wallet_pass is None:
        return None
    if not token or not hmac.compare_digest(
        token, wallet_service.authentication_token(settings, wallet_pass.membership_id)
    ):
        return None
    return wallet_pass


@router.post("/devices/{device_id}/registrations/{pass_type_id}/{serial}")
async def register_device(
    device_id: str,
    pass_type_id: str,
    serial: str,
    request: Request,
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Registra un dispositivo para recibir actualizaciones de un pase (201)."""
    wallet_pass = _authenticated(session, serial, get_settings(), authorization)
    if wallet_pass is None:
        return _unauthorized()
    body = {}
    try:
        body = await _json_body(request)
    except ValueError:
        body = {}
    existing = session.scalar(
        select(PassDeviceRegistration).where(
            PassDeviceRegistration.device_id == device_id,
            PassDeviceRegistration.serial == serial,
        )
    )
    if existing is None:
        session.add(
            PassDeviceRegistration(
                device_id=device_id,
                pass_type_id=pass_type_id,
                serial=serial,
                membership_id=wallet_pass.membership_id,
                push_token=str(body.get("pushToken") or "")[:255] or None,
                created_at=datetime.now(UTC),
            )
        )
        session.commit()
        return Response(status_code=201)
    return Response(status_code=200)


@router.delete("/devices/{device_id}/registrations/{pass_type_id}/{serial}")
def unregister_device(
    device_id: str,
    pass_type_id: str,  # noqa: ARG001 — forma del contrato Apple
    serial: str,
    session: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Baja del registro de un dispositivo (200)."""
    wallet_pass = _authenticated(session, serial, get_settings(), authorization)
    if wallet_pass is None:
        return _unauthorized()
    row = session.scalar(
        select(PassDeviceRegistration).where(
            PassDeviceRegistration.device_id == device_id,
            PassDeviceRegistration.serial == serial,
        )
    )
    if row is not None:
        session.delete(row)
        session.commit()
    return Response(status_code=200)


@router.get("/devices/{device_id}/registrations/{pass_type_id}")
def serials_updated_since(
    device_id: str,
    pass_type_id: str,  # noqa: ARG001
    session: DbSession,
    passesUpdatedSince: str | None = None,
) -> Response:
    """Seriales de pases actualizados desde la marca temporal ( PassKit )."""
    since: datetime | None = None
    if passesUpdatedSince:
        try:
            since = datetime.fromisoformat(passesUpdatedSince.replace("Z", "+00:00"))
        except ValueError:
            since = None
    query = (
        select(WalletPass.provider_object_id)
        .join(
            PassDeviceRegistration,
            PassDeviceRegistration.serial == WalletPass.provider_object_id,
        )
        .where(
            PassDeviceRegistration.device_id == device_id,
            WalletPass.provider == "apple",
            WalletPass.status == "issued",
        )
        .distinct()
    )
    if since is not None:
        query = query.where(WalletPass.last_updated_at > since)
    serials = [str(row) for row in session.scalars(query)]
    from fastapi.responses import JSONResponse

    return JSONResponse(
        {
            "serialNumbers": serials,
            "lastUpdated": datetime.now(UTC).isoformat(),
        }
    )


@router.get("/passes/{pass_type_id}/{serial}")
def download_pass(
    pass_type_id: str,  # noqa: ARG001
    serial: str,
    session: DbSession,
    settings: Annotated[Settings, Depends(get_settings)],
    authorization: Annotated[str | None, Header()] = None,
) -> Response:
    """Sirve el `.pkpass` reconstruido con el saldo real del ledger (§6.1)."""
    wallet_pass = _authenticated(session, serial, get_settings(), authorization)
    if wallet_pass is None:
        return _unauthorized()
    membership = session.get(Membership, wallet_pass.membership_id)
    if membership is None:
        return Response(status_code=404)
    provider = get_wallet_provider(settings)
    context = wallet_service.pass_context(session, membership, settings)
    try:
        payload = provider.build_pass(context)  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001 — respuesta honesta al dispositivo
        logger.exception("passkit: no se pudo reconstruir el pase %s", wallet_pass.id)
        return Response(status_code=500)
    # Trazabilidad (§8.4): cada descarga de pase queda registrada sin datos
    # personales (actor = dispositivo del cliente vía token del pase).
    record_audit(
        session,
        action="wallet.pass_download",
        entity_type="wallet_pass",
        actor_type="member",
        merchant_id=membership.merchant_id,
        entity_id=str(wallet_pass.id),
        metadata={"provider": "apple"},
    )
    session.commit()
    return Response(
        content=payload,
        media_type="application/vnd.apple.pkpass",
        headers={"Content-Disposition": f'attachment; filename="pass-{serial}.pkpass"'},
    )


@router.post("/log")
def pass_log() -> Response:
    """Mensajes de depuración del dispositivo ( PassKit ): se aceptan y se ignora el cuerpo."""
    return Response(status_code=200)


async def _json_body(request: Request) -> dict[str, object]:
    import json

    raw = await request.body()
    if not raw:
        return {}
    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError("cuerpo no es un objeto")
    result: dict[str, object] = {}
    result.update(parsed)
    return result
