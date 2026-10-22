"""Prueba end-to-end del recorrido completo del MVP (AGENTS.md §19.3, §21).

Recorre, contra la API real y con proveedores simulados:

plataforma crea comercio → comercio publica programa → cliente se registra →
personal acumula sellos (idempotente) → canje → tarjeta Wallet simulada →
etiqueta de alta → enlace de reseñas verificado → redirect → analítica →
exportación → aislamiento entre comercios.
"""

from app.domain.roles import PlatformRole
from app.models.members import Membership
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from .conftest import EMAIL_OUTBOX, PASSWORD, PLATFORM_EMAIL, create_user, email_token

TERMS = "1 sello por visita. Canje desde 10 sellos. Condiciones visibles v1."


def test_recorrido_completo_del_mvp(client: TestClient, db_session: Session) -> None:
    # 0. Administración de plataforma con sesión.
    create_user(db_session, PLATFORM_EMAIL, password=PASSWORD, platform_role=PlatformRole.OWNER)
    db_session.commit()
    assert (
        client.post(
            "/api/v1/auth/login", json={"email": PLATFORM_EMAIL, "password": PASSWORD}
        ).status_code
        == 200
    )

    # 1. La plataforma crea un comercio con su propietario.
    comercio = client.post(
        "/api/v1/platform/merchants",
        json={
            "name": "Cafetería Central",
            "owner_email": "central@example.com",
            "owner_password": "cafeteria-central-123",
        },
    ).json()
    merchant_id = comercio["id"]
    client.post("/api/v1/auth/logout")

    # 2. El propietario entra, crea el programa y lo publica con condiciones.
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "central@example.com", "password": "cafeteria-central-123"},
        ).status_code
        == 200
    )
    programa = client.post(
        f"/api/v1/merchants/{merchant_id}/programs",
        json={"name": "Club del Café", "terms": TERMS},
    ).json()
    recompensa = client.post(
        f"/api/v1/merchants/{merchant_id}/programs/{programa['id']}/rewards",
        json={"name": "Café gratis", "stamps_required": 10},
    ).json()
    assert (
        client.post(f"/api/v1/merchants/{merchant_id}/programs/{programa['id']}/publish").json()[
            "status"
        ]
        == "active"
    )
    client.post("/api/v1/auth/logout")

    # 3. El cliente ve la página pública y se registra con datos mínimos.
    publica = client.get("/api/v1/public/programs/cafeteria-central/club-del-cafe")
    assert publica.status_code == 200 and publica.json()["enrollment_open"] is True
    alta = client.post(
        "/api/v1/public/programs/cafeteria-central/club-del-cafe/enroll",
        json={
            "email": "cliente@example.com",
            "display_name": "Cliente de Prueba",
            "privacy_notice_version": 1,
            "accepted_terms_version": 1,
        },
    )
    assert alta.status_code == 201, alta.text
    assert "membership_token" not in alta.json()
    verification_token = email_token(subject="Confirma")
    confirmed = client.post("/api/v1/public/email/verify", json={"token": verification_token})
    assert confirmed.status_code == 200
    assert len(EMAIL_OUTBOX) == 2
    assert "Tu tarjeta" in EMAIL_OUTBOX[1]["subject"]
    assert (
        client.post("/api/v1/public/email/verify", json={"token": verification_token}).status_code
        == 400
    )
    token = db_session.query(Membership).one().public_token

    # 4. El personal identifica la tarjeta y acumula sellos de forma idempotente.
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"email": "central@example.com", "password": "cafeteria-central-123"},
        ).status_code
        == 200
    )
    membresia = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/lookup", json={"token": token}
    ).json()
    membership_id = membresia["id"]
    earn_url = f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/earn"
    for i in range(10):
        assert (
            client.post(
                earn_url, json={"quantity": 1, "idempotency_key": f"visita-{i}"}
            ).status_code
            == 201
        )
    repetida = client.post(earn_url, json={"quantity": 1, "idempotency_key": "visita-3"})
    assert repetida.json()["already_applied"] is True  # sin duplicar

    # 5. La tarjeta del cliente refleja los sellos y el Wallet simulado.
    tarjeta = client.get(f"/api/v1/public/memberships/{token}").json()
    assert tarjeta["stamps"] == 10
    assert tarjeta["simulated_wallet"] is True
    assert tarjeta["rewards"][0]["earned"] is True

    # 6. Emisión del pase Wallet (simulado) y canje de la recompensa.
    pase = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/wallet/issue"
    ).json()
    assert pase["simulated"] is True and pase["job_status"] == "succeeded"

    canje = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/redeem",
        json={"reward_id": recompensa["id"], "idempotency_key": "canje-e2e-1"},
    )
    assert canje.status_code == 201 and canje.json()["stamps"] == 0
    canje_repetido = client.post(
        f"/api/v1/merchants/{merchant_id}/memberships/{membership_id}/redeem",
        json={"reward_id": recompensa["id"], "idempotency_key": "canje-e2e-1"},
    )
    assert canje_repetido.json()["already_applied"] is True

    # 7. Etiqueta NFC de alta y etiqueta de reseñas (independientes, §5.1).
    etiqueta_alta = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags",
        json={
            "tag_type": "loyalty_signup",
            "label": "Mostrador",
            "program_id": programa["id"],
        },
    ).json()
    assert etiqueta_alta["destination_url"] == "/p/cafeteria-central/club-del-cafe"

    assert (
        client.put(
            f"/api/v1/merchants/{merchant_id}/review-destination",
            json={"review_url": "https://g.page/r/central/review"},
        ).status_code
        == 200
    )
    etiqueta_resena = client.post(
        f"/api/v1/merchants/{merchant_id}/nfc-tags", json={"tag_type": "google_review"}
    ).json()
    sin_verificar = client.get(f"/go/{etiqueta_resena['public_slug']}", follow_redirects=False)
    assert sin_verificar.status_code == 404  # sin verificar no se redirige (§4.1)
    client.post(f"/api/v1/merchants/{merchant_id}/review-destination/verify")
    redirect = client.get(f"/go/{etiqueta_resena['public_slug']}", follow_redirects=False)
    assert redirect.status_code == 302
    assert redirect.headers["location"] == "https://g.page/r/central/review"

    # 8. Analítica real y exportación sin tokens.
    resumen = client.get(f"/api/v1/merchants/{merchant_id}/dashboard/summary").json()
    assert resumen["members_total"] == 1
    assert resumen["stamps_granted"] == 10
    assert resumen["redemptions"] == 1
    assert resumen["review_link_clicks"] == 1
    export = client.get(f"/api/v1/merchants/{merchant_id}/export/members.csv")
    assert token not in export.text

    # 9. Auditoría completa del recorrido.
    from app.models.audit import AuditEvent

    acciones = {e.action for e in db_session.query(AuditEvent).all()}
    assert {
        "merchant.created",
        "program.created",
        "program.published",
        "member.enrolled",
        "loyalty.earn",
        "loyalty.redeem",
        "wallet.issue",
        "nfc_tag.created",
        "review_destination.verified",
    } <= acciones


