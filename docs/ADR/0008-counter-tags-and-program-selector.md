# ADR-0008: etiquetas de mostrador y selector de programa

- **Fecha:** 15/10/2026
- **Estado:** aceptado e implementado
- **Contexto:** un comercio puede tener varias promociones activas a la vez
  («5 cafés → 1 gratis» y «3 menús → medio menú gratis»). En el mostrador hay
  que sumar el sello **a la promoción correcta** y con pocos toques cuando hay
  cola. Se pidió estudiar una etiqueta NFC que «sume puntos».

## Decisión

Se implementan **dos piezas complementarias**, nunca un sello automático por
tocar una etiqueta:

1. **Selector de programa en Operaciones.** Tras identificar la tarjeta, la
   pantalla carga **todas las tarjetas del cliente** (una por programa) y las
   ofrece como botones grandes («Club del Café · 4 sellos»). La promoción
   activa manda en el botón «+1 sello» y en las recompensas. Un cliente con
   un solo programa ve la pantalla de siempre.
2. **Etiqueta de mostrador** (`counter`): una etiqueta NFC por promoción,
   pegada junto a caja. Su URL redirige a
   `/merchants/{id}/operations?program={program_id}`. El **personal** la toca
   con **su** móvil y las operaciones se abren con ese programa
   preseleccionado: *tocar → escanear → sumar*. Si el cliente no está en ese
   programa, la pantalla lo explica y ofrece el selector igualmente.

### Reglas que no se rompen

- Una etiqueta **jamás** suma sellos por sí sola: su URL es pública y estática
  (cualquiera podría sellarse desde casa). El sello lo autoriza siempre un
  usuario autenticado del comercio con su sesión.
- La etiqueta **propone** el programa; el personal confirma. La pantalla
  permite corregir sin volver a tocar nada.
- Con la etiqueta de reseñas no cambia nada: sigue siendo otro flujo,
  neutral y sin incentivos.

## Alternativas descartadas

- **Etiqueta que suma al tocarla el cliente**: fraude trivial (URL compartible,
  sello repetible) y sin forma de saber quién ha tocado.
- **Autodetección por compra (TPV)**: requiere integración con caja; fuera del
  alcance actual y dependiente del TPV de cada comercio.
- **Tarjeta unificada por cliente** (un único QR con todos los programas): es
  la evolución natural si el uso real lo pide, pero implica cambio de modelo
  (token a nivel de cliente). El selector actual ya resuelve el caso con las
  tarjetas existentes.

## Consecuencias

- El id interno del comercio aparece en la URL de las etiquetas de mostrador.
  No es un secreto (no concede acceso: Operaciones exige sesión y el
  aislamiento multiempresa sigue vigente), pero es una exposición a tener en
  cuenta si en el futuro se acortan las rutas por *slug*.
- Nuevo tipo de tag `counter` con su propia métrica (`counter_clicks`): mide
  la adopción del atajo por el personal, separada de altas y reseñas.
- **Corrección incluida**: los clics de las etiquetas de alta ahora se
  registran de verdad (`loyalty_signup_clicks` quedaba siempre a 0).
- El mostrador gana además `GET /members/{id}/cards` (tarjetas del cliente) y
  el nombre del programa en todas las respuestas de tarjeta.
