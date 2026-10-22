"""Límites del tráfico público: lecturas generosas, altas estrictas (§13.4).

Contexto real: la tarjeta del cliente se **sondea** para actualizarse sin
recargar y varios dispositivos pueden compartir IP tras el NAT del local.
Un único cupo de 30/min para todo habría bloqueado a clientes legítimos.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import login
from .test_ledger import _world


def test_las_lecturas_publicas_toleran_el_sondeo_de_la_tarjeta(
    client: TestClient, db_session: Session
) -> None:
    _, token, _ = _world(client, db_session)

    # 40 consultas seguidas de la tarjeta (más de las 30 del límite antiguo):
    # ninguna debe responder 429.
    for _ in range(40):
        response = client.get(f"/api/v1/public/memberships/{token}")
        assert response.status_code == 200, "el sondeo de la tarjeta no debe bloquearse"


def test_las_altas_siguen_limitadas_por_ip(client: TestClient, db_session: Session) -> None:
    from app.api.public import public_limiter

    merchant_id, _, _ = _world(client, db_session)
    login(client, "owner-a@example.com")
    program = client.get(f"/api/v1/merchants/{merchant_id}/programs").json()[0]
    client.post("/api/v1/auth/logout")
    public_limiter.reset()  # la preparación no debe consumir el cupo medido

    statuses: list[int] = []
    for index in range(61):
        response = client.post(
            f"/api/v1/public/programs/cafeteria-a/{program['slug']}/enroll",
            json={
                "email": f"rafaga-{index}@example.com",
                "display_name": f"Cliente {index}",
                "privacy_notice_version": 1,
                "accepted_terms_version": 1,
            },
        )
        statuses.append(response.status_code)

    # La ráfaga cabe hasta 60/min (holgada para un mostrador con cola)…
    assert all(status == 201 for status in statuses[:60]), statuses
    # …y la petición 61 desde la misma IP se frena (sin bloquear a nadie legítimo).
    assert statuses[60] == 429
