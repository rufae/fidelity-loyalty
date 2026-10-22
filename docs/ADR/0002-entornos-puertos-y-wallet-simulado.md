# ADR-0002 — Entornos, puertos y Wallet simulado por defecto

- **Estado:** Aceptado
- **Fecha:** 2026-10-12 (FASE 0)
- **Contexto:** §16.1, §17.2, §18 de `AGENTS.md`; entorno real inspeccionado
  el 12/10/2026.

## Decisión 1 — Puertos locales reservados

Para poder levantar `localai-sales` y `localai-fidelity` a la vez:

| Servicio | Puerto | Estado el 12/10/2026 |
|---|---|---|
| Web (Next.js) | **8100** | libre |
| API (FastAPI) | **8101** | libre |
| PostgreSQL | **5434** | libre |
| n8n (perfil opcional) | 5680 | libre |

Ocupados y no tocables: 8090/8091/5433 (localai-sales), 5432 (PostgreSQL
genérica), 3000/3001/3002/5678/6379 y demás servicios del equipo.

## Decisión 2 — Wallet simulado por defecto

- `WALLET_PROVIDER=simulated` es el valor por defecto en desarrollo, tests y
  demo: **el producto completo es usable sin ninguna credencial**.
- El proveedor simulado debe rotularse `SIMULATED` en UI y logs (§17.2): nunca
  puede confundirse con una tarjeta emitida realmente.
- Los adaptadores Apple (FASE 7) y Google (FASE 8) se implementan **detrás de
  la interfaz** `WalletProvider` y quedan `not_configured` hasta provisionar
  credenciales reales. Su ausencia **no bloquea** ninguna operación de
  fidelización (§10.3).

## Decisión 3 — Nada se publica en Internet sin autorización explícita

- No se abren puertos, túneles ni `tailscale funnel` sin decisión expresa del
  usuario (§18.2).
- Las fases 0-12 se validan en local/red interna. La exposición pública
  (alta de clientes reales, `/go/{slug}`, actualizaciones de Wallet) exige
  dominio + TLS y el checklist de `docs/DEPLOYMENT.md`, y se planifica como
  tarea propia dentro de la FASE 12.

## Consecuencias

- Todo el flujo (alta → sellos → canje → QR → reseñas) se puede construir y
  probar antes de gastar en dominio, certificados o cuentas de desarrollador.
- El coste inicial del stack es 0 € en software; los costes reales (dominio,
  certificados, cuotas de proveedores) se declaran en §17.1 cuando toque.
