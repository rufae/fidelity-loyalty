# Despliegue — LocalAI Fidelity

## 1. Desarrollo local

```bash
cp .env.example .env      # credenciales de desarrollo rotuladas en el propio fichero
docker compose up --build
```

| Servicio | URL |
|---|---|
| Web | http://localhost:8100 |
| API | http://localhost:8101 |
| PostgreSQL | localhost:5434 |
| `/go/{slug}` | http://localhost:8100/go/{slug} (proxy de la web) |

La API ejecuta `alembic upgrade head` al arrancar: el esquema siempre está
actualizado. El volumen `pgdata` persiste los datos entre reinicios (verificado
con `down`+`up`).

## 2. Copia de seguridad y restauración (§18.4)

```bash
scripts/backup.sh /ruta/de/copias        # volcado custom comprimido + poda
BACKUP_KEEP=30 scripts/backup.sh         # más historia
scripts/restore.sh <fichero.dump> localai_fidelity_restore_check   # prueba aislada
```

- El script **falla ruidosamente** si el volcado sale vacío.
- **Restauración probada** (12/10/2026): volcado → BD de prueba → 17 tablas
  idénticas en origen y destino.
- Pendiente operativo: agendar el script con cron/systemd y el aviso de fallo
  del temporizador (correo/ntfy).

## 3. Antes de publicar a terceros

Checklist obligatorio (§18.2, §16):

1. **HTTPS**: la cookie de sesión es `Secure` en producción; por HTTP el
   login no funciona.
2. **Dominio propio** y proxy inverso (nginx/caddy) delante de la web.
3. `AUTH_SESSION_SECRET` y credenciales de semilla **generadas** (no las de
   desarrollo). Producción no arranca sin ellas (fail-closed).
4. Revisar `docs/SECURITY.md` §8 (CSP con nonces, retención ejecutada).
5. Copias agendadas dentro de tu política de respaldo.
6. Revisión jurídica antes de operar con datos reales de clientes.

## 4. Variables de entorno

Ver `.env.example`. Ninguna es imprescindible para usar el producto completo:
el proveedor de Wallet es simulado por defecto (ADR-0002). Las credenciales
Apple/Google se añaden únicamente al activar las FASES 7/8 reales
(`docs/WALLET_INTEGRATIONS.md`).

## 5. n8n (futuro)

No hay automatizaciones externas hoy. Si se añaden, irán detrás del perfil
`automation` de compose y nunca expuestas a Internet (§16.4 de la especificación).
