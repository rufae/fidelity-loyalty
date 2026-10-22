"""Seguridad de credenciales: hash de contraseñas, cookie de sesión y
límite de intentos de login (AGENTS.md §8.3, §16.2)."""

import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

# Argon2id con parámetros por encima del mínimo del OWASP (2024): ~19 MiB de
# memoria, 2 iteraciones, 1 hilo. El coste es intencionado: el login es un
# evento raro y la fuerza bruta debe salir cara.
_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

SESSION_COOKIE_NAME = "lf_session"


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Comparación en tiempo constante; nunca lanza excepción al usuario."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(password_hash: str) -> bool:
    try:
        return _hasher.check_needs_rehash(password_hash)
    except InvalidHashError:
        return True


@dataclass(frozen=True)
class RateLimitDecision:
    allowed: bool
    retry_after_seconds: int = 0


class LoginRateLimiter:
    """Ventana deslizante por (IP, email) — §8.3 y §16.2.

    En memoria a propósito en la FASE 2: una sola instancia del backend y un
    solo usuario operando. Si la app escala a varios procesos, moverlo a
    PostgreSQL o Redis será una decisión documentada, no un reescritor.
    """

    def __init__(
        self,
        max_attempts: int,
        window_seconds: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> RateLimitDecision:
        now = self._clock()
        window_start = now - self._window_seconds
        hits = self._hits[key]
        while hits and hits[0] < window_start:
            hits.popleft()
        if len(hits) >= self._max_attempts:
            retry_after = int(hits[0] + self._window_seconds - now) + 1
            return RateLimitDecision(allowed=False, retry_after_seconds=max(retry_after, 1))
        return RateLimitDecision(allowed=True)

    def record_failure(self, key: str) -> None:
        self._hits[key].append(self._clock())

    def reset(self, key: str | None = None) -> None:
        """Borra el contador (login correcto, o todo el estado en pruebas)."""
        if key is None:
            self._hits.clear()
        else:
            self._hits.pop(key, None)
