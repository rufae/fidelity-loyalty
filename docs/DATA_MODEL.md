# Modelo de datos — LocalAI Fidelity

> Esquema real a 28/10/2026: **23 tablas** + `alembic_version`, con 11
> migraciones versionadas (`0001_baseline` … `0011_support`).

## Entidades

| Tabla | Rol | Notas |
|---|---|---|
| `users` | Identidad única (email + hash) | `platform_role` nullable; ver ADR-0003 |
| `merchants` | Comercio cliente | `slug` único, no es control de acceso |
| `merchant_users` | Usuario ↔ comercio con rol | Única por (usuario, comercio) |
| `sessions` | Sesiones en servidor | Revocables individualmente |
| `audit_events` | Auditoría | `metadata` con *allowlist*; email solo como hash |
| `loyalty_programs` | Programa (`stamps`) | Estados draft/active/paused/archived; `terms_version` |
| `program_rewards` | Recompensas | `stamps_required` > 0 |
| `members` | Cliente por comercio | Email opcional y único por comercio (privacidad) |
| `memberships` | Cliente ↔ programa | Token opaco único; `stamps` caché + `version` (optimista) |
| `loyalty_transactions` | **Ledger inmutable** | Cantidad con signo; `idempotency_key` única |
| `reward_redemptions` | Canjes confirmados | Referencia al movimiento |
| `wallet_passes` | Estado del pase por proveedor | `simulated` rotulado; error visible |
| `background_jobs` | Trabajos Wallet | queued/running/succeeded/failed |
| `nfc_tags` | Etiquetas lógicas | `tag_type` distingue alta vs reseñas; slug aleatorio |
| `review_destinations` | Destino oficial verificado | 1 por comercio; cambiar URL pierde verificación |
| `redirect_events` | Métrica de clics | Sin IP, sin user-agent, sin PII |
| `support_threads` | Conversación de soporte del comercio | `idempotency_key` única por comercio |
| `support_messages` | Mensajes del hilo | Texto plano; lecturas separadas comercio/plataforma |
| `support_callback_requests` | Solicitud de llamada | `phone_encrypted`; nunca se expone al comercio |
| `support_notifications` | Outbox de avisos | email/ntfy/Telegram con reintentos; `idempotency_key` única |

## Reglas de integridad

- Fechas con **zona horaria** (UTC) en todas las tablas (§11.19).
- Sin `float` para cantidades: sellos en `Integer`.
- `loyalty_transactions.idempotency_key` UNIQUE → una operación repetida no
  puede aplicarse dos veces (§16.4).
- `memberships` UNIQUE (miembro, programa) → sin dobles altas.
- `support_threads.idempotency_key` UNIQUE por comercio → reintentar la misma
  petición no duplica conversaciones.
- `support_messages.idempotency_key` UNIQUE por hilo → un mensaje repetido no
  se guarda dos veces.
- `support_notifications.idempotency_key` UNIQUE → un aviso se envía una sola
  vez por mensaje y canal.
- El teléfono de `support_callback_requests` se guarda **cifrado** en la
  aplicación; no existe como texto plano en el modelo.
- No existen claves foráneas hacia recompensas desde `nfc_tags`: la
  vinculación recompensa↔reseña **no es modelable** (§4.2).

## Deduplicación y alcance

- Toda consulta de comercio filtra por `merchant_id`; los IDs ajenos responden
  404 en la capa de API (§8.2).
- Un email repetido en el mismo comercio reutiliza el `member` pero no duplica
  la membresía del programa (409 `membership_already_exists`).
