# NFC, QR y reseñas de Google — guía operativa

## 1. Dos etiquetas, dos destinos (§5.1)

| Tipo | `tag_type` | Abre | Requisito |
|---|---|---|---|
| Alta de fidelización | `loyalty_signup` | `/p/{comercio}/{programa}` | Programa activo |
| Recuperación de tarjetas | `member_card_access` | `/my-card/{comercio}` | El cliente solicita un enlace por correo |
| Reseñas de Google | `google_review` | Enlace oficial verificado | Destino guardado **y** verificado |

Nunca se mezclan: cada etiqueta tiene su URL corta (`/go/{slug}`), su QR y su
métrica. El panel las distingue por etiqueta y color. La etiqueta de
recuperación es compartida y no contiene un token del cliente: el cliente
introduce su correo en una página neutral y recibe un enlace personal
temporal, de un solo uso y limitado a sus tarjetas de ese comercio.

## 2. Cómo instalar una etiqueta (para el comercio)

1. En **NFC y QR** crea la etiqueta que necesitas (alta, recuperación o
   reseñas).
2. **Descarga el QR** (SVG) e imprímelo en tu cartel o mostrador.
3. Para etiqueta NFC: escribe la URL corta (`https://TU-DOMINIO/go/{slug}`)
   en la etiqueta con cualquier app que soporte **NDEF URI** (NFC Tools,
   etc.). El software no programa la etiqueta física (§14.3).
4. **Pruébala** con un iPhone y un Android antes de dejarla fija: acerca el
   móvil y comprueba que abre la página esperada.
5. Si pierdes o te roban la etiqueta: **Desactivar** en el panel. La URL
   responde una página «etiqueta desactivada» (410) en lugar de redirigir.

## 3. Reglas del módulo de reseñas (§4.2) — verificadas por tests

- Solo se redirige a un destino **guardado y verificado**; cambiar el enlace
  obliga a verificar de nuevo.
- `/go/{slug}` ignora parámetros: no hay filtro por satisfacción ni historial.
- El esquema de etiquetas **rechaza** campos de incentivo (`extra="forbid"`).
- La métrica se llama `review_link_clicks` (clics, **no** reseñas).
- No se publican reseñas ni se consulta la API de reseñas de Google.

Texto neutral sugerido para el cartel: **«¿Quieres compartir tu experiencia?
Puedes dejar una reseña aquí»**.

## 4. Qué mide la plataforma

- `loyalty_signup_clicks`: visitas a la página de alta.
- `member_card_access_clicks`: visitas a la página de recuperación (no
  equivalen a accesos a tarjetas).
- `review_link_clicks`: visitas al enlace de reseñas.
- `tags_active`: etiquetas activas.

Ninguna de esas cifras equivale a altas ni a reseñas publicadas: son clics al
enlace (§4.4).

## 5. Compatibilidad

- Los QR se generan con `segno` (error `m`, escala 8): legibles en impresión
  normal y en pantalla.
- NFC: la plataforma no garantiza que toda etiqueta/teléfono/carcasa reaccione
  igual; por eso el panel recomienda probar cada etiqueta antes de instalarla.
