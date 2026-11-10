# LocalAI Fidelity

Plataforma SaaS multiempresa de **fidelización digital** para pequeños y
medianos negocios (cafeterías, restaurantes, peluquerías, tiendas…): crea un
programa de **sellos**, registra a los clientes con una **tarjeta digital**,
suma y canjea en el mostrador, y genera además **etiquetas NFC/QR
independientes** que llevan al cliente a la ficha oficial de **reseñas de
Google** del negocio.

La tarjeta vive hoy en la web del cliente (con su QR personal y su progreso
de sellos). La emisión de pases nativos de **Apple Wallet y Google Wallet
está implementada en código** y se activa configurando las credenciales de
esas plataformas; mientras tanto, la interfaz lo rotula honestamente como
modo de demostración.

> Especificación completa (producto, seguridad, privacidad, fases): **[AGENTS.md](./AGENTS.md)**.
> Documentación técnica: [`docs/`](./docs/) · Plan de implementación: [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md).

**Dos reglas irrenunciables (AGENTS.md §28):**

1. El **backend es la fuente de verdad** de puntos y sellos: cada operación
   es auditable, idempotente y autorizada; una tarjeta (web o Wallet) es una
   representación sincronizada, nunca la base contable.
2. El módulo de reseñas **facilita el acceso a Google Reviews de forma
   neutral, voluntaria y sin incentivos**: nunca filtra por satisfacción ni
   condiciona recompensas a reseñas (§4.2).

---

## 1. Qué hace, paso a paso

### Para tus clientes (con su móvil, sin instalar nada)

1. **Toca una etiqueta NFC o escanea un QR** → se abre la página de alta del
   programa con la marca del comercio, sus condiciones (versionadas) y sus
   recompensas.
2. **Se registra** con nombre completo y correo (obligatorios, ADR-0006),
   aceptando las condiciones y el aviso de privacidad. El marketing es
   opcional y **desmarcado por defecto**. Recibe un email de verificación
   antes de activar la tarjeta.
3. Al confirmar el correo, se crea una sesión privada y se envía un segundo
   email con un enlace personal de un solo uso. La tarjeta muestra el saldo,
   el progreso y un **QR personal** opaco, sin datos personales.
4. Si el cliente pierde ese enlace, puede tocar la etiqueta NFC compartida
   **«Recuperar mi tarjeta»**, escribir su correo y recibir un enlace temporal.
   La etiqueta solo abre la página de recuperación: no contiene credenciales
   ni permite ver tarjetas de otros clientes.

### Para el personal del comercio (desde un móvil, tablet u ordenador)

5. En **Operaciones** identifica la tarjeta: **escaneando el QR con la
   cámara** del propio dispositivo, pegando la URL o escribiendo el código.
   Si el cliente **no tiene el móvil a mano**, busca por **nombre o correo**:
   esa búsqueda queda registrada en la auditoría del comercio (§13.5).
6. **«+1 sello»** (idempotente: repetir la petición no duplica) o **canjea**
   una recompensa (el servidor verifica el saldo: sin doble gasto ni saldos
   negativos).

### Para el administrador del comercio

7. **Programas**: crear, editar, publicar, pausar o archivar; las condiciones
   visibles se versionan y el cliente acepta la versión vigente.
8. **Clientes y tarjetas**: buscar por nombre/correo, ver historial, y
   **suspender / reactivar / revocar / solicitar eliminación / anonimizar**
   cada tarjeta con confirmación y auditoría (ADR-0005). Una tarjeta
   suspendida no puede sumar ni canjear **en el servidor**, aunque conserve
   una tarjeta antigua.
9. **Etiquetas NFC/QR** de tres tipos, visualmente separados:
   - **Alta de fidelización**: su URL abre la página de registro.
   - **Recuperar mi tarjeta**: abre la recuperación por correo, nunca una
     tarjeta o cuenta directamente.
   - **Reseñas de Google**: su URL lleva, sin filtros ni intermedios, al
     enlace oficial verificado del negocio. La plataforma mide **visitas al
     enlace** (nunca «reseñas publicadas») y **no permite** incentivos por
     reseñar: el esquema de la API rechaza esos campos por diseño.
