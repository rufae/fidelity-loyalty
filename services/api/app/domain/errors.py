"""Errores de dominio normalizados (AGENTS.md §23).

Cada error lleva un `code` legible y un status HTTP. Las respuestas **nunca**
revelan si un recurso ajeno existe: un comercio al que no perteneces responde
igual que uno inexistente (404), para no permitir enumeración (§8.2).
"""

from fastapi import HTTPException, status


class DomainError(HTTPException):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(status_code=status_code, detail={"code": code, "message": message})
        self.code = code


def unauthorized(code: str = "unauthorized", message: str = "No autenticado") -> DomainError:
    return DomainError(status.HTTP_401_UNAUTHORIZED, code, message)


def invalid_credentials() -> DomainError:
    # Mensaje idéntico exista o no el email: sin enumeración de cuentas (§8.2).
    return DomainError(
        status.HTTP_401_UNAUTHORIZED, "invalid_credentials", "Credenciales incorrectas"
    )


def login_rate_limited(retry_after_seconds: int) -> DomainError:
    error = DomainError(
        status.HTTP_429_TOO_MANY_REQUESTS,
        "login_rate_limited",
        f"Demasiados intentos. Reintenta en {retry_after_seconds} segundos",
    )
    error.headers = {"Retry-After": str(retry_after_seconds)}
    return error


def not_found(entity: str = "Recurso") -> DomainError:
    return DomainError(status.HTTP_404_NOT_FOUND, "not_found", f"{entity} no encontrado")


def slug_conflict() -> DomainError:
    return DomainError(
        status.HTTP_409_CONFLICT, "merchant_slug_conflict", "Ya existe un comercio con ese nombre"
    )


def user_exists() -> DomainError:
    return DomainError(
        status.HTTP_409_CONFLICT, "user_exists", "Ya existe un usuario con ese email"
    )


class PlanLimitError(DomainError):
    """El comercio alcanzó el límite de estructura de su plan (FASE 14)."""


def plan_limit_reached(kind: str, limit: int) -> PlanLimitError:
    """Error legible y accionable: qué límite y qué hacer (§3.3: nada oculto)."""
    nouns = {
        "locations": ("tienda", "Mejora de plan para añadir más."),
        "programs": ("programa", "Pausa o archiva uno antes, o mejora de plan."),
        "staff": ("empleado", "Mejora de plan para dar de alta a más personal."),
    }
    noun, action = nouns.get(kind, nouns["locations"])
    noun = f"{noun}{'s' if limit != 1 else ''}"
    return PlanLimitError(409, "plan_limit_reached", f"Tu plan permite {limit} {noun}. {action}")
