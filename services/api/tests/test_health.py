"""Pruebas de los endpoints de salud, cabeceras y correlation ID (FASE 1)."""

from typing import Any

from app.api import health
from app.db.session import DatabaseStatus
from app.main import app
from fastapi.testclient import TestClient


def test_health_responde_ok_sin_tocar_la_bd() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "LocalAI Fidelity API"
    assert payload["environment"] in {"development", "test", "production"}


def test_ready_devuelve_503_si_la_bd_no_responde(monkeypatch: Any) -> None:
    monkeypatch.setattr(
        health,
        "check_database",
        lambda: DatabaseStatus(reachable=False, error_type="OperationalError"),
    )
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database"] == "unavailable"


def test_ready_devuelve_200_cuando_la_bd_responde(monkeypatch: Any) -> None:
    monkeypatch.setattr(health, "check_database", lambda: DatabaseStatus(reachable=True))
    with TestClient(app) as client:
        response = client.get("/ready")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"
    # ADR-0002: el proveedor de Wallet visible es el configurado (simulado por defecto).
    assert payload["wallet_provider"] == "simulated"


def test_cabeceras_de_seguridad_presentes_en_todas_las_respuestas() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_correlation_id_se_genera_y_se_devuelve() -> None:
    with TestClient(app) as client:
        response = client.get("/health")
    request_id = response.headers.get("X-Request-ID")
    assert request_id and request_id != "-"


def test_correlation_id_entrante_se_respeta_si_es_saneable() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "fase1-abc-123"})
    assert response.headers["X-Request-ID"] == "fase1-abc-123"


def test_correlation_id_malicioso_se_sustituye() -> None:
    with TestClient(app) as client:
        response = client.get("/health", headers={"X-Request-ID": "<script>" * 10})
    request_id = response.headers["X-Request-ID"]
    assert "<" not in request_id
    assert len(request_id) <= 64


def test_error_interno_no_fuga_el_stack_trace() -> None:
    @app.get("/boom-test")
    def boom() -> None:
        raise RuntimeError("secreto que no debe salir")

    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/boom-test")
    finally:
        app.router.routes[:] = [
            r for r in app.router.routes if getattr(r, "path", None) != "/boom-test"
        ]

    assert response.status_code == 500
    body = response.text
    assert "Traceback" not in body
    assert "secreto que no debe salir" not in body
    assert response.json()["error"]["code"] == "internal_error"
    assert response.json()["error"]["request_id"]


def test_la_documentacion_openapi_no_esta_en_produccion(monkeypatch: Any) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    monkeypatch.setattr(settings, "app_env", "production")
    try:
        from app.main import create_app

        prod_app = create_app()
        assert prod_app.openapi_url is None
        assert prod_app.docs_url is None
    finally:
        get_settings.cache_clear()
