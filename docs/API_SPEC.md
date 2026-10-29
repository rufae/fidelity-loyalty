# API — contratos implementados

> Prefijo `/api/v1` salvo `/health`, `/ready` y `/go/{slug}` (raíz).
> Errores de dominio: `{"detail": {"code": "...", "message": "..."}}`.
> Las mutaciones exigen `application/json` (415 en caso contrario).

## Autenticación

```text
POST   /api/v1/auth/login      {email, password} → cookie lf_session (HttpOnly)
POST   /api/v1/auth/logout     revoca la sesión en servidor
GET    /api/v1/auth/me         identidad + comercios visibles (401 sin sesión)
```

## Plataforma (solo platform_owner/admin)

```text
GET    /api/v1/platform/merchants
POST   /api/v1/platform/merchants        {name, owner_email, owner_password}
GET    /api/v1/platform/merchants/{id}
PATCH  /api/v1/platform/merchants/{id}
POST   /api/v1/platform/merchants/{id}/suspend | /activate
```

## Comercio (rol requerido por endpoint)

```text
GET    /api/v1/merchants                       comercios de la sesión
GET    /api/v1/merchants/{id}                  (lectura: owner/admin/staff/viewer)
PATCH  /api/v1/merchants/{id}                  (admin)
GET    /api/v1/merchants/{id}/users            (admin)
POST   /api/v1/merchants/{id}/users            (admin; sin crear otro owner)
PATCH  /api/v1/merchants/{id}/users/{user_id}  (admin; protege al último owner)
```

## Programas (admin del comercio)

```text
GET    /api/v1/merchants/{id}/programs
POST   /api/v1/merchants/{id}/programs         {name, description?, terms?}
GET    /api/v1/merchants/{id}/programs/{pid}
PATCH  /api/v1/merchants/{id}/programs/{pid}   (cambiar terms incrementa terms_version)
POST   /api/v1/merchants/{id}/programs/{pid}/publish | /pause | /archive
GET|POST /api/v1/merchants/{id}/programs/{pid}/rewards
PATCH  /api/v1/merchants/{id}/programs/{pid}/rewards/{rid}
GET    /api/v1/merchants/{id}/memberships?q=   tarjetas (filtro por nombre/correo)
GET    /api/v1/merchants/{id}/members        clientes del comercio
```

## Públicos (rate limit por IP)

```text
GET  /api/v1/public/programs/{merchant}/{program}                 condiciones vigentes
POST /api/v1/public/programs/{merchant}/{program}/enroll          alta (201 + token)
GET  /api/v1/public/memberships/{token}                           tarjeta web
GET  /api/v1/public/memberships/{token}/qr                        QR de la tarjeta
```

## Operaciones (staff+) y ajustes (admin)

```text
POST /api/v1/merchants/{id}/memberships/lookup                  {token}
GET  /api/v1/merchants/{id}/memberships/search?q=               nombre/correo (auditado)
GET  /api/v1/merchants/{id}/members/{member_id}/cards           todas las tarjetas del cliente
POST /api/v1/merchants/{id}/memberships/{mid}/earn              {quantity, idempotency_key}
POST /api/v1/merchants/{id}/memberships/{mid}/redeem            {reward_id, idempotency_key}
POST /api/v1/merchants/{id}/memberships/{mid}/adjust            {delta, reason}   (admin)
GET  /api/v1/merchants/{id}/memberships/{mid}/transactions
GET  /api/v1/merchants/{id}/memberships/{mid}/qr
POST /api/v1/merchants/{id}/memberships/{mid}/wallet/issue      → 202 + job
GET  /api/v1/merchants/{id}/wallet/passes | /wallet/jobs        (admin)
```

Las respuestas de tarjeta incluyen `member_name`, `member_email` y
`program_name` (identidad mínima para el mostrador, §13.5). La búsqueda por
nombre/correo queda registrada en la auditoría (`member.searched`, con hash
del término, sin PII).

