# Seguridad — LocalAI Fidelity

> Refleja la implementación real a 12/10/2026 (FASE 12). Nada de este
> documento es «pendiente disfrazado»: lo no implementado se marca como tal.

## 1. Identidad y sesiones (ADR-0003)

| Control | Cómo |
|---|---|
| Hash de contraseñas | Argon2id (2 iteraciones, 19 MiB, 1 hilo) vía `argon2-cffi` |
| Sesión | Cookie `lf_session` = `<id>.<HMAC-SHA256>`, `HttpOnly`, `SameSite=Lax`, `Secure` en producción |
| Invalidación | Tabla `sessions`: logout y cambio de contraseña revocan en servidor |
| Fail-closed | Producción sin `AUTH_SESSION_SECRET`/semilla **no arranca** (validador de settings) |
| Rate limiting | Login 5 intentos / 300 s por (IP, email) → `429` + `Retry-After` |
| Sin enumeración de cuentas | Respuesta idéntica exista o no el email; hash de decoy para igualar tiempos |
| Semilla | `AUTH_BOOTSTRAP_*` solo crea el primer admin **si la tabla está vacía** |

## 2. Aislamiento multiempresa (§8.2)

- Toda ruta de comercio pasa por `merchant_access(...)`: el rol sale de la
  sesión, nunca de un parámetro del cliente.
- Comercio ajeno → `404` **idéntico** al inexistente (sin enumeración).
- Pruebas negativas obligatorias en `tests/test_isolation.py` y
  `tests/test_e2e_flow.py` (A↔B en CRUD, membresías, operaciones, analítica).
- Un `admin` no crea `owner` ni degrada al último `owner` (sin huérfanos).

## 3. Protección de operaciones de saldo (§16.4)

- `idempotency_key` **única** en `loyalty_transactions`: repetir una petición
  devuelve el mismo movimiento (`already_applied=true`).
- Canje transaccional con `SELECT ... FOR UPDATE` sobre la membresía +
  verificación de saldo dentro de la transacción (sin doble gasto).
- El ledger es inmutable: las correcciones son `adjustment`/`reversal` con
  motivo y actor. No existe endpoint de borrado de movimientos.
- Un fallo de Wallet **no revierte** el ledger (probado en
  `test_el_rollback_de_wallet_no_reviente_el_ledger`).

## 4. Endpoints públicos

| Riesgo | Control |
|---|---|
| Alta pública masiva | Rate limit por IP (30/min) en `/enroll` |
| Enumeración de membresías | Token opaco de 256 bits; respuesta uniforme |
| *Open redirect* en `/go/{slug}` | Solo resuelve al destino guardado; `?url=` se ignora (testeado) |
| Redirección sin verificar | Destino de reseñas sin verificar → `404 review_destination_not_verified` |
| Etiqueta perdida/robada | `PATCH status=disabled` → `410` con página neutral, sin redirigir |
| CSRF | Cookie `SameSite=Lax` + mutaciones solo con `application/json` (415 si no) |

## 5. Google Reviews (§4.2) — verificado por tests

- El esquema de creación de etiquetas tiene `extra="forbid"`: un campo tipo
  `reward_id` o `incentive` en una etiqueta de reseñas es **422**, no un dato
  ignorado (`test_no_se_puede_crear_una_etiqueta_con_incentivo`).
- El mismo destino se sirve con cualquier parámetro: no hay filtro por
  satisfacción (`test_no_filtrado_por_satisfaccion`).
- La métrica se llama `review_link_clicks`; no existe ninguna métrica
  «reseñas recibidas» ni «valoración».
- `redirect_events` no guarda IP, user-agent ni identidad del cliente.

## 6. Secretos

- Solo en `.env` (gitignored). `.env.example` trae credenciales de
  **desarrollo local** claramente rotuladas; en producción se generan con
  `openssl rand`.
- El escáner previo a cada commit no detecta secretos reales en el repo.
- Los certificados Apple/Google (FASE 7/8) se montarán como ficheros o
  gestor de secretos, nunca en el repositorio ni en el frontend.

## 7. Cabeceras y navegador

- API: `X-Content-Type-Options`, `X-Frame-Options: DENY`, `Referrer-Policy`,
  `Cache-Control: no-store`, `X-Request-ID` (correlación).
- Web: CSP con solo orígenes propios (`script-src 'unsafe-inline'` necesario
  por el arranque en línea de Next; pendiente de nonces con render dinámico),
  `Permissions-Policy` con `camera=(self)` (la cámara solo se usa en la
  pantalla de escaneo del personal, nunca en páginas públicas) y micrófono y
  geolocalización denegados.

## 8. Pendiente antes de publicar a terceros (no bloquea el uso local)

1. HTTPS obligatorio (la cookie `Secure` lo exige en producción).
2. CSP con nonces (render dinámico) para eliminar `unsafe-inline`.
3. Revisión jurídica de la base jurídica del tratamiento de clientes.
4. Retención ejecutada (hoy el borrado de miembros es lógico, no físico).
5. Copias agendadas con aviso de fallo (el procedimiento está probado).


## 9. Endurecimiento de la sesión de cierre (18/10/2026)

- **Correo transaccional con TLS**: la API no arranca en producción sin
  `EMAIL_SMTP_STARTTLS=true` o `EMAIL_SMTP_SSL=true`, y el envío usa un
  contexto TLS que **verifica el certificado del servidor** (un STARTTLS sin
  contexto admite intermediarios). Cubierto por `tests/test_email_smtp.py`.
- **Enlaces de un solo uso atómicos**: el canje de tokens de verificación y
  acceso es un `UPDATE … WHERE used_at IS NULL` con comprobación de filas
  afectadas; dos peticiones simultáneas no pueden canjear el mismo enlace.
  Prueba de concurrencia contra PostgreSQL en `test_postgres_concurrency.py`.
- **Credenciales de desarrollo**: los valores públicos de `.env.example`
  (sesión, bootstrap y `DATABASE_URL` local) se **rechazan al arrancar** en
  producción; el `.env` local ya no coincide con ellos (rotado). Las pruebas
  E2E leen las credenciales rotadas del `.env`, nunca de valores fijos.
- **Red local**: web, API y PostgreSQL escuchan en `127.0.0.1` por defecto;
  exponer la web a la red local exige sobrescribir `WEB_PORT` de forma
  explícita. `mailpit` (captura de correo) también vive solo en loopback.
- **Roles y pantallas**: matriz fijada en `tests/test_role_routes.py` y en el
  E2E `roles.spec.ts`; la interfaz filtra navegación y rutas, pero el backend
  responde 404 a toda operación no autorizada (control definitivo).
