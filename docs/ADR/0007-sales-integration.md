# ADR-0007: integración con LocalAI Sales por API autenticada

- **Fecha:** 14/10/2026
- **Estado:** aceptado e implementado (ambos repositorios)
- **Contexto:** AGENTS.md §2 prevé que LocalAI Sales (prospección/CRM interno)
  y LocalAI Fidelity (plataforma de fidelización que se vende a los comercios)
  se integren «cuando tenga sentido», **sin compartir base de datos ni copiar
  lógica**. El propietario ha decidido activar esa integración ahora.

## Decisión

La integración es **un cliente HTTP de esta plataforma desde el backend de
LocalAI Sales**, en la dirección Sales → Fidelity. Nunca al revés y nunca una
conexión a la base de datos.

1. **Superficie usada** (ya existente, sin cambios en esta API):
   - `POST /api/v1/auth/login` con un **usuario de plataforma dedicado**.
   - `POST /api/v1/platform/merchants` (alta del comercio con su propietario).
   - `GET /api/v1/platform/merchants/{id}` (comprobación del vínculo).
   - `GET /api/v1/merchants/{id}/dashboard/summary` (agregados reales).
   Un admin de plataforma puede operar cualquier comercio (§8.1), así que no
   hacen falta permisos nuevos ni endpoints de integración específicos.
2. **Autenticación**: credenciales del usuario de plataforma en las variables
   `FIDELITY_*` del `.env` de Sales (fail-closed: `FIDELITY_PROVIDER=api` sin
   configuración completa no arranca). La cookie de sesión vive solo en
   memoria y se renueva una vez ante un 401.
3. **Qué cruza la frontera**: solo datos de **nivel comercio** — nombre, slug,
   estado y agregados (clientes registrados, tarjetas activas, sellos,
   canjes y clics al enlace de reseñas). **Nunca** datos personales de
   clientes, tokens de tarjeta, movimientos ni credenciales de los comercios.
4. **Dónde vive el vínculo**: en Sales, tabla `provider_references`
   (`provider="localai_fidelity"`, `provider_entity_id` = id del comercio),
   el mismo patrón que el `place_id` de Google. Cada operación queda en el
   historial de actividad del negocio.
5. **Desvincular no borra**: quita el enlace del CRM; el comercio de Fidelity
   se gestiona desde su propio panel (baja incluida).
6. **Simulado por defecto**: `FIDELITY_PROVIDER=simulated` (tests/desarrollo)
   devuelve comercios con prefijo `sim-` para que no se confundan con reales.

## Alternativas descartadas

- **Compartir base de datos**: violaría el aislamiento de productos (AGENTS.md
  §2 de Fidelity) y acoplaría migraciones y datos de clientes.
- **Fidelity consulta a Sales**: el flujo comercial va de la prospección al
  cliente; además Sales guarda datos internos de ventas que no deben exponerse.
- **Webhooks en tiempo real**: innecesarios para la fase actual; el panel lee
  los agregados bajo demanda. Puede añadirse después sin romper el contrato.
- **Endpoint/API-key nueva en Fidelity**: ampliaría la superficie de ataque sin
  necesidad; un usuario de plataforma dedicado ya cumple y su actividad es
  auditable en el registro de auditoría de Fidelity.

## Consecuencias

- Sales depende de la disponibilidad de Fidelity para mostrar el panel: los
  fallos se traducen a `502/503` con códigos estables y la UI ofrece reintento.
- Rotar la contraseña del usuario de plataforma exige actualizar el `.env` de
  Sales y reiniciar su API.
- Si la integración crece (migración de tarjetas, campañas…), exigirá un ADR
  nuevo: el alcance actual es alta/vínculo/estado/desvinculación.
