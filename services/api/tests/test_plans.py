"""Planes comerciales y tiendas (tasks.md §2, §5, §6).

Cubre: límites de estructura por plan (tiendas y programas en vivo), la
asignación de plan por la plataforma, el uso real del plan y el aislamiento
de las tiendas por comercio.
"""

import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import OWNER_EMAIL, PLATFORM_EMAIL, create_user, login
from .test_ledger import _world

MERCHANT_LOCATIONS_URL = "/api/v1/merchants/{merchant_id}/locations"
PLAN_URL = "/api/v1/merchants/{merchant_id}/plan"
PLATFORM_PLAN_URL = "/api/v1/platform/merchants/{merchant_id}/plan"
PUBLIC_PLANS_URL = "/api/v1/public/plans"


def _with_platform(db_session: Session) -> None:
    """Usuario de administración de plataforma para las pruebas de plan."""
    from app.domain.roles import PlatformRole

    create_user(db_session, PLATFORM_EMAIL, platform_role=PlatformRole.OWNER)
    db_session.commit()


def test_catalogo_publico_de_planes_sin_sesion(client: TestClient) -> None:
    """La página de precios se sirve sin login: es información pública."""
    response = client.get(PUBLIC_PLANS_URL)
    assert response.status_code == 200
    planes = response.json()
    assert [p["code"] for p in planes] == ["basic", "plus", "max"]
    basico = planes[0]
    assert basico["max_locations"] == 1
    assert basico["max_active_programs"] == 1
    assert basico["price_month_eur"] > 0


def test_plan_del_comercio_refleja_uso_real(client: TestClient, db_session: Session) -> None:
    """El plan y su uso salen de la base de datos, nunca se inventan (§13.2)."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    response = client.get(PLAN_URL.format(merchant_id=merchant_id))
    assert response.status_code == 200
    data = response.json()
    # Comercio nuevo: plan Básico por omisión, un programa activo (el de _world).
    assert data["plan"] == "basic"
    assert data["plan_name"] == "Básico"
    assert data["max_locations"] == 1
    assert data["locations"] == 0
    assert data["max_active_programs"] == 1
    assert data["active_programs"] == 1


def test_staff_consulta_el_plan_pero_no_gestiona_tiendas(
    client: TestClient, db_session: Session
) -> None:
    """El plan es de lectura; crear tiendas es tarea de administración."""
    from .conftest import STAFF_EMAIL

    merchant_id, _, _ = _world(client, db_session)
    login(client, STAFF_EMAIL)
    assert client.get(PLAN_URL.format(merchant_id=merchant_id)).status_code == 200
    response = client.post(
        MERCHANT_LOCATIONS_URL.format(merchant_id=merchant_id),
        json={"name": "Tienda 2"},
    )
    assert response.status_code == 404


def test_basico_limita_a_una_tienda_y_mensaje_accionable(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    url = MERCHANT_LOCATIONS_URL.format(merchant_id=merchant_id)

    first = client.post(url, json={"name": "Sede Centro"})
    assert first.status_code == 201

    second = client.post(url, json={"name": "Tienda 2"})
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "plan_limit_reached"
    assert "1 tienda" in second.json()["detail"]["message"]


def test_plus_permite_tres_tiendas_y_el_limite_se_mantiene(
    client: TestClient, db_session: Session
) -> None:
    merchant_id, _, _ = _world(client, db_session)
    _with_platform(db_session)
    login(client, PLATFORM_EMAIL)
    plan_change = client.patch(
        PLATFORM_PLAN_URL.format(merchant_id=merchant_id), json={"plan": "plus"}
    )
    assert plan_change.status_code == 200
    assert plan_change.json()["plan"] == "plus"

    login(client, OWNER_EMAIL)
    url = MERCHANT_LOCATIONS_URL.format(merchant_id=merchant_id)
    for name in ("Centro", "Ronda", "Marina"):
        assert client.post(url, json={"name": name}).status_code == 201

    fourth = client.post(url, json={"name": "Excedente"})
    assert fourth.status_code == 409
    assert "3 tiendas" in fourth.json()["detail"]["message"]

    listing = client.get(url).json()
    assert len(listing) == 3


def test_basico_limita_programas_en_vivo_al_publicar(
    client: TestClient, db_session: Session
) -> None:
    """Los borradores son gratis; el límite muerde al publicar el segundo."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)

    second = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club Postres", "terms": "Términos de prueba del programa"},
    )
    assert second.status_code == 201
    program_id = second.json()["id"]

    publish = client.post(f"/api/v1/merchants/{merchant_id}/programs/{program_id}/publish")
    assert publish.status_code == 409
    assert publish.json()["detail"]["code"] == "plan_limit_reached"

    # Subir a Plus abre hueco para dos programas en vivo.
    _with_platform(db_session)
    login(client, PLATFORM_EMAIL)
    assert (
        client.patch(
            PLATFORM_PLAN_URL.format(merchant_id=merchant_id), json={"plan": "plus"}
        ).status_code
        == 200
    )
    login(client, OWNER_EMAIL)
    assert (
        client.post(f"/api/v1/merchants/{merchant_id}/programs/{program_id}/publish").status_code
        == 200
    )