## NFC y reseñas (admin)

```text
GET|PUT  /api/v1/merchants/{id}/review-destination
POST     /api/v1/merchants/{id}/review-destination/verify
GET|POST /api/v1/merchants/{id}/nfc-tags                        (extra=forbid)
PATCH    /api/v1/merchants/{id}/nfc-tags/{tag_id}
GET      /api/v1/merchants/{id}/nfc-tags/{tag_id}/qr
GET      /api/v1/merchants/{id}/nfc/stats                       review_link_clicks, counter_clicks…
GET      /go/{public_slug}                                      302 al destino guardado
```

Tipos de etiqueta: `loyalty_signup` (alta, abre `/p/{comercio}/{programa}`),
`counter` (mostrador: abre `/merchants/{id}/operations?program=…` para el
personal, ADR-0008) y `google_review` (solo con el enlace verificado). Los
clics se cuentan por tipo: `loyalty_signup_clicks`, `counter_clicks`,
`review_link_clicks`; ninguno es una reseña publicada.

## Analítica y exportación (admin)

```text
GET /api/v1/merchants/{id}/dashboard/summary
GET /api/v1/merchants/{id}/dashboard/loyalty?period=7|30|90
GET /api/v1/merchants/{id}/export/members.csv
```

## Soporte B2B (privado, Plan.md §9)

```text
# Comercio (owner/admin/staff; staff solo sus hilos)
GET    /api/v1/merchants/{id}/support
POST   /api/v1/merchants/{id}/support                          Idempotency-Key opcional
GET    /api/v1/merchants/{id}/support/unread-count
GET    /api/v1/merchants/{id}/support/{thread_id}
POST   /api/v1/merchants/{id}/support/{thread_id}/messages      Idempotency-Key opcional
POST   /api/v1/merchants/{id}/support/{thread_id}/callback-requests
POST   /api/v1/merchants/{id}/support/{thread_id}/close
POST   /api/v1/merchants/{id}/support/{thread_id}/read

# Plataforma (solo platform_owner/platform_admin)
GET    /api/v1/platform/support/threads
GET    /api/v1/platform/support/threads/{thread_id}
POST   /api/v1/platform/support/threads/{thread_id}/messages
PATCH  /api/v1/platform/support/threads/{thread_id}
POST   /api/v1/platform/support/threads/{thread_id}/callback-requests/{request_id}/mark-called
POST   /api/v1/platform/support/threads/{thread_id}/read
GET    /api/v1/platform/support/unread-count
POST   /api/v1/platform/support/notifications/{notification_id}/retry
```

- `staff` solo ve las conversaciones que ha creado; `viewer` no accede.
- El teléfono de llamada solo se devuelve en el detalle de plataforma; el
  comercio solo ve el estado de su solicitud.
- `Idempotency-Key` evita duplicar conversaciones, mensajes y solicitudes.
- Límites por día: conversaciones, mensajes y solicitudes de llamada (`429`).
- Los avisos externos (email/ntfy/Telegram) se registran en un outbox y se
  reintentan; nunca bloquean la conversación.

## Códigos de error de dominio

`invalid_credentials`, `login_rate_limited`, `program_not_active`,
`program_terms_required`, `invalid_program_transition`, `membership_already_exists`,
`membership_not_found`, `membership_inactive`, `insufficient_stamps`,
`reward_not_available`, `duplicate_operation`, `wallet_provider_not_configured`,
`tag_disabled`, `tag_not_found`, `review_destination_not_verified`,
`invalid_review_url`, `review_destination_required`, `not_found`,
`support_rate_limited`, `support_thread_closed`, `support_thread_not_found`,
`notification_delivery_failed`, `notification_not_configured`.

> Un recurso ajeno responde **igual** que uno inexistente (`404 not_found`),
> para no permitir enumeración (§8.2).
