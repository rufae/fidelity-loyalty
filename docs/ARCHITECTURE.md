# Arquitectura — LocalAI Fidelity

## 1. Componentes

```text
apps/web (Next.js 16 + TS + Tailwind)        services/api (FastAPI + SQLAlchemy 2)
├── /login                ── cookie ───────▶  /api/v1/auth/*
├── /merchants            ── rewrites ─────▶  /api/v1/platform/merchants
├── /merchants/{id}/*     (panel del comercio) /api/v1/merchants/{id}/*
├── /p/{m}/{p}  (alta pública)               /api/v1/public/*
├── /card/{token} (tarjeta del cliente)      /api/v1/public/memberships/*
└── /go/{slug}  (etiquetas) ── rewrite ────▶  /go/{slug}
                                             └── PostgreSQL 15 (volumen pgdata)
```

- El navegador **solo** habla con la web; esta proxifica la API (nunca hay
  secretos ni acceso directo a la BD en el frontend, §10.5).
- `/go/{slug}` está en la raíz porque es la URL impresa en las etiquetas.

## 2. Capas del backend

| Capa | Contenido | Regla |
|---|---|---|
| `app/api/*` | Routers: permisos, códigos HTTP, auditoría | El rol sale de la sesión, nunca del body |
| `app/services/*` | Lógica de negocio (loyalty, ledger, members, nfc, wallet, dashboard) | Sin HTTP; recibe `Session` |
| `app/domain/*` | Roles, errores de dominio, tokens | Sin dependencias de infraestructura |
| `app/models/*` | ORM (SQLAlchemy 2 tipado) | Migraciones con Alembic |
| `app/integrations/*` | Adaptadores de Wallet (simulado/apple/google) | El dominio no conoce al proveedor |

## 3. Flujos principales

**Fidelización (fuente de verdad: ledger):**
alta pública → `memberships` (token opaco) → `earn` idempotente →
`loyalty_transactions` (+) → caché `memberships.stamps` → `redeem` transaccional →
`reward_redemptions` → actualización de Wallet (trabajo, nunca revierte el ledger).

**Reseñas (independiente):**
URL oficial guardada → verificación manual con fecha → etiqueta `/go/{slug}` →
302 al destino + `redirect_events` (sin PII).

## 4. Soporte B2B

Flujo privado entre el comercio y la plataforma (Plan.md):

```text
Comercio crea conversación → support_threads + support_messages
        ↓ misma transacción
support_notifications (outbox: email/ntfy/Telegram)
        ↓ worker con reintentos
Buzón de plataforma → respuesta → aviso al comercio
```

- **Solo usuarios autenticados** de comercio (`owner`, `admin`, `staff`); `staff`
  solo ve sus hilos. La plataforma ve todos.
- El teléfono de una solicitud de llamada se guarda **cifrado**
  (`app/core/crypto.py`) y solo se descifra en el buzón de plataforma.
- El outbox `support_notifications` usa `UPDATE` condicional al reclamar cada
  aviso: funciona con varios nodos sin duplicar envíos.
- Los avisos externos son opcionales; el buzón interno es la fuente de verdad.
- No hay telefonía integrada: la llamada se acuerda fuera de la aplicación.

## 5. Decisiones documentadas

- `docs/ADR/0001-stack-y-estructura.md`
- `docs/ADR/0002-entornos-puertos-y-wallet-simulado.md`
- `docs/ADR/0003-identidad-y-autenticación.md`

## 6. Pendientes explícitos

- Worker en segundo plano real (hoy el trabajo Wallet se ejecuta de forma
  síncrona-simple con estado persistido; el modelo ya lo soporta).
- Retención física de datos (el borrado de miembros es lógico).
- CSP con nonces (render dinámico).