def test_el_comercio_no_se_cambia_el_plan_a_si_mismo(
    client: TestClient, db_session: Session
) -> None:
    """El plan es un dato comercial: solo la plataforma lo toca (§22)."""
    merchant_id, _, _ = _world(client, db_session)
    _with_platform(db_session)
    login(client, OWNER_EMAIL)
    response = client.patch(PLATFORM_PLAN_URL.format(merchant_id=merchant_id), json={"plan": "max"})
    # La sesión de comercio no es válida en la superficie de plataforma.
    assert response.status_code in {401, 403, 404}


def test_plan_invalido_rechazado(client: TestClient, db_session: Session) -> None:
    merchant_id, _, _ = _world(client, db_session)
    _with_platform(db_session)
    login(client, PLATFORM_EMAIL)
    response = client.patch(PLATFORM_PLAN_URL.format(merchant_id=merchant_id), json={"plan": "oro"})
    assert response.status_code == 422


def test_reactivar_tienda_tambien_respeta_el_plan(client: TestClient, db_session: Session) -> None:
    """Reactivar consume un hueco igual que dar de alta: no se supera el plan."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    url = MERCHANT_LOCATIONS_URL.format(merchant_id=merchant_id)
    created = client.post(url, json={"name": "Sede Centro"}).json()

    # Desactivar libera el hueco; reactivar lo vuelve a ocupar.
    off = client.patch(f"{url}/{created['id']}", json={"status": "inactive"})
    assert off.status_code == 200

    # Una segunda tienda ocupa el hueco libre.
    second = client.post(url, json={"name": "Tienda Marina"})
    assert second.status_code == 201

    # Reactivar la primera ahora excedería el plan → 409 accionable.
    on = client.patch(f"{url}/{created['id']}", json={"status": "active"})
    assert on.status_code == 409
    assert on.json()["detail"]["code"] == "plan_limit_reached"
    assert "1 tienda" in on.json()["detail"]["message"]


def test_tienda_de_otro_comercio_no_se_toca(client: TestClient, db_session: Session) -> None:
    """Aislamiento: la tienda de otro comercio responde como inexistente."""
    from app.services.auth import find_user_by_email  # noqa: F401

    from .conftest import create_user

    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    created = client.post(
        MERCHANT_LOCATIONS_URL.format(merchant_id=merchant_id),
        json={"name": "Sede Centro"},
    ).json()

    other_owner = create_user(db_session, "owner-otro@example.com")
    from .conftest import create_merchant_with_owner as _cmwo

    other_merchant = _cmwo(db_session, other_owner, name="Bar Sur")
    db_session.commit()

    login(client, OWNER_EMAIL)
    response = client.patch(
        MERCHANT_LOCATIONS_URL.format(merchant_id=other_merchant.id) + f"/{created['id']}",
        json={"status": "inactive"},
    )
    assert response.status_code == 404
    assert str(uuid.UUID(created["id"])) == created["id"]


USERS_URL = "/api/v1/merchants/{merchant_id}/users"


def test_plan_limita_el_personal_y_el_mensaje_es_accionable(
    client: TestClient, db_session: Session
) -> None:
    """El Básico permite 2 empleados activos (1 libre tras el montaje); el
    siguiente se rechaza con 409 accionable."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    url = USERS_URL.format(merchant_id=merchant_id)

    # El mundo trae un staff activo: queda 1 hueco libre en el Básico.
    assert (
        client.post(
            url,
            json={
                "email": "empleado-nuevo@example.com",
                "password": "contrasena-larga-1234",
                "display_name": "Empleado Nuevo",
                "role": "staff",
            },
        ).status_code
        == 201
    )
    third = client.post(
        url,
        json={
            "email": "empleado-3@example.com",
            "password": "contrasena-larga-1234",
            "display_name": "Empleado Tres",
            "role": "staff",
        },
    )
    assert third.status_code == 409
    assert third.json()["detail"]["code"] == "plan_limit_reached"
    assert "2 empleados" in third.json()["detail"]["message"]

    # El uso del plan refleja el personal activo (el owner no cuenta).
    usage = client.get(PLAN_URL.format(merchant_id=merchant_id)).json()
    assert usage["staff"] == 2
    assert usage["max_staff"] == 2