10. **Resumen**: estadísticas reales (clientes, tarjetas activas, sellos,
   canjes, clics de etiquetas) y **exportación CSV** de clientes.

### Quién ve cada pantalla

| Rol | Pantallas |
|---|---|
| Administración de plataforma | Lista de comercios, **buzón de soporte**, panel completo de cualquier comercio y `/estado` (diagnóstico) |
| Propietario / administrador del comercio | Panel completo: Resumen, Programas, Operaciones, Clientes, NFC y QR, Reseñas y Soporte |
| Personal de mostrador | **Operaciones** (acumular y canjear) y su propio **Soporte**; la URL directa a otras secciones no las muestra |
| Solo lectura | Ficha del comercio y un aviso de alcance; sin secciones operativas ni soporte |
| Cliente final | Páginas públicas: alta (`/p/…`), tarjeta (`/card/…`), recuperación (`/my-card/…`) y el enlace de reseñas. **Nunca** el panel |

La portada `/` es pública y separa los dos recorridos (comercios → acceso;
clientes → alta/recuperación desde la etiqueta o el correo). El diagnóstico
técnico ya no vive en la portada: está en `/estado`, solo para operadores.
La interfaz oculta y redirige, pero **la API es el control definitivo**
(404 idéntico al recurso inexistente cuando el rol no permite la operación).

### Para la plataforma

11. Un administrador de plataforma crea comercios y sus propietarios, y
    supervisa cualquier panel. **Un comercio jamás ve datos de otro** (las
    pruebas lo comprueban de forma negativa A↔B).
12. En **Soporte**, cada comercio abre conversaciones privadas con la
    plataforma; el propietario responde desde el buzón y recibe avisos por
    email/ntfy/Telegram. Si el comercio pide llamada, deja un teléfono cifrado
    que solo ve la plataforma; la llamada se hace fuera de la aplicación.

### Ecosistema

LocalAI Sales (repositorio hermano) puede **crear el comercio desde su CRM**
y ver sus métricas mediante la integración por API (ADR-0007): Sales captara
al negocio y Fidelity lo opera. Nunca comparten base de datos.

---

## 2. Qué hay dentro (funcionalidad real)

| Módulo | Estado | Notas |
|---|---|---|
| Autenticación y sesiones | ✅ | Argon2id, cookie firmada y revocable, fail-closed en producción |
| Aislamiento multiempresa | ✅ | Recurso ajeno = 404 idéntico al inexistente (sin enumeración) |
| Programas de sellos + recompensas | ✅ | Condiciones versionadas, estados draft/active/paused/archived |
| Alta y acceso de clientes | ✅ | Verificación de correo, enlace personal de un uso, recuperación NFC sin enumerar cuentas |
| Ledger inmutable | ✅ | earn/redeem/adjustment/reversal, idempotencia con restricción en BD |
| Tarjeta web + QR | ✅ | QR con URL absoluta y token opaco sin PII |
| Escáner QR con cámara | ✅ | BarcodeDetector + respaldo ZXing; código manual siempre disponible |
| Ciclo de vida de tarjetas | ✅ | Suspender/reactivar/revocar/supresión/anonimización con auditoría |
| Etiquetas NFC/QR (alta, recuperación y reseñas) | ✅ | `/go/{slug}` sin open redirect; recuperación por email y desactivación con página 410 |
| Reseñas de Google | ✅ | Neutral, verificado, métrica = visitas al enlace |
| Analítica y exportación CSV | ✅ | Cifras reales, sin tokens en la exportación |
| Trabajos Wallet resilientes | ✅ | Reintentos con backoff, dead-letter, worker opt-in e reintento manual |
| Soporte B2B | ✅ | Conversaciones privadas del comercio con la plataforma, teléfono cifrado y avisos email/ntfy/Telegram |
| Generadores Apple/Google | 🟡 | `.pkpass` firmado y JWT «Save to Google Wallet» implementados y probados con credenciales de prueba; **faltan credenciales reales y validación en dispositivo** |
| Integración con LocalAI Sales | 🟡 | Por API con usuario de plataforma; simulado por defecto (ADR-0007) |
| Modo «puntos» | ⛔ | Solo sellos en el piloto (decisión documentada) |

