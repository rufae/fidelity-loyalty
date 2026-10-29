# Privacidad — LocalAI Fidelity

> Aplicación a España/UE. Este documento describe el tratamiento **técnico**;
> no sustituye una revisión jurídica antes de operar con clientes reales.

## 1. Qué datos se tratan

| Categoría | Datos | Origen | Finalidad |
|---|---|---|---|
| Clientes de los comercios (miembros) | email (opcional), nombre (opcional), versiones de condiciones aceptadas | Alta pública del cliente | Gestionar la tarjeta de fidelización |
| Membresías | token opaco, saldo de sellos, historial de movimientos | Operaciones del comercio | Funcionamiento del programa |
| Usuarios del comercio | email, nombre, hash de contraseña | Alta por el propietario | Acceso al panel |
| Métricas de enlaces | hora, tipo de etiqueta, ID interno del tag | Clics en `/go/{slug}` | Estadística de uso de los materiales |

**No se recogen**: IP completa, user-agent, huella del dispositivo, fecha de
nacimiento, dirección, ni datos sensibles. No hay identidad global entre
comercios: un cliente es un registro distinto en cada comercio (§11.7).

## 2. Consentimiento y transparencia (§9.4)

- El alta muestra las **condiciones vigentes con su versión** y exige
  aceptarlas (`accepted_terms_version`): si cambian, el alta se rechaza hasta
  que el cliente las revise de nuevo.
- El consentimiento de comunicaciones es **opcional, separado y no
  predeterminado** (`marketing_consent=false` por defecto). El MVP no envía
  ninguna comunicación.
- Se registra la versión aceptada en la membresía como prueba.

## 3. Datos en URLs y códigos (§9.3)

- Los tokens de tarjeta son opacos (256 bits aleatorios): no codifican email,
  nombre ni IDs internos (testeado).
- Los QR y las etiquetas NFC solo contienen rutas públicas o tokens opacos.
- Ninguna URL privada es adivinable.

## 4. Conservación y borrado

| Datos | Política actual |
|---|---|
| Miembros y membresías | Borrado lógico (estado); el físico queda pendiente de la política de retención (FASE 12 pendiente) |
| Ledger de movimientos | Se conserva: es el registro contable del programa y su corrección es una reversión, nunca un borrado |
| `redirect_events` | Solo hora + tag; sin PII. Candidato a poda por antigüedad |
| Sesiones | Expiran (`AUTH_SESSION_TTL_SECONDS`) y se revocan al logout |
| Auditoría | Conservada; sus metadatos pasan por *allowlist* |

## 5. Encargados y proveedores

- **Sin proveedores externos por defecto**: todo corre en el servidor propio
  (PostgreSQL, API, web). No hay trackers ni CDN.
- Apple Wallet / Google Wallet (FASE 7/8, hoy `not_configured`): al
  activarlos, el pase contiene el nombre comercial, el programa y el
  identificador opaco; **nunca** email ni teléfono. Revisar entonces las
  condiciones del proveedor y minimizar lo que se envía.

## 6. Derechos de las personas interesadas

Un cliente puede ejercer sus derechos (acceso, rectificación, supresión,
oposición) ante el comercio, que es quien determina finalidades y medios en
su relación con sus clientes. La plataforma debe permitir localizar y suprimir
el registro de un cliente; hoy existe el servicio
`app/services/members.py` sobre el que se implementará el flujo de ejercicio
de derechos (pendiente explícita).

## 7. Reseñas de Google (§4)

La plataforma **no** trata datos de reseñas ni intenta saber quién publicó
qué: solo facilita el acceso al enlace oficial y cuenta clics. Ese tratamiento
es anónimo por diseño.

## 8. Soporte B2B

- **Quién**: solo usuarios autenticados de los comercios que contratan la
  plataforma; los clientes finales no usan este canal.
- **Datos del mensaje**: el contenido puede contener datos personales que el
  comercio decida incluir. Se usa para atender la solicitud y se conserva
  mientras la conversación esté abierta y durante el plazo de retención.
- **Teléfono de llamada**: opcional y con consentimiento separado. Se guarda
  cifrado (`SUPPORT_PHONE_ENCRYPTION_KEY`), solo lo descifra la administración
  de plataforma y **no** se incluye en emails, push, logs ni listados.
- **Avisos**: email/ntfy/Telegram pueden contener comercio, asunto, un extracto
  corto del mensaje y un enlace. Nunca el teléfono ni el mensaje completo si
  no es necesario.
- **Retención**: conversaciones cerradas 12 meses; solicitudes de llamada 30
  días después de atenderse o cancelarse; registros de aviso 30 días. Estos
  plazos son la política inicial y se revisarán antes de producción.
- **Derechos**: el comercio puede solicitar acceso, rectificación o supresión
  de sus conversaciones; el ledger de movimientos del programa no se toca.
