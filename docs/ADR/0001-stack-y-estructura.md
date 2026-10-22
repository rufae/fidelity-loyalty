# ADR-0001 — Stack y estructura del monorepo

- **Estado:** Aceptado
- **Fecha:** 2026-10-12 (FASE 0)
- **Contexto:** §10 de `AGENTS.md`

## Decisión

Monorepo `localai-fidelity` con la estructura de §10.4:

| Capa | Elección |
|---|---|
| Frontend | Next.js + React + TypeScript + Tailwind (+ shadcn/ui o equivalente accesible) |
| Backend | Python 3.12 + FastAPI + Pydantic |
| Persistencia | PostgreSQL 15 + SQLAlchemy 2 + Alembic |
| Tareas asíncronas | `background_jobs` en PostgreSQL + worker sencillo (sin Redis ni colas externas) |
| Pruebas | pytest (backend) · Vitest (frontend) · Playwright solo para E2E clave |
| Calidad | ruff, ruff format, mypy --strict, eslint, tsc |
| Contenedores | Docker + Docker Compose |

## Consecuencias

- Coherente con `localai-sales`: se reutilizan convenciones, gates de calidad y
  patrones ya probados (cookie de sesión, validación de URL/SSRF, scripts de
  backup). **No** se copia código sin revisarlo: son dominios distintos.
- Sin dependencias de infraestructura nuevas (no Redis, no Kubernetes, no
  microservicios) hasta que exista una necesidad real (§10.2).

## Alternativas descartadas

- *Un solo repo con localai-sales*: dominios, datos y responsables distintos;
  el producto que se vende debe desplegarse y escalarse por separado.
- *Django/DRF u otro backend*: no aporta frente a la experiencia ya consolidada.
- *Cola externa (Redis/RabbitMQ)*: complejidad prematura; §15 basta con
  trabajos persistidos y reintentos.