---

## 3. Cómo se ejecuta en local

Requisitos: **Docker + Docker Compose**. No hace falta ninguna credencial:
el proveedor de Wallet es simulado por defecto (ADR-0002).

```bash
cp .env.example .env
docker compose up --build
```

| Servicio | URL |
|---|---|
| Web | http://localhost:8100 |
| API | http://localhost:8101 |
| OpenAPI | http://localhost:8101/docs |
| PostgreSQL | localhost:5434 |

Comprobación rápida:

```bash
curl -s localhost:8101/health   # {"status":"ok",...}
curl -s localhost:8101/ready    # {"status":"ready",...,"database":"ok"}
```

Desarrollo sin Docker:

```bash
# Backend (Python 3.12 + uv)
cd services/api
uv sync
uv run alembic upgrade head     # requiere PostgreSQL en :5434
uv run uvicorn app.main:app --reload --port 8101

# Frontend (Node 24)
cd apps/web
npm install
npm run dev                      # http://localhost:8100
```

### Acceso de desarrollo

`.env.example` incluye credenciales de desarrollo que crean un administrador
inicial **solo la primera vez** (tabla de usuarios vacía):

| Campo | Valor de desarrollo |
|---|---|
| URL | http://localhost:8100 |
| Email | el de `AUTH_BOOTSTRAP_EMAIL` de tu `.env` |
| Contraseña | la de `AUTH_BOOTSTRAP_PASSWORD` de tu `.env` |

**Credenciales de desarrollo rotadas**: este repositorio ya no depende de
valores fijos. `playwright.config.ts` lee las credenciales reales del `.env`
local para las pruebas E2E. En producción se generan valores propios
(`openssl rand`) y **no existe interruptor para desactivar la autenticación**:
sin `AUTH_SESSION_SECRET` la API no arranca (§16.2), y los valores de ejemplo
públicos de `.env.example` son **rechazados al arrancar** en producción
(sesión, bootstrap y `DATABASE_URL`).

### Pruebas desde el móvil (red local, con HTTPS)

La cámara (`getUserMedia`) solo funciona en un contexto seguro, es decir sobre
**HTTPS**. Para probar desde un móvil en la misma Wi‑Fi sin instalar VPN:

> **Por qué en contenedor:** el ufw del servidor bloquea todo el tráfico
> entrante excepto SSH y los puertos que publica Docker. Un proxy corriendo
> como proceso normal en el host queda bloqueado (`:8443` da timeout desde
> otro equipo), así que el proxy TLS vive en un contenedor: su publicación
> pasa por las reglas de Docker y **no hay que abrir puertos en el firewall**.

```bash
# 1) Genera el certificado autofirmado con la IP de LAN (una vez)
mkdir -p apps/web/.certs
openssl req -x509 -newkey rsa:2048 -nodes -sha256 -days 825 \
  -keyout apps/web/.certs/dev-lan-key.pem \
  -out apps/web/.certs/dev-lan-cert.pem \
  -subj "/CN=192.168.1.110" \
  -addext "subjectAltName=IP:192.168.1.110,IP:127.0.0.1,DNS:localhost"

# 2) Levanta el proxy TLS (perfil opt-in: no arranca con `docker compose up`)
docker compose --profile lan-tls up -d lan-tls
```

Y desde el móvil, con la **misma Wi‑Fi**: **`https://192.168.1.110:8443`**

- Sustituye `192.168.1.110` por la IP de este servidor en tu red
  (`ip -4 addr show | grep wlp`).
