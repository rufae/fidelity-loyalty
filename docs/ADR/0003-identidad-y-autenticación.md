# ADR-0003 — Identidad única y autenticación por sesión en servidor

- **Estado:** Aceptado
- **Fecha:** 2026-10-12 (FASE 2)
- **Contexto:** §8, §11.1, §11.4 y §16.2 de `AGENTS.md`.

## Decisión 1 — Una sola tabla de identidad (`users`)

En lugar de `platform_users` y `merchant_users` como entidades de credencial
independientes (§11.1/§11.4), existe **una** tabla `users` (email + hash) y una
tabla `merchant_users` que es la **relación** usuario ↔ comercio con su rol.

Motivo: un email no debe tener dos contraseñas, dos recuperaciones ni dos
historiales de login. El propio §11.4 permite evitar credenciales duplicadas
si se documenta la elección; aquí se hace.

## Decisión 2 — Sesión firmada **y** registrada en servidor

- Cookie `lf_session` = `<session_id>.<hmac_sha256(session_id)>`, `HttpOnly`,
  `SameSite=Lax`, `Secure` en producción, `Path=/`.
- `session_id` aleatorio de 256 bits guardado en la tabla `sessions`: permite
  **invalidar** una sesión concreta (logout, robo, cambio de contraseña) sin
  rotar el secreto global.
- Rotar `AUTH_SESSION_SECRET` también invalida todas las cookies de golpe.

## Decisión 3 — No existe interruptor de autenticación

`AUTH_ENABLED=false` no existe en este producto: guarda datos de clientes de
comercios. En **producción** el arranque falla sin `AUTH_SESSION_SECRET` ni
credenciales de semilla (fail-closed, §16.2). En desarrollo, si falta el
secreto se genera uno efímero por proceso.

El usuario inicial se crea con `AUTH_BOOTSTRAP_EMAIL`/`AUTH_BOOTSTRAP_PASSWORD`
y **solo si la tabla de usuarios está vacía**: nunca hay admin/admin por
defecto (§8.3).

## Decisión 4 — Semántica de errores para no filtrar existencia

- Comercio ajeno → `404 not_found`, **idéntico** al de un comercio
  inexistente (§8.2).
- Credenciales inválidas → `401 invalid_credentials` con mensaje idéntico
  exista o no el email, y un hash de decoy para que el tiempo de respuesta
  tampoco delate cuentas.
- Rate limiting por (IP, email): 5 intentos / 300 s → `429` con `Retry-After`.

## Decisión 5 — La interfaz nunca autoriza

Los permisos del frontend (`lib/session.ts`) sirven para **ocultar botones**;
el backend los vuelve a comprobar en cada endpoint con el contexto de sesión
(`app/api/deps.py`). Existe test negativo que lo verifica.

## Consecuencias

- Añadir un comercio al que un usuario ya pertenece con otro rol exige un
  endpoint de actualización (la restricción única `uq_merchant_user` impide
  duplicados).
- Las contraseñas usan Argon2id (2 iteraciones, 19 MiB): el login cuesta
  decenas de milisegundos a propósito.
- Un `admin` de comercio no puede crear otro `owner` ni degradar al último
  `owner` (sin propietarios, el comercio quedaría huérfano).
