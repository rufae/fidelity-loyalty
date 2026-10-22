# Estrategia de pruebas

## 1. Suites

| Suite | Herramienta | Cantidad (14/10/2026) | Corre sin credenciales |
|---|---|---|---|
| Backend | pytest (SQLite en memoria por prueba) | **131** | ✅ |
| PostgreSQL real | pytest, marcador `pg` (`tests/test_postgres_concurrency.py`) | **3** | ✅ (BD local) |
| Frontend | Vitest | **32** | ✅ |
| E2E de dominio | pytest (`tests/test_e2e_flow.py`) | 2 | ✅ |
| E2E de navegador | Playwright (`apps/web/e2e/flow.spec.ts`, `npm run e2e`) | **3** | ✅ (pila levantada) |
| Migraciones | `alembic upgrade head` en el arranque del contenedor | 8 revisiones | ✅ |

Gates obligatorios antes de dar por terminada cualquier tarea:
`ruff format` · `ruff check` · `mypy --strict` · `pytest` · `eslint` ·
`tsc --noEmit` · `vitest` · `next build`.

## 2. Qué cubre el backend

- **Aislamiento multiempresa** (`test_isolation.py`, `test_e2e_flow.py`):
  comercio A↔B en CRUD, membresías, operaciones, etiquetas y analítica.
- **Auth** (`test_auth.py`): cookie, rate limiting, invalidación de sesiones,
  fail-closed en producción, sin enumeración de emails, auditoría.
- **Ledger** (`test_ledger.py`): idempotencia, doble gasto, saldo insuficiente,
  programa pausado, permisos de ajuste, reconciliación con el historial.
- **Wallet** (`test_wallet.py`, `test_jobs.py`, `test_pkpass.py`,
  `test_google_wallet.py`): simulado rotulado, proveedor sin configurar,
  trabajos fallidos visibles y **rollback que no revierte el ledger**;
  reintentos con backoff y dead-letter; `.pkpass` firmado con certificado de
  prueba y JWT de Google con clave de prueba (sin credenciales reales).
- **Ciclo de vida** (`test_lifecycle.py`): suspender/reactivar/revocar,
  eliminar en un paso (anonimización directa) y solicitud en dos vía API,
  con transiciones validadas, bloqueo inmediato de earn/redeem, exclusión de
  los clientes eliminados de las listas, roles y aislamiento.
- **Alta** (`test_members.py`): nombre completo y email obligatorios,
  normalización, duplicados por comercio/programa, consentimientos persistidos
  y compatibilidad con membresías históricas.
- **Concurrencia real** (`test_postgres_concurrency.py`, marcador `pg`):
  doble canje simultáneo (201/409), earn con la misma clave sin duplicar
  (restricción de BD) y revocación en carrera con earn.
- **NFC/Reseñas** (`test_nfc_reviews.py`): redirect verificado, sin *open
  redirect*, sin filtro de satisfacción, esquema sin campos de incentivo,
  métrica `review_link_clicks`, etiqueta desactivada con 410.
- **E2E** (`test_e2e_flow.py`): recorrido completo §19.3 con auditoría final.

## 3. Qué cubre el frontend

Clasificación de estados de servicio, permisos de interfaz (que **solo**
ocultan botones), claves idempotentes únicas, etiquetas de estado y extracción
del código de tarjeta desde la URL que codifica el QR.

## 4. Qué NO está cubierto todavía

- Emisión e instalación de pases Wallet **reales**: imposible sin credenciales
  y dispositivos (§19.5); los generadores (`.pkpass`, JWT de Google) están
  cubiertos con credenciales de prueba.
- El estado «escaneando» del escáner QR con una cámara física: verificado a
  mano con un stream simulado; falta comprobarlo en mostrador real.
- Pruebas de accesibilidad automatizadas (axe): se revisa a mano (teclado,
  foco, contraste, `aria-live`).
