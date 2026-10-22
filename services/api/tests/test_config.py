"""Pruebas de la configuración por defecto (sin `.env`, sin secretos reales)."""

from app.core.config import Settings, get_settings


def test_defaults_arrancan_sin_secretos() -> None:
    settings = Settings.model_validate({})
    assert settings.app_env == "development"
    assert settings.api_prefix == "/api/v1"


def test_wallet_simulado_por_defecto_adr_0002() -> None:
    """El producto completo debe ser usable sin credenciales Apple/Google (§17.2)."""
    settings = Settings.model_validate({})
    assert settings.wallet_provider == "simulated"


def test_database_url_usa_el_puerto_reservado_5434() -> None:
    settings = Settings.model_validate({})
    assert ":5434/" in settings.database_url


def test_cache_de_settings_es_invalidable() -> None:
    get_settings.cache_clear()
    first = get_settings()
    second = get_settings()
    assert first is second
