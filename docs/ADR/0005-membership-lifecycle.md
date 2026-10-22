# ADR-0005 — Ciclo de vida de la membresía y de la tarjeta

**Fecha:** 14/10/2026 · **Estado:** aceptado

## Contexto

El comercio necesita controlar sus tarjetas: bloquear una tarjeta perdida,
expulsar a un cliente, reactivar tras un incidente o tramitar una supresión de
datos. Además, **las Wallet no permiten borrar remotamente** una tarjeta ya
instalada: Google no deja eliminar clases/objetos por API (solo pasarlos a
EXPIRED/INACTIVE/COMPLETED), y Apple permite actualizar/anular un pase
(voided) pero la sincronización depende del dispositivo.

## Decisión

Semántica de `Membership.status` (transiciones validadas en backend):

| Estado | Significado | Transiciones |
|---|---|---|
| `active` | Usa el programa | → suspended, revoked, deletion_pending, anonymized |
| `suspended` | Pausa temporal: no suma ni canjea | → active (reactivar), revoked, deletion_pending, anonymized |
| `revoked` | Baja definitiva del programa; bloqueo permanente | → deletion_pending, anonymized |
| `deletion_pending` | Solicitud de supresión de datos tramitándose | → `anonymized` |
| `anonymized` | PII eliminada; se conserva el ledger seudonimizado | terminal |

Reglas:

1. **El bloqueo es inmediato en backend**: suspender/revocar impide earn,
   redeem y operaciones en ese mismo momento, sin esperar a Wallet.
2. La sincronización con Wallet se intenta por trabajos (pase `voided` en
   Apple, `INACTIVE/EXPIRED` en Google) y **se registra el resultado**, sin
   prometer borrado remoto del dispositivo. La interfaz lo explica así.
3. La eliminación de datos **anonimiza** (nombre/email → vacíos, estado
   `anonymized`) y **conserva el ledger** referido a la membresía para no
   corromper la integridad contable; nunca `DELETE CASCADE` sobre movimientos.
4. Cada transición queda en `audit_events` (actor, estado anterior/nuevo,
   fecha UTC y motivo).

## Consecuencias

- La UI usa los verbos exactos: «Suspender», «Reactivar», «Revocar tarjeta»
  y «Eliminar cliente» (nunca un «Eliminar tarjeta» ambiguo: la tarjeta se
  revoca con datos intactos; los datos se eliminan con «Eliminar»).
- Las operaciones de mostrador muestran el estado y desactivan las acciones
  prohibidas con el motivo visible.

**Enmienda (20/10/2026):** el panel ejecuta la supresión **en un solo paso**
(`anonymize` accesible desde cualquier estado vivo): un «Eliminar» que solo
registraba una solicitud confundía al comercio, y además la lista de clientes
**excluye** las membresías `anonymized`, de modo que el cliente borrado
desaparece de la vista (el ledger permanece). `deletion_pending` y su
endpoint se conservan para la vía API en dos pasos y para registros
históricos; en esos casos la fila sigue visible hasta completar la
anonimización.