- El navegador avisará de **certificado no confiable** (es autofirmado).
  En Android/Chrome: «Avanzado → Continuar». La cámara ya funcionará porque
  la conexión es HTTPS.
- Para eliminar el aviso, instala `apps/web/.certs/dev-lan-cert.pem` como
  certificado de usuario en el móvil.
- El servicio `lan-tls` reenvía a `web:8100` dentro de la red de Docker; el
  web sigue escuchando solo en loopback y no se expone directamente.
- Detenerlo: `docker compose --profile lan-tls stop lan-tls`.
- Servidor alternativo: `node scripts/tls-proxy.mjs` (mismos ficheros, sirve
  en el puerto `8443` del host) **solo si no hay ufw filtrando**.

Si pruebas códigos QR generados con la URL pública, ajusta
`PUBLIC_BASE_URL=https://192.168.1.110:8443` en `.env` para que apunten a la
misma dirección. Todo esto es solo para desarrollo: **no se usa en producción**
(el perfil `lan-tls` no está pensado para el despliegue del HP).

### Variables de entorno

Ver [`.env.example`](./.env.example). Los secretos van siempre en `.env`
(gitignored), nunca en el repositorio, imágenes ni capturas (§16.1).

| Variable | Por defecto | Nota |
|---|---|---|
| `APP_ENV` | `development` | `production` activa el modo estricto (auth, HTTPS…) |
| `WALLET_PROVIDER` | `simulated` | `apple`/`google` exigen sus credenciales completas |
| `WALLET_WORKER_ENABLED` | `true` (en `.env.example`) | worker de reintentos de trabajos Wallet |
| `PUBLIC_BASE_URL` | ver `.env.example` | origen absoluto de los QR y las etiquetas NFC; obligatoria y `https://` en producción |
| `EMAIL_FROM` / `EMAIL_SMTP_HOST` | `mailpit` en desarrollo | SMTP transaccional: verificación de altas y recuperación de tarjetas. En producción es obligatorio **y exige TLS** (`EMAIL_SMTP_STARTTLS` o `EMAIL_SMTP_SSL`); sin SMTP la API no arranca (fail-closed) |
| `EMAIL_SMTP_PORT` | `1025` (Mailpit) / `587` real | En desarrollo el correo se captura en `http://localhost:8025` (contenedor `mailpit`) |
| `SUPPORT_NOTIFICATION_EMAIL` / `SUPPORT_FROM_EMAIL` | vacío | Correo privado del propietario y remitente genérico del soporte B2B |
| `SUPPORT_NTFY_*` / `SUPPORT_TELEGRAM_*` | desactivados | Canales de aviso opcionales; ntfy puede autoalojarse y Telegram usa un bot gratuito |
| `SUPPORT_PHONE_ENCRYPTION_KEY` | vacío | Clave para cifrar el teléfono de las solicitudes de llamada; sin ella no se guardan teléfonos |
| `SUPPORT_WORKER_ENABLED` | `false` | Worker del outbox de avisos de soporte |
| `WEB_PORT` / `API_PORT` / `DATABASE_PORT` | `127.0.0.1:8100` / `127.0.0.1:8101` / `127.0.0.1:5434` | **solo loopback por defecto** (§16.2); para probar desde el móvil en la red local hay que sobrescribir `WEB_PORT` en `.env` de forma explícita |

---

## 4. Cómo se prueba (todas las suites, sin credenciales ni Internet)

