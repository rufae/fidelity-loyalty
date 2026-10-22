# Integraciones Wallet — estado y requisitos

## 1. Estado actual (12/10/2026)

| Proveedor | Estado | Comportamiento |
|---|---|---|
| `simulated` (defecto) | ✅ operativo | Emite pases ficticios persistidos, **rotulados `simulated`** en API e interfaz (§17.2) |
| `apple` | ⛔ `not_configured` | Devuelve error documentado; no finge emisiones |
| `google` | ⛔ `not_configured` | Devuelve error documentado; no finge emisiones |

La fidelización **no depende** de Wallet: el ledger es la fuente de verdad y
un fallo de proveedor deja el trabajo fallido visible y reintenable sin tocar
los sellos (§6.1, §15). Prueba automatizada:
`test_el_rollback_de_wallet_no_reviente_el_ledger`.

## 2. Arquitectura

```
app/integrations/wallet/
├── base.py       # interfaz WalletProvider + PassResult + estados
├── simulated.py  # proveedor por defecto (sin credenciales)
├── apple.py      # FASE 7: emisión real cuando existan certificados
└── google.py     # FASE 8: emisión real cuando exista cuenta de servicio
```

La emisión/actualización es un **trabajo** (`background_jobs`) con estado,
intentos y error visible en `/merchants/{id}/wallet/jobs` (§15).

## 3. Qué hace falta para activar Apple Wallet (FASE 7)

1. Cuenta de desarrollador Apple y **Pass Type ID** aprobado.
2. Certificado de Pass Type ID + clave privada, y certificado intermedio WWDR.
3. `APPLE_PASS_TYPE_IDENTIFIER`, `APPLE_TEAM_IDENTIFIER`,
   `APPLE_PASS_CERT_PATH`, `APPLE_WWDR_CERT_PATH` (+ contraseña si aplica).
4. Para pases **actualizables**: servicio web por HTTPS público y APNs.
5. Revisar la documentación vigente:
   https://developer.apple.com/documentation/walletpasses

Con esas credenciales se implementará la generación y firma del `.pkpass` y el
servicio de actualización; hoy el adaptador lo deja explícito en su docstring.

## 4. Qué hace falta para activar Google Wallet (FASE 8)

1. **Issuer ID** de la cuenta de desarrollador.
2. Cuenta de servicio con permiso sobre Google Wallet API (clave JSON).
3. `GOOGLE_WALLET_ISSUER_ID` y `GOOGLE_WALLET_SERVICE_ACCOUNT_JSON` (solo en
   backend o gestor de secretos; nunca en el frontend).
4. Revisar: https://developers.google.com/wallet/retail/loyalty-cards

## 5. Reglas irrenunciables

- Ninguna clave o certificado en el repositorio ni en el navegador (§16.1).
- Un proveedor deshabilitado no rompe el resto de la aplicación (test:
  `test_proveedor_sin_configurar_no_rompe_y_deja_error_visible`).
- La UI nunca presenta un pase simulado como emitido.