def test_un_comercio_no_ve_nada_de_otro(client: TestClient, db_session: Session) -> None:
    """§8.2: aislamiento comprobado de extremo a extremo con dos comercios."""
    create_user(db_session, PLATFORM_EMAIL, password=PASSWORD, platform_role=PlatformRole.OWNER)
    db_session.commit()
    client.post("/api/v1/auth/login", json={"email": PLATFORM_EMAIL, "password": PASSWORD})
    a = client.post(
        "/api/v1/platform/merchants",
        json={
            "name": "Comercio A",
            "owner_email": "a@example.com",
            "owner_password": "comercio-a-largo-12",
        },
    ).json()
    b = client.post(
        "/api/v1/platform/merchants",
        json={
            "name": "Comercio B",
            "owner_email": "b@example.com",
            "owner_password": "comercio-b-largo-12",
        },
    ).json()
    client.post("/api/v1/auth/logout")

    client.post(
        "/api/v1/auth/login", json={"email": "b@example.com", "password": "comercio-b-largo-12"}
    )
    programa_a = client.post(f"/api/v1/merchants/{a['id']}/programs", json={"name": "Club A"})

    assert programa_a.status_code == 404
    assert client.get(f"/api/v1/merchants/{a['id']}/members").status_code == 404
    assert client.get(f"/api/v1/merchants/{a['id']}/dashboard/summary").status_code == 404
    assert [m["name"] for m in client.get("/api/v1/merchants").json()] == ["Comercio B"]
    assert b["slug"] == "comercio-b"