| Suite | Comando | Cubre |
|---|---|---|
| Backend (pytest) | `cd services/api && uv run pytest` | 201 pruebas: dominio, aislamiento, matriz de roles, ledger, ciclo de vida, Wallet, trabajos, `.pkpass`, JWT de Google, correo/SMTP, soporte B2B, límites públicos y regresiones de la auditoría |
| Concurrencia real (PostgreSQL) | `uv run pytest -m pg` | doble canje simultáneo, idempotencia por restricción de BD, revocación en carrera y canje concurrente de enlaces de un solo uso. Usa `PG_TEST_URL` o el `DATABASE_URL` del `.env` |
| Frontend (vitest) | `cd apps/web && npm test` | 40 pruebas de utilidades y regresiones |
| E2E de navegador (Playwright) | `cd apps/web && npm run e2e` | 14 pruebas: etiqueta NFC → alta → tarjeta → sello → canje → suspensión; escáner; etiqueta de mostrador; actualización de la tarjeta sin recargar; roles; y soporte B2B (conversación, respuesta y llamada privada). Requiere la pila levantada |

Gates de calidad:

```bash
# Backend
cd services/api && uv run ruff format . && uv run ruff check . && uv run mypy .

# Frontend
cd apps/web && npm run lint && npm run typecheck && npm run build
```

---

## 5. Estado y limitaciones honestas

| Fase | Contenido | Estado |
|---|---|---|
| 0-12 | Producto completo (especificación en `AGENTS.md`) | ✅ |
| Producción | Ciclo de vida de tarjetas, alta obligatoria, trabajos resilientes, generadores Wallet, escáner, E2E, concurrencia PG | ✅ |
| Wallet real | Emisión con credenciales Apple/Google y validación en iPhone/Android | ⛔ bloqueada por credenciales |
| 13 | Piloto con un establecimiento real | ⛔ requiere decisión comercial |

Limitaciones conocidas:

- **Emisión real de Wallet**: los generadores existen y están probados con
  credenciales de prueba; falta configurar Pass Type ID/Issuer ID y validar
  en dispositivos físicos (`docs/WALLET_INTEGRATIONS.md`).
- **Retención física**: la supresión de datos es ejecutable (anonimización),
  pero la poda automática por plazos aún no está programada (`docs/PRIVACY.md`).
- **CSP con `unsafe-inline`** para el arranque en línea de Next; los nonces
  quedan pendientes (`docs/SECURITY.md`).
- **Rate limiting en memoria** (un solo proceso; al escalar habría que
  externalizarlo).
- **Modo puntos**: no implementado; el piloto usa sellos.

---

## 6. Documentación

| Documento | Contenido |
|---|---|
| [`AGENTS.md`](./AGENTS.md) | especificación maestra de producto y reglas |
| [`docs/IMPLEMENTATION_PLAN.md`](./docs/IMPLEMENTATION_PLAN.md) | fases y estado |
| [`docs/API_SPEC.md`](./docs/API_SPEC.md) | contratos de la API |
| [`docs/DATA_MODEL.md`](./docs/DATA_MODEL.md) | entidades y restricciones |
| [`docs/SECURITY.md`](./docs/SECURITY.md) · [`docs/PRIVACY.md`](./docs/PRIVACY.md) | seguridad y privacidad |
| [`docs/WALLET_INTEGRATIONS.md`](./docs/WALLET_INTEGRATIONS.md) · [`docs/NFC_AND_REVIEWS.md`](./docs/NFC_AND_REVIEWS.md) | Wallet, etiquetas y política de reseñas |
| [`docs/ADR/`](./docs/ADR/) | decisiones (emisor Wallet, ciclo de vida, datos del alta, integración con Sales) |

## 7. Estructura

```text
localai-fidelity/
├── AGENTS.md                especificación maestra
├── docker-compose.yml       web + api + postgres (entorno local)
├── apps/web/                Next.js + TypeScript + Tailwind
│   ├── components/          vistas del panel, escáner, tarjeta…
│   └── e2e/                 suite Playwright (npm run e2e)
├── services/api/            FastAPI + SQLAlchemy 2 + Alembic
│   ├── app/                 API, dominio, servicios, adaptadores Wallet
│   ├── migrations/          migraciones versionadas
│   └── tests/               pytest (unitarias, integración y pg)
├── docs/                    documentación y ADRs
└── .env.example             variables (sin secretos)
```
