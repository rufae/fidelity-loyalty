# ADR-0006 — Datos obligatorios del alta y consentimientos

**Fecha:** 14/10/2026 · **Estado:** aceptado (requisito comercial del producto)

## Contexto

El alta actual era de datos mínimos (nombre y email opcionales). El nuevo
requisito comercial exige que el cliente introduzca **nombre completo y correo
electrónico** al darse de alta desde la etiqueta NFC, además de aceptar
condiciones y el aviso de privacidad. Esto aumenta la responsabilidad sobre
datos personales.

## Decisión

1. **Nombre completo y email obligatorios** en toda alta nueva (validación en
   frontend y backend; el backend es autoridad).
2. **Email normalizado** (`trim` + minúsculas) para duplicados y búsquedas, sin
   asumir identidad global entre comercios (el aislamiento por comercio se
   mantiene).
3. **Unicidad**: un email no puede crear dos membresías en el mismo programa
   del mismo comercio (responde 409 `membership_already_exists` sin revelar
   datos de la tarjeta existente).
4. **Consentimientos separados y registrados**:
   - condiciones del programa: versión + fecha (ya existía);
   - aviso de privacidad: se registra su versión (`privacy_notice_version`);
   - marketing: opcional, **desmarcado por defecto**, se persiste la elección.
5. **Compatibilidad**: las membresías históricas sin nombre/email siguen
   siendo válidas (columnas siguen permitiendo `NULL`); solo las altas nuevas
   exigen datos.
6. **Verificación de email**: **no** se exige en el piloto (evita fricción y no
   hay proveedor transaccional configurado). Se documenta como decisión
   reversible y se prevé recuperación de acceso en una fase posterior.

## Consecuencias

- Sube el nivel de exigencia de privacidad: aviso visible en el alta,
  política de retención y derechos ARCO antes de datos reales (ya reflejado en
  `docs/PRIVACY.md`).
- El QR de la tarjeta sigue sin contener PII (solo URL con token opaco).