def test_reactivar_personal_tambien_respeta_el_plan(
    client: TestClient, db_session: Session
) -> None:
    """Desactivar libera hueco; reactivar cuando está lleno vuelve a 409."""
    merchant_id, _, _ = _world(client, db_session)
    login(client, OWNER_EMAIL)
    url = USERS_URL.format(merchant_id=merchant_id)
    users = client.get(url).json()
    staff_user = next(u for u in users if u["role"] == "staff")

    # Desactivo al staff del montaje: queda hueco. Lleno el plan con dos
    # nuevos (2 activos de 2) para que la reactivación exceda el límite.
    off = client.patch(f"{url}/{staff_user['user_id']}", json={"status": "disabled"})
    assert off.status_code == 200
    for i in (1, 2):
        assert (
            client.post(
                url,
                json={
                    "email": f"otro-empleado-{i}@example.com",
                    "password": "contrasena-larga-1234",
                    "display_name": f"Otro Empleado {i}",
                    "role": "staff",
                },
            ).status_code
            == 201
        )

    # Reactivar al primero excedería el plan → 409 accionable.
    on = client.patch(f"{url}/{staff_user['user_id']}", json={"status": "active"})
    assert on.status_code == 409
    assert on.json()["detail"]["code"] == "plan_limit_reached"


def test_catalogo_publico_expone_el_personal_por_plan(client: TestClient) -> None:
    planes = {p["code"]: p for p in client.get(PUBLIC_PLANS_URL).json()}
    assert planes["basic"]["max_staff"] == 2
    assert planes["plus"]["max_staff"] > planes["basic"]["max_staff"]
    assert planes["max"]["max_staff"] > planes["plus"]["max_staff"]


LEAD_URL = "/api/v1/public/merchant-lead"


def test_solicitud_de_alta_publica_llega_a_la_plataforma(
    client: TestClient, db_session: Session
) -> None:
    """Un interesado deja su contacto en /precios y la plataforma lo recibe."""
    from app.core.config import Settings, get_settings
    from app.main import app as fastapi_app

    lead_settings = Settings(
        auth_session_secret="secreto-largo-de-pruebas-1234567890",
        support_notification_email="propietario@plataforma.example.com",
        support_email_enabled=True,
        support_from_email="soporte@localai.example.com",
    )
    # Mismo objeto que atiende `client`: el override alcanza la petición.
    fastapi_app.dependency_overrides[get_settings] = lambda: lead_settings
    try:
        response = client.post(
            LEAD_URL,
            json={
                "business_name": "Heladería Polar",
                "contact_name": "Alicia Ramos",
                "email": "alicia@polar.example.com",
                "plan": "plus",
                "message": "Tengo dos locales, ¿podemos probarlo?",
            },
        )
    finally:
        fastapi_app.dependency_overrides.pop(get_settings, None)
    assert response.status_code == 202
    assert response.json() == {"ok": True}

    from .conftest import EMAIL_OUTBOX

    leads = [m for m in EMAIL_OUTBOX if "Solicitud de alta" in m.get("subject", "")]
    assert leads, "no se notificó a la plataforma"
    assert "Heladería Polar" in leads[-1]["text"]
    assert "plus" in leads[-1]["text"]


def test_solicitud_de_alta_valida_los_datos(client: TestClient) -> None:
    """Nombre corto o plan inventado no pasan la validación (422)."""
    assert (
        client.post(
            LEAD_URL,
            json={"business_name": "X", "contact_name": "Ana", "email": "a@b.co", "plan": "plus"},
        ).status_code
        == 422
    )
    assert (
        client.post(
            LEAD_URL,
            json={
                "business_name": "Local Valido",
                "contact_name": "Ana",
                "email": "a@b.co",
                "plan": "oro",
            },
        ).status_code
        == 422
    )
