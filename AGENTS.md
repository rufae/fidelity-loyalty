# AGENTS.md — LocalAI Fidelity

> Documento maestro de producto, arquitectura, requisitos funcionales, seguridad, cumplimiento, experiencia de usuario y plan de implementación.

> Este archivo es la fuente principal de verdad para los agentes de programación que trabajen en este repositorio. Describe el producto objetivo y las restricciones que debe respetar. No significa que todo esté ya implementado: el estado real debe mantenerse actualizado en docs/IMPLEMENTATION_PLAN.md.

> Regla principal: inspeccionar el repositorio, planificar una fase cada vez, implementar una unidad verificable y ejecutar las pruebas. No construir toda la plataforma de una sola vez ni afirmar que algo funciona sin comprobarlo.

# 1. IDENTIDAD Y VISIÓN DEL PRODUCTO

## 1.1 Nombre

Nombre de trabajo: LocalAI Fidelity. El nombre puede cambiarse más adelante sin alterar el dominio ni la lógica de negocio.

## 1.2 Qué es

LocalAI Fidelity es una plataforma SaaS multiempresa para que pequeños y medianos negocios creen y gestionen programas de fidelización digital. Los clientes de esos negocios podrán registrarse desde una página móvil, guardar su tarjeta en Apple Wallet o Google Wallet y utilizar un identificador QR/código de barras para acumular puntos, sellos o canjear recompensas.

La plataforma también ofrecerá un segundo producto físico-digital: etiquetas NFC y códigos QR independientes que llevan al perfil oficial de reseñas de Google del negocio, facilitando que cualquier cliente que lo desee escriba una reseña basada en una experiencia auténtica.

El sistema debe separar claramente dos recorridos:

- Fidelización: captar al cliente en el programa, emitir la tarjeta digital y gestionar operaciones/recompensas.
- Reseñas: facilitar el acceso del cliente a la página oficial para publicar una reseña voluntaria y honesta.

Ambos recorridos pueden presentarse en materiales físicos o en el panel de negocio, pero nunca deben mezclarse de forma que se condicione un premio, descuento o beneficio a la publicación de una reseña.

## 1.3 Problema que resuelve

Muchos negocios locales quieren fomentar visitas recurrentes sin desarrollar una aplicación móvil propia, imprimir tarjetas de papel ni comprar sistemas complejos. La plataforma debe proporcionar una alternativa sencilla y administrable desde un navegador.

También debe simplificar la forma en que un negocio solicita opiniones auténticas: un cliente acerca el móvil a una etiqueta NFC o escanea un QR y llega a la página de reseñas del negocio en Google.

## 1.4 Visión

Un propietario de negocio debe poder:

- Crear una cuenta y configurar su comercio.
- Crear un programa de fidelización sin programación.
- Personalizar el nombre, logotipo, colores y condiciones visibles de la tarjeta.
- Crear una página de alta optimizada para móvil.
- Colocar un QR o una etiqueta NFC en el mostrador.
- Permitir que sus clientes añadan la tarjeta a Apple Wallet o Google Wallet.
- Identificar al cliente con un código QR/barra opaco y seguro.
- Registrar visitas, puntos y sellos mediante un panel web para el personal.
- Definir y canjear recompensas.
- Consultar movimientos y estadísticas.
- Configurar enlaces/etiquetas de reseñas de Google para que los clientes puedan opinar libremente.
- Descargar o imprimir instrucciones y materiales para el establecimiento.
- Administrar a sus empleados y permisos, cuando el plan lo permita.

Los clientes finales deben poder utilizar la experiencia principal sin instalar una aplicación propia de LocalAI Fidelity. Apple Wallet y Google Wallet son destinos compatibles, no sustitutos de la lógica de negocio del backend.

## 1.5 Principios rectores

- Multiempresa desde el diseño: una empresa jamás debe acceder a los datos de otra.
- Web-first: el alta, la gestión y el uso del personal funcionan desde un navegador moderno.
- Wallet-native, no Wallet-dependent: Wallet mejora la experiencia, pero el backend es la fuente de verdad de puntos y recompensas.
- Datos mínimos: no recoger información personal que no sea necesaria para operar el programa.
- Operaciones auditables: cada alta, movimiento, ajuste y canje debe quedar trazado.
- No inventar estados: el backend confirma los cambios; el frontend no simula éxitos.
- Seguridad por defecto: autorización comprobada en el backend, secretos fuera de Git y límites en endpoints expuestos.
- Cumplimiento de políticas: no manipular reseñas, no condicionar recompensas a reseñas y respetar las condiciones de Apple/Google.
- Costes transparentes: la solución debe poder autoalojarse, pero no debe prometer coste cero donde haya costes externos reales.
- Iteración incremental: primero un flujo completo de fidelización, después mejoras y automatizaciones.
- Portabilidad: el dominio debe poder utilizar otros proveedores de infraestructura en el futuro.
- Operabilidad: copias, restauración, migraciones y observabilidad forman parte del producto, no son tareas opcionales indefinidas.

# 2. RELACIÓN CON LOCALAI SALES

Existe otro proyecto llamado LocalAI Sales, orientado a descubrir negocios, investigar oportunidades y gestionar el CRM de prospección. Este repositorio tiene un objetivo distinto.

- LocalAI Sales: herramienta interna para encontrar, cualificar y captar comercios.
- LocalAI Fidelity: producto que se ofrece a los comercios para gestionar sus programas de fidelización y sus enlaces de reseñas.

No copiar el backend ni compartir directamente la base de datos de LocalAI Sales. Cada sistema conserva su propio repositorio, despliegue, configuración y esquema de datos.

La integración entre ambos será opcional y posterior. Podría consistir en una API autenticada o importación/exportación explícita para registrar el estado de un comercio cliente. No debe bloquear el MVP de fidelización.

No importar credenciales, datos de clientes ni tablas de un proyecto al otro sin una decisión explícita y documentada.

# 3. ALCANCE DEL PRODUCTO

## 3.1 MVP obligatorio

El primer MVP debe completar este flujo real:

- Un administrador de la plataforma crea o habilita un comercio.
- Un usuario autorizado del comercio entra en su panel.
- Configura un programa simple de fidelización basado en sellos o puntos.
- Publica una página móvil de alta para clientes.
- Un cliente abre la página mediante URL, QR o etiqueta NFC.
- El cliente introduce los datos mínimos y acepta la información de privacidad aplicable.
- El sistema crea su membresía y emite un identificador seguro.
- El cliente puede descargar/añadir una tarjeta a Apple Wallet o Google Wallet cuando la configuración del emisor lo permita.
- El personal autorizado identifica la tarjeta desde su dispositivo y registra una visita o transacción.
- El backend actualiza el libro de movimientos y calcula el saldo.
- La tarjeta se actualiza cuando la integración Wallet lo permita; el saldo real sigue consultándose en el backend.
- El negocio puede canjear una recompensa con validación en servidor.
- El panel muestra el historial y estadísticas básicas.
- El comercio configura un enlace verificado de Google Reviews y genera una URL/QR/NFC de reseñas independiente.
- El cliente que toca esa etiqueta puede abrir el destino público de reseñas sin pasar por un filtro de satisfacción.

## 3.2 Fuera del MVP inicial

No implementar inicialmente, salvo que una fase posterior lo apruebe expresamente:

- Aplicación móvil nativa propia para consumidores.
- Integraciones profundas con todos los TPV del mercado.
- Terminales NFC de pago.
- Pagos, monederos monetarios o custodia de dinero.
- Cashback monetario con implicaciones financieras.
- Suscripciones avanzadas de consumidores.
- Sistema complejo de niveles VIP.
- Campañas de marketing automatizadas multicanal.
- Envío masivo de SMS, email o WhatsApp.
- Segmentación basada en datos sensibles.
- Programa de afiliados.
- Marketplace público de comercios.
- Agentes autónomos con permisos de modificar saldos sin autorización.
- Analítica predictiva avanzada.
- Integración automática con Google Business Profile para responder reseñas, salvo evaluación posterior de permisos y alcance.
- Sistema de solicitud de reseñas que filtre a los clientes por satisfacción.

## 3.3 Reglas para evitar el exceso de alcance

Antes de implementar una funcionalidad, el agente debe responder:

- ¿Es necesaria para el flujo MVP?
- ¿Está definida en este documento?
- ¿Qué criterios de aceptación verificables tiene?
- ¿Afecta a privacidad, seguridad, costes o políticas de terceros?
- ¿Existe una solución mucho más sencilla?

No implementar por adelantado funcionalidades de fases futuras solo porque la arquitectura las mencione.

# 4. REGLAS CRÍTICAS SOBRE GOOGLE REVIEWS

Este apartado es obligatorio. Cualquier implementación de NFC/QR de reseñas debe respetarlo.

## 4.1 Flujo permitido

El negocio proporciona o verifica su enlace oficial para escribir una reseña de Google. La plataforma genera un enlace corto propio opcional, un QR imprimible y las instrucciones para programar una etiqueta NFC. Al tocar o escanear la etiqueta, el usuario llega al destino oficial para escribir una reseña voluntaria.

La plataforma no escribe reseñas por el usuario, no simula clics ni valoraciones y no intenta automatizar publicaciones. El usuario decide si publica una reseña y qué contenido escribe.

La URL guardada debe ser verificada y asociada al comercio correcto. Nunca construir un enlace de destino con un identificador inventado ni afirmar que es oficial sin validarlo.

## 4.2 Prohibiciones

Está prohibido implementar funcionalidades que:

- Ofrezcan puntos, sellos, regalos, descuentos, sorteos o cualquier incentivo a cambio de escribir, cambiar o eliminar una reseña de Google.
- Den más recompensa a quien deje cinco estrellas o una reseña positiva.
- Soliciten una reseña solo a clientes que respondan que están satisfechos.
- Envíen a clientes insatisfechos a un formulario privado mientras muestran Google Reviews solo a clientes satisfechos.
- Oculten o dificulten el acceso a Google Reviews a determinados clientes.
- Sugieran una puntuación mínima o contenido predeterminado para la reseña.
- Generen reseñas falsas o publiquen automáticamente en nombre de clientes.
- Midan el éxito mediante valoración positiva de la reseña o impulsen al personal a conseguir una cantidad específica de valoraciones positivas.
- Vinculen una operación de fidelización al hecho de publicar una reseña.

Sí se puede facilitar que todos los clientes encuentren el enlace de reseñas mediante NFC/QR, siempre que la solicitud sea neutral, voluntaria y no incentivada.

La recompensa de fidelización debe depender de compras, visitas u otras reglas legítimas del programa, no de publicar reseñas.

## 4.3 Experiencia recomendada para reseñas

La página de configuración del comercio mostrará:

- Campo para introducir el enlace oficial a Google Reviews.
- Instrucciones para localizar/validar el enlace del negocio.
- Botón para abrir el destino y comprobarlo manualmente.
- Fecha de última verificación.
- Opción para generar un QR.
- Opción para generar una URL corta bajo el dominio de la plataforma.
- Instrucciones para escribir esa URL en una etiqueta NFC.
- Material imprimible con texto neutral, por ejemplo: “¿Quieres compartir tu experiencia? Puedes dejar una reseña aquí”.

No incluir por defecto mensajes como “Déjanos cinco estrellas”, “Solo si estás satisfecho” o “Consigue un descuento por reseñar”.

## 4.4 Redireccionamiento y métricas

Se puede ofrecer una URL de redireccionamiento propia para actualizar el destino sin reescribir todas las etiquetas, pero debe cumplir estas reglas:

- No filtrar ni desviar usuarios según su experiencia, valoración, historial de compras o respuestas.
- No exigir iniciar sesión antes de abrir el destino de reseñas.
- Mostrar el destino de forma clara cuando proceda.
- Recopilar solo métricas mínimas de clics/escaneos.
- No prometer que cada escaneo equivale a una reseña publicada.
- No intentar averiguar qué reseña publicó una persona a partir de un clic.
- No exponer identificadores de clientes en la URL.
- Definir límites antiabuso sin bloquear a clientes legítimos.

La métrica representa visitas al enlace, no reseñas, valoraciones ni satisfacción. Los registros de clics deberán tener una política de retención y minimización.

## 4.5 Políticas oficiales a consultar

Antes de cambiar cualquier flujo de reseñas, comprobar las políticas vigentes de Google:

- https://support.google.com/contributionpolicy/answer/7400114?hl=es
- https://support.google.com/business/answer/3474122?hl=es
- https://developers.google.com/my-business/content/review-data

Si una página cambia, consultar su versión vigente. La implementación debe cumplir la política de Google más restrictiva que resulte aplicable.

# 5. EXPERIENCIA NFC Y QR

## 5.1 Tipos de etiqueta/producto

El sistema debe admitir al menos dos tipos distintos de destino físico:

### A. Alta de tarjeta de fidelización

Etiqueta o QR que abre la página pública de alta de un programa concreto. Tras registrarse, el cliente puede añadir su tarjeta a Wallet.

### B. Reseñas de Google

Etiqueta o QR independiente que abre directamente o redirige de forma transparente al enlace oficial de reseñas del comercio.

No se deben confundir los dos tipos en el panel ni en los materiales impresos. La pantalla de configuración debe mostrar con claridad la finalidad de cada etiqueta.

## 5.2 URLs y tokens

- Preferir rutas cortas y legibles con un identificador aleatorio no predecible cuando se use redireccionamiento propio.
- Nunca codificar en una etiqueta NFC nombre, email, teléfono, saldo, identificador interno secuencial ni otros datos personales.
- No utilizar un token de una etiqueta NFC como credencial para canjear recompensas.
- Los identificadores de alta pueden ser públicos, pero no deben permitir acceder a la información privada de clientes.
- Las URLs de redirección solo pueden resolver destinos permitidos y validados.
- Evitar redirecciones abiertas a dominios arbitrarios. El destino para reseñas debe quedar asociado y aprobado para ese comercio.
- Mostrar una vista previa del destino antes de programar/descargar material.

## 5.3 Compatibilidad de NFC

La plataforma debe crear instrucciones de uso y configuración para etiquetas NFC compatibles con enlaces NDEF URI. No debe afirmar que todas las etiquetas, teléfonos, carcasas o sistemas operativos reaccionan igual.

No se necesita un lector NFC para la versión inicial: un teléfono puede abrir el enlace de una etiqueta programada. La validación de compras utiliza el QR/código de la tarjeta en la interfaz del personal, salvo que una integración futura justifique un lector específico.

El sistema no escribe directamente en la etiqueta física desde el navegador en todos los dispositivos. En el MVP, proporciona la URL y las instrucciones para programarla con una herramienta compatible, y puede recomendar comprobaciones de lectura antes de instalar la etiqueta.

## 5.4 Calidad de instalación

Para cada etiqueta, facilitar:

- Identificador interno y finalidad.
- URL de destino actual.
- QR descargable en SVG/PNG de calidad adecuada.
- Etiqueta de texto para impresión.
- Instrucciones de programación NFC.
- Instrucciones para probar con iOS y Android.
- Estado activo/inactivo.
- Fecha de creación/última modificación.
- Prueba de destino sin exponer datos privados.

# 6. TARJETAS DIGITALES Y WALLET

## 6.1 Reglas generales

La base de datos del backend es la fuente de verdad. Apple Wallet y Google Wallet son representaciones digitales del programa y pueden no actualizarse de forma instantánea o estar temporalmente sin conexión.

Nunca confiar en el código QR mostrado en una tarjeta como prueba suficiente de que un saldo tiene valor actual. El backend debe verificar el estado y el saldo durante cada operación.

La interfaz debe mostrar opciones solo para plataformas compatibles cuando se detecte razonablemente el dispositivo, y mantener siempre una alternativa accesible.

## 6.2 Datos visibles en la tarjeta

Incluir únicamente lo que aporte valor y sea adecuado para visualizarse en una pantalla bloqueada o en un teléfono compartido:

- Nombre comercial.
- Nombre del programa.
- Logotipo y colores.
- Identificador de fidelización público u opaco.
- Puntos o sellos, si la integración permite actualizarlo.
- Resumen de la recompensa o regla, si procede.
- Código QR/barra opaco para identificar la membresía.
- Enlace de ayuda o web del comercio cuando sea apropiado.

No mostrar por defecto email, teléfono, dirección particular, historial de compras ni otros datos personales.

## 6.3 Identificador de tarjeta

Cada tarjeta tendrá:

- Identificador interno del sistema.
- Serial de pass para la plataforma Wallet cuando sea necesario.
- Token opaco para identificación/validación, separado de cualquier token administrativo.
- Estado de la tarjeta y de la membresía.

Los tokens deben generarse con aleatoriedad criptográfica suficiente. No usar IDs secuenciales como tokens públicos. Si un token permite una operación sensible, validar permisos, estado, expiración y contexto en backend.

## 6.4 Apple Wallet

Implementar la integración detrás de un adaptador específico. Consultar la documentación oficial vigente antes de codificar detalles de formato, firma, distribución o actualización:

- https://developer.apple.com/documentation/walletpasses
- https://developer.apple.com/documentation/walletpasses/adding-a-web-service-to-update-passes
- https://developer.apple.com/documentation/walletpasses/distributing-and-updating-a-pass

Requisitos:

- Generar el pase con los campos obligatorios y recursos gráficos válidos.
- Firmar el archivo .pkpass mediante los certificados de Pass Type ID requeridos.
- Guardar certificados y claves privadas en un sistema de secretos/volumen restringido, nunca en Git ni en frontend.
- No generar un pase de producción sin verificar certificado, Pass Type Identifier, Team Identifier y firmas.
- Mantener una relación entre el pase, la membresía y el identificador del programa.
- Implementar el servicio web de actualización si el producto lo necesita: registro, baja, consulta de pases actualizados y descarga de pases actualizados, con autenticación conforme a la documentación de Apple.
- Gestionar notificaciones push para pases actualizables cuando el entorno esté configurado.
- No afirmar que una actualización es instantánea o garantizada en cualquier dispositivo.
- No exponer tokens de autenticación del pase ni usar el token de actualización como identificador visible.
- Probar emisión, instalación, actualización y revocación con certificados y dispositivos de prueba.

La disponibilidad de pases actualizables requiere endpoints accesibles desde los servicios y dispositivos correspondientes por HTTPS. Un servidor exclusivamente accesible mediante Tailscale no sirve para una experiencia pública completa de clientes externos.

## 6.5 Google Wallet

Implementar la integración detrás de un adaptador propio, consultando siempre la documentación oficial vigente:

- https://developers.google.com/wallet/retail/loyalty-cards
- https://developers.google.com/wallet/retail/loyalty-cards/overview/how-classes-objects-work
- https://developers.google.com/wallet/retail/loyalty-cards/overview/add-to-google-wallet-flow

Requisitos:

- Separar la configuración del emisor, clase de fidelización y objeto por miembro conforme a los conceptos de Google Wallet.
- Crear el flujo de “Añadir a Google Wallet” mediante el mecanismo oficial y credenciales de servidor.
- Mantener la clave de cuenta de servicio exclusivamente en backend o gestor de secretos.
- No construir manualmente JWT inseguros ni permitir al navegador firmar pases.
- Gestionar estados de desarrollo/test y producción.
- Actualizar el objeto de Wallet cuando cambien los datos visibles de la membresía y la API lo permita.
- Tratar errores de emisión/actualización como estados recuperables y observables.
- Evitar duplicados de objetos y usar identificadores válidos según las reglas del proveedor.
- Comprobar las condiciones del emisor, aprobaciones, uso de marcas y requisitos de publicación vigentes.
- No asumir que Google Wallet enviará notificaciones arbitrarias iguales a las capacidades de Apple Wallet.

## 6.6 Proveedor abstracto

El dominio no debe depender de una sola plataforma.

Definir una interfaz conceptual como:

```python
class WalletProvider:
    async def issue_pass(self, membership_id: str): ...
    async def update_pass(self, membership_id: str): ...
    async def revoke_pass(self, membership_id: str): ...
    async def get_add_to_wallet_action(self, membership_id: str): ...
```

La implementación real puede diferir, pero la interfaz de dominio debe impedir que la lógica de puntos dependa del SDK de Apple o Google.

Cada proveedor debe registrar su estado: not_configured, test, active, error o disabled.

## 6.7 Fallback si no hay Wallet

El cliente debe tener una alternativa razonable:

- Mostrar su tarjeta en una página segura para móvil.
- Mostrar el código QR/barra de identificación.
- Consultar instrucciones de alta.

El fallback web no debe exponer datos del cliente por una URL predecible. La sesión o token usado debe ser revocable y limitado.

# 7. MODELO DE FIDELIZACIÓN

## 7.1 Tipos de programa

Diseñar para admitir varios tipos, pero implementar progresivamente:

- stamps: sellos por visitas/compras elegibles.
- points: puntos según reglas configurables.
- rewards: catálogo de recompensas canjeables asociado a uno de los anteriores.

Los niveles, membresías de pago, cashback y reglas avanzadas se dejan para fases futuras.

## 7.2 Reglas configurables

Un programa puede definir:

- Nombre.
- Descripción y condiciones.
- Tipo (stamps o points).
- Reglas de acumulación.
- Cantidad de sellos/puntos por operación o por importe, si se implementa con seguridad.
- Umbral de canje.
- Recompensas disponibles.
- Vigencia y caducidad, si existe una política explícita.
- Límites de operaciones.
- Fecha de inicio y finalización.
- Estado (draft, active, paused, archived).
- Identidad visual.
- URL pública de alta.
- Configuración de Wallet.

No añadir campos con efectos económicos sin definir reglas de redondeo, reembolso, reversión, caducidad y auditoría.

## 7.3 Fuente de verdad: libro inmutable de movimientos

El saldo no debe ser un número editable libremente por la interfaz.

Crear un libro de movimientos (ledger) para cada operación. Ejemplos:

- earn: puntos/sellos acumulados.
- redeem: puntos/sellos consumidos al canjear.
- adjustment: ajuste manual con motivo y usuario autorizado.
- reversal: reversión de una operación anterior.
- expiry: expiración conforme a una regla publicada.

Cada movimiento debe registrar:

- ID.
- comercio/programa/membresía.
- tipo.
- cantidad firmada o representación equivalente definida en dominio.
- origen o referencia de operación.
- usuario/staff que la ejecutó, cuando aplique.
- fecha UTC.
- clave idempotente.
- motivo/nota cuando proceda.
- referencia al movimiento revertido si existe.

No editar ni borrar movimientos históricos para corregir un error: generar una reversión o ajuste auditable. El saldo puede materializarse para rendimiento, pero debe poder reconciliarse a partir del ledger.

## 7.4 Canjes seguros

Un canje debe ser una transacción atómica:

- Autenticar al personal.
- Comprobar que pertenece al comercio.
- Cargar la membresía y saldo actual.
- Verificar que la recompensa existe, está activa y es elegible.
- Verificar saldo suficiente y límites.
- Bloquear o serializar la operación para evitar doble gasto concurrente.
- Crear movimiento de canje con idempotencia.
- Registrar auditoría.
- Solicitar actualización de Wallet de forma asíncrona cuando aplique.
- Devolver resultado confirmado por el backend.

No confiar en la información impresa en la tarjeta sin verificación del servidor.

## 7.5 Sellos

Para programas de sellos:

- Los sellos son unidades enteras.
- Definir si un escaneo equivale a una visita o si el personal debe confirmar una operación.
- Evitar que una misma petición repetida otorgue sellos múltiples.
- No prometer prevención total del fraude solo por usar un QR.
- Registrar usuario y motivo para correcciones manuales.
- Una recompensa no debe canjearse más de una vez.

## 7.6 Puntos

Para programas de puntos:

- Definir la regla exacta de asignación.
- Validar que cantidad, importe y moneda tienen tipos adecuados.
- No aceptar el importe de una venta sin verificarlo en un sistema confiable cuando haya integración externa.
- Evitar cantidades negativas en acumulaciones normales.
- Permitir ajustes solo a roles autorizados.
- Controlar redondeos con Decimal o unidades enteras según el dominio; no usar floats de punto flotante binario para cantidades económicas.

## 7.7 Vencimientos y reembolsos

No habilitar caducidad ni reembolso automáticamente. Definir las reglas y mostrarlas al cliente antes del alta. Los reembolsos de compras deben tener un mecanismo para revertir puntos cuando el negocio lo considere aplicable y la regla haya sido comunicada.

# 8. ROLES Y PERMISOS MULTIEMPRESA

## 8.1 Roles iniciales

- platform_owner: administración global de la plataforma.
- merchant_owner: propietario del comercio.
- merchant_admin: administración del comercio.
- staff: tareas operativas permitidas, como registrar acumulaciones/canjes.
- analyst o viewer: lectura limitada, solo si se necesita.

Los clientes finales (members) no son usuarios de administración por defecto. Su acceso a la tarjeta se gestiona con un flujo independiente y tokens acotados.

## 8.2 Aislamiento de datos

Toda consulta o mutación de datos de comercio debe verificar el merchant_id autorizado en backend. No aceptar como prueba de autorización un merchant_id enviado por el navegador.

Crear pruebas negativas en las que un usuario del comercio A intente consultar, modificar, exportar o canjear datos del comercio B.

Ningún endpoint público de alta debe permitir enumerar membresías ni recuperar su información personal.

## 8.3 Autenticación

Implementar autenticación real antes de un despliegue público:

- Hash de contraseñas mediante algoritmo moderno apropiado (preferencia por Argon2id, si la librería elegida lo permite).
- Sesiones seguras con cookies HttpOnly, Secure en HTTPS y SameSite apropiado.
- Protección CSRF donde el modelo de autenticación lo requiera.
- Rate limiting para login, recuperación y endpoints sensibles.
- Rotación/invalidez de sesión tras login/logout y cambio de credenciales.
- Política para usuarios suspendidos.
- Recuperación de contraseña segura, si se implementa.
- Verificación de email solo cuando el flujo la necesite y tenga un proveedor configurado.

No crear una contraseña universal para todos los comercios ni dejar una cuenta admin/admin.

## 8.4 Auditoría

Registrar los eventos sensibles:

- Alta/cambio de usuarios.
- Cambio de configuración de programa.
- Emisión/revocación de tarjeta.
- Acumulación/canje/ajuste/reversión.
- Exportación de datos.
- Cambio de enlace de reseñas.
- Cambio de configuración Wallet.
- Acciones de administración global.

No guardar contraseñas, tokens, claves privadas ni datos de tarjeta completa en logs.

# 9. PRIVACIDAD Y CUMPLIMIENTO

## 9.1 Contexto

Producto orientado inicialmente a España y la Unión Europea. El diseño debe considerar RGPD, LOPDGDD, normativa de comunicaciones electrónicas y condiciones de proveedores. Este documento no sustituye una revisión jurídica.

Fuentes oficiales para consultar antes del lanzamiento:

- RGPD (Reglamento (UE) 2016/679): https://eur-lex.europa.eu/eli/reg/2016/679/oj
- AEPD: https://www.aepd.es/
- Google Maps User-Contributed Content Policy: https://support.google.com/contributionpolicy/answer/7400114?hl=es
- Apple Wallet Passes: https://developer.apple.com/documentation/walletpasses
- Google Wallet: https://developers.google.com/wallet

## 9.2 Papeles y acuerdos

En función de quién determine finalidades y medios del tratamiento, el negocio y el proveedor de la plataforma pueden desempeñar papeles distintos (responsable, encargado u otros). No codificar una afirmación legal fija en la interfaz. Documentar que hace falta determinar las responsabilidades y firmar los acuerdos pertinentes antes de operar con datos de clientes reales.

## 9.3 Minimización

Solicitar únicamente datos necesarios. Para una tarjeta básica podría bastar una cuenta interna y un identificador opaco; email o teléfono solo deben solicitarse si una función concreta los necesita y se explica la finalidad. No exigir fecha de nacimiento, dirección física u otros datos por defecto.

No poner email, teléfono, nombre completo ni identificador de base de datos en la URL pública o código de la tarjeta.

## 9.4 Transparencia y consentimiento

Antes de activar un checkbox o mensaje de consentimiento, especificar:

- Qué tratamiento se describe.
- Para qué finalidad.
- Si es necesario para el servicio o es opcional.
- Qué información se entrega al cliente.
- Cómo retirar consentimiento cuando proceda.
- Cómo conservar la prueba de la elección, si debe conservarse.

No unir el consentimiento del programa de fidelización con consentimiento de marketing opcional. No marcar casillas de forma predeterminada.

## 9.5 Conservación y eliminación

Definir y documentar periodos de conservación para:

- Datos de membresía.
- Historial de movimientos.
- Eventos de NFC/QR.
- Logs de autenticación.
- Datos de auditoría.
- Registros de error.
- Exportaciones.

Permitir procesos de acceso, exportación, rectificación o supresión cuando correspondan. Si ciertas operaciones deben conservarse por obligaciones contables, contractuales o antifraude, documentar esa necesidad y no eliminar indiscriminadamente el ledger. Aplicar anonimización/pseudonimización cuando sea viable.

## 9.6 Marketing

El MVP no enviará campañas publicitarias automáticamente. Si más adelante se desarrolla email/SMS/WhatsApp marketing, deberá revisarse el canal, la base jurídica, el consentimiento cuando proceda, la prueba de opt-in, la baja, la lista de supresión y las condiciones del proveedor antes de activarlo.

## 9.7 Privacidad por defecto

- Sin trackers de publicidad por defecto.
- Sin compartir listas de clientes entre comercios.
- Sin reutilizar datos de clientes de un comercio para otro.
- Sin entrenar modelos con datos de clientes sin evaluación legal y autorización apropiada.
- Sin enviar datos personales a modelos de IA innecesariamente.
- Métricas agregadas siempre que sea suficiente.

# 10. ARQUITECTURA TÉCNICA PROPUESTA

## 10.1 Principio

Antes de cambiar o crear archivos, inspeccionar el repositorio real. Si ya existen convenciones o tecnología funcional, conservarlas salvo justificación documentada.

## 10.2 Stack de referencia

Stack sugerido para iniciar, coherente con LocalAI Sales:

- Frontend: Next.js + React + TypeScript.
- UI: Tailwind CSS y una librería accesible basada en shadcn/ui o equivalente.
- Backend: Python + FastAPI.
- Validación: Pydantic.
- ORM: SQLAlchemy 2.
- Migraciones: Alembic.
- DB: PostgreSQL.
- Tareas asíncronas: iniciar con tareas en segundo plano simples; incorporar cola solo si la carga real lo exige.
- Contenedores: Docker y Docker Compose.
- Pruebas backend: pytest.
- Pruebas frontend: Vitest y Playwright para recorridos clave.
- Calidad: Ruff, mypy, ESLint y TypeScript estricto.

Se puede elegir otra tecnología si el repositorio ya tiene una base apropiada. No introducir Redis, Kubernetes, microservicios ni una arquitectura multiagente por moda.

## 10.3 Arquitectura lógica

Separar:

- UI de administración de plataforma.
- UI de comercios.
- Páginas públicas de alta/consulta para consumidores.
- API de dominio.
- Persistencia relacional.
- Adaptadores de Wallet.
- Adaptadores de QR/NFC/redirect.
- Servicio de generación de QR/materiales.
- Worker o tareas asíncronas para emisión/actualización Wallet.
- Integraciones externas opcionales.

El backend debe seguir funcionando para lógica de fidelización si Apple Wallet o Google Wallet no están configurados. La integración Wallet es un adaptador, no una dependencia de todas las operaciones.

## 10.4 Estructura orientativa

```text
localai-fidelity/
├── AGENTS.md
├── README.md
├── .env.example
├── docker-compose.yml
├── apps/
│   └── web/
│       ├── app/
│       ├── components/
│       ├── features/
│       │   ├── platform-admin/
│       │   ├── merchants/
│       │   ├── programs/
│       │   ├── members/
│       │   ├── wallet/
│       │   ├── rewards/
│       │   ├── transactions/
│       │   ├── nfc-tags/
│       │   ├── google-reviews/
│       │   ├── analytics/
│       │   └── settings/
│       ├── lib/
│       ├── tests/
│       └── package.json
├── services/
│   └── api/
│       ├── app/
│       │   ├── main.py
│       │   ├── core/
│       │   ├── api/
│       │   ├── domain/
│       │   ├── models/
│       │   ├── schemas/
│       │   ├── repositories/
│       │   ├── services/
│       │   ├── integrations/
│       │   │   ├── apple_wallet/
│       │   │   ├── google_wallet/
│       │   │   ├── qr/
│       │   │   └── email/
│       │   ├── workers/
│       │   └── utils/
│       ├── migrations/
│       ├── tests/
│       ├── pyproject.toml
│       └── Dockerfile
├── docs/
│   ├── PRODUCT_SPEC.md
│   ├── ARCHITECTURE.md
│   ├── DATA_MODEL.md
│   ├── API_SPEC.md
│   ├── SECURITY.md
│   ├── PRIVACY.md
│   ├── WALLET_INTEGRATIONS.md
│   ├── NFC_AND_REVIEWS.md
│   ├── DEPLOYMENT.md
│   ├── TEST_STRATEGY.md
│   ├── IMPLEMENTATION_PLAN.md
│   └── ADR/
├── scripts/
└── tests/
```

No crear todos los ficheros vacíos desde el primer día. Crear documentación y carpetas conforme a su fase.

## 10.5 Límites arquitectónicos

- El navegador nunca accede directamente a PostgreSQL.
- Ninguna clave privada de Wallet llega al frontend.
- La lógica de puntos y canjes pertenece al dominio/backend.
- El saldo no depende de lo que muestre una tarjeta cacheada.
- Las integraciones se encapsulan en adaptadores.
- El frontend no decide permisos.
- Las tareas de emisión y sincronización tienen estados persistidos.
- Las operaciones de valor usan transacciones de base de datos.
- Los cambios del esquema usan migraciones versionadas.
- La API debe poder probarse mediante proveedores simulados.

# 11. MODELO DE DATOS CONCEPTUAL

El modelo definitivo debe ajustarse a cada fase, pero debe preservar las siguientes entidades y relaciones.

## 11.1 platform_users

Usuarios administradores de la plataforma.

Campos conceptuales: id, email, password_hash, display_name, status, created_at, updated_at, last_login_at.

## 11.2 merchants

Negocio/cliente comercial.

Campos: id, name, slug, legal_name opcional, status, timezone, country_code, default_locale, created_at, updated_at.

No usar el slug como único control de acceso.

## 11.3 merchant_locations

Sucursales físicas opcionales.

Campos: id, merchant_id, name, address opcional, timezone, status, created_at.

## 11.4 merchant_users

Usuarios vinculados a un comercio.

Campos: id, merchant_id, email, password_hash o referencia de identidad, role, status, created_at, updated_at, last_login_at.

Evitar duplicar credenciales si se usa un sistema centralizado de identidad; documentar la elección.

## 11.5 loyalty_programs

Programa de fidelización.

Campos: id, merchant_id, name, slug, program_type, description, status, rules_json validado o columnas tipadas según complejidad, terms_version, created_at, updated_at, published_at.

No introducir reglas económicas opacas dentro de JSON sin validación de dominio.

## 11.6 program_rewards

Recompensas.

Campos: id, program_id, name, description, points_cost o stamps_required, status, inventory_limit opcional, valid_from, valid_until, created_at, updated_at.

## 11.7 members

Identidad mínima del cliente dentro de la plataforma.

Campos: id, merchant_id, email opcional, phone opcional, display_name opcional, status, privacy_notice_version, created_at, updated_at, deleted_at/estado de supresión según política.

La pertenencia del cliente a múltiples comercios no debe resolverse compartiendo automáticamente su perfil personal. El diseño inicial puede aislar miembros por comercio; cualquier identidad global futura requiere una decisión de privacidad explícita.

## 11.8 memberships

Relación de un cliente con un programa.

Campos: id, merchant_id, program_id, member_id, membership_number interno no secuencial expuesto, status, joined_at, current_balance_cache opcional, current_stamps_cache opcional, version/control de concurrencia.

Aplicar una restricción única acorde a la regla de una membresía por miembro y programa.

## 11.9 wallet_passes

Estado del pase por proveedor.

Campos: id, merchant_id, membership_id, provider (apple/google), provider_object_id o serial, status, last_issued_at, last_updated_at, last_error_code, provider_metadata solo no sensible.

No guardar secretos, claves privadas ni authentication tokens en metadatos genéricos sin cifrado y necesidad justificada.

## 11.10 loyalty_transactions

Libro de movimientos.

Campos: id, merchant_id, program_id, membership_id, transaction_type, quantity, currency/importe solo si aplica, source, idempotency_key, created_by_user_id opcional, related_transaction_id opcional, reason, created_at.

Añadir restricciones únicas para idempotencia y claves foráneas.

## 11.11 reward_redemptions

Canjes confirmados.

Campos: id, merchant_id, membership_id, reward_id, transaction_id, status, redeemed_by_user_id, idempotency_key, redeemed_at, notes opcional.

No registrar datos excesivos del cliente en las notas.

## 11.12 nfc_tags

Registro lógico de etiquetas.

Campos: id, merchant_id, location_id opcional, tag_type (loyalty_signup, google_review, other_approved), public_slug, destination_url o referencia controlada, status, label, created_at, updated_at, last_tested_at.

Para etiquetas de reseña, el destino debe ser una URL validada asociada al comercio. public_slug no concede permisos de administración.

## 11.13 review_destinations

Configuración de reseñas por comercio o ubicación.

Campos: id, merchant_id, location_id opcional, provider (google), review_url, verification_status, verified_at, created_at, updated_at.

No afirmar que una reseña se publicó. Esta entidad solo representa el destino configurado.

## 11.14 redirect_events

Métricas mínimas de uso de enlaces.

Campos: id, merchant_id, tag_id, event_type, occurred_at, coarse_user_agent_category opcional y estrictamente necesario, referrer_category opcional.

Por defecto no almacenar IP completa ni fingerprints. Si se necesita protección contra abuso, usar el mínimo dato temporal necesario y documentar retención.

## 11.15 merchant_branding

Configuración visual.

Campos: id, merchant_id, logo_asset_id, primary_color, secondary_color, font/visual settings limitados, updated_at.

Validar colores y tipos de archivo. No permitir HTML/JS arbitrario.

## 11.16 assets

Metadatos de logos y recursos subidos.

Campos: id, merchant_id, asset_type, storage_key, mime_type, file_size, created_at.

Validar MIME real, tamaño, dimensiones y contenido. No confiar en extensión.

## 11.17 audit_events

Eventos de seguridad/administración.

Campos: id, merchant_id nullable para eventos globales, actor_type, actor_id, action, entity_type, entity_id, created_at, metadata allowlisted.

## 11.18 background_jobs

Estado de tareas asíncronas si no se usa una cola externa.

Campos: id, job_type, entity_type, entity_id, status, attempts, created_at, started_at, completed_at, error_code, idempotency_key.

## 11.19 Principios de esquema

- Usar UTC en almacenamiento; convertir a zona horaria del comercio para la interfaz.
- Añadir restricciones e índices a partir de consultas reales.
- No usar floats para dinero.
- No borrar físicamente movimientos de puntos para corregir errores.
- Separar estado del proveedor Wallet del estado del programa.
- Mantener estados de error recuperables.
- Versionar cambios mediante Alembic.
- No persistir información de terceros sin confirmar que está permitido.

# 12. API DEL BACKEND

## 12.1 Convenciones

- Prefijo: /api/v1.
- JSON con esquemas explícitos.
- Errores normalizados y mensajes no sensibles.
- Autenticación/autorización en backend.
- Paginación en colecciones.
- Idempotencia para acumulaciones, canjes y operaciones repetibles.
- Rate limits diferenciados según riesgo.
- Correlation ID/Request ID.
- OpenAPI solo accesible públicamente si se considera seguro; deshabilitar o restringir detalles en producción cuando corresponda.
- No exponer stack traces.

## 12.2 Endpoints conceptuales de plataforma

```text
POST   /api/v1/platform/merchants
GET    /api/v1/platform/merchants
GET    /api/v1/platform/merchants/{merchant_id}
PATCH  /api/v1/platform/merchants/{merchant_id}
POST   /api/v1/platform/merchants/{merchant_id}/suspend
```

## 12.3 Autenticación y equipo del comercio

```text
POST   /api/v1/auth/login
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
POST   /api/v1/merchant/users
GET    /api/v1/merchant/users
PATCH  /api/v1/merchant/users/{user_id}
```

Los endpoints definitivos deben seguir el mecanismo de sesión elegido. No devolver passwords ni hashes.

## 12.4 Programas

```text
GET    /api/v1/merchant/programs
POST   /api/v1/merchant/programs
GET    /api/v1/merchant/programs/{program_id}
PATCH  /api/v1/merchant/programs/{program_id}
POST   /api/v1/merchant/programs/{program_id}/publish
POST   /api/v1/merchant/programs/{program_id}/pause
GET    /api/v1/merchant/programs/{program_id}/stats
```

## 12.5 Alta pública de clientes

```text
GET  /p/{merchant_slug}/{program_slug}
POST /api/v1/public/programs/{program_public_id}/enroll
GET  /api/v1/public/memberships/{opaque_token}
```

Las rutas son ejemplos. Los tokens no deben permitir consultar datos privados sin límites. Proteger altas contra abuso y spam sin imponer CAPTCHA por defecto si no es necesario; aplicar controles graduales.

## 12.6 Wallet

```text
POST /api/v1/merchant/memberships/{membership_id}/wallet/issue
GET  /api/v1/public/memberships/{opaque_token}/wallet-options
POST /api/v1/merchant/memberships/{membership_id}/wallet/retry-update
```

Crear endpoints técnicos necesarios por cada plataforma. Los endpoints oficiales requeridos por Apple Wallet deben respetar sus rutas/contratos correspondientes, posiblemente bajo /v1/ y la autenticación documentada por Apple. No forzar los endpoints del protocolo Apple dentro de las rutas internas si eso rompe compatibilidad.

## 12.7 Operaciones de fidelización

```text
POST /api/v1/merchant/memberships/{membership_id}/earn
POST /api/v1/merchant/memberships/{membership_id}/adjust
POST /api/v1/merchant/memberships/{membership_id}/redeem
GET  /api/v1/merchant/memberships/{membership_id}/transactions
GET  /api/v1/merchant/rewards
POST /api/v1/merchant/rewards
PATCH /api/v1/merchant/rewards/{reward_id}
```

Cada mutación debe comprobar comercio, rol, reglas de programa y concurrencia.

## 12.8 QR/NFC y reseñas

```text
GET    /api/v1/merchant/review-destination
PUT    /api/v1/merchant/review-destination
POST   /api/v1/merchant/review-destination/verify
GET    /api/v1/merchant/nfc-tags
POST   /api/v1/merchant/nfc-tags
PATCH  /api/v1/merchant/nfc-tags/{tag_id}
GET    /go/{public_slug}
GET    /api/v1/merchant/nfc-tags/{tag_id}/qr
```

La ruta /go/{public_slug} debe resolver exclusivamente a un destino validado asociado al tag, no aceptar ?url= libre que cree una redirección abierta.

## 12.9 Estadísticas

```text
GET /api/v1/merchant/dashboard/summary
GET /api/v1/merchant/dashboard/loyalty
GET /api/v1/merchant/dashboard/redemptions
GET /api/v1/merchant/dashboard/nfc
```

Los clics en enlaces de reseñas se deben denominar review_link_clicks o equivalente, nunca reviews_received salvo que exista una fuente autorizada que lo demuestre.

# 13. PANEL Y EXPERIENCIA DE USUARIO

## 13.1 Direcciones principales de navegación

Panel del comercio:

- Overview
- Program
- Members
- Transactions
- Rewards
- Wallet & Cards
- NFC & QR
- Google Reviews
- Team
- Analytics
- Settings

Panel de plataforma:

- Overview
- Merchants
- Plans (future)
- Wallet Providers
- Jobs & Errors
- Audit Log
- Settings

Ocultar las funciones que no estén implementadas. No mostrar botones que lleven a páginas ficticias.

## 13.2 Dashboard del comercio

Mostrar métricas reales, por periodo:

- Miembros registrados.
- Nuevas altas.
- Membresías activas.
- Puntos/sellos acumulados.
- Recompensas disponibles/canjeadas.
- Transacciones de fidelización.
- Fallos pendientes de sincronización de Wallet.
- Visitas a enlace de alta.
- Clics en el enlace de reseñas, si se mide de forma permitida.

Distinguir claramente valores acumulados, valores del periodo y estimaciones. Si no existen datos, mostrar estados vacíos instructivos.

## 13.3 Editor del programa

Debe permitir configurar los campos soportados en la fase actual y presentar vista previa realista de la tarjeta. Validar colores, logos, límites y reglas. Mostrar advertencias cuando una opción no esté disponible en Wallet o dependa de credenciales.

## 13.4 Página pública de alta

Requisitos:

- Mobile-first.
- Carga rápida.
- Marca del comercio.
- Explicación clara del programa y condiciones.
- Campos mínimos necesarios.
- Aviso de privacidad.
- Consentimientos separados cuando proceda.
- Mensajes de validación accesibles.
- Protección básica antiabuso.
- Confirmación de alta con siguientes pasos.
- Opciones Wallet según capacidad/configuración.
- Fallback seguro si Wallet no está disponible.

No recoger datos antes de informar de la finalidad correspondiente.

## 13.5 Identificación de la tarjeta

El personal debe poder abrir una vista móvil e introducir o escanear el identificador de una tarjeta. La UI debe mostrar solo la información necesaria para validar una operación: estado, saldo/sellos, recompensas y acciones autorizadas.

No facilitar búsquedas abiertas de clientes por teléfono/email a cualquier empleado. Si esa función se implementa, exigir permisos y registrar el acceso.

## 13.6 Diseño visual

La experiencia debe ser de SaaS B2B profesional, limpia y confiable. Evitar una UI genérica con tarjetas redundantes.

- Jerarquía visual clara.
- Formularios cortos por pasos cuando sea útil.
- Tablas con búsqueda, paginación y estados.
- Estados de carga, error, vacío y éxito explícitos.
- Diseño responsive.
- Contraste y accesibilidad.
- Teclado y lector de pantalla.
- No comunicar estados solo mediante color.
- Confirmación antes de acciones sensibles.
- Vista previa de tarjetas para Wallet.

## 13.7 Localización

Preparar textos para español como idioma principal. Evitar hardcodear todos los textos en lógica de negocio para facilitar internacionalización posterior. Usar zona horaria del comercio en visualizaciones y UTC en la base de datos.

# 14. GENERACIÓN DE QR Y MATERIALES

## 14.1 QR

Generar QR con una librería mantenida. Validar que el contenido sea una URL HTTPS esperada. Ofrecer SVG para impresión y PNG para usos sencillos. Probar el tamaño mínimo y la corrección de errores en impresiones reales.

## 14.2 Materiales descargables

Permitir, progresivamente, generar plantillas que incluyan:

- Nombre/logo del negocio.
- Instrucción neutral.
- QR.
- Indicación de “Toca o escanea”.
- Destino o propósito: “Añade tu tarjeta” o “Comparte tu experiencia”.

Mantener diseños distintos para fidelización y reseñas para evitar confusiones.

## 14.3 NFC

El software genera/gestiona la URL asociada al tag. El usuario compra y programa físicamente la etiqueta; esa operación no se considerará realizada por la aplicación salvo que exista integración hardware real.

La interfaz debe indicar claramente el proceso de instalación y la necesidad de probar cada etiqueta. Debe poder desactivar una URL pública si una etiqueta se pierde o se utiliza indebidamente; en ese caso mostrar una página de destino desactivada en lugar de redirigir.

# 15. SINCRONIZACIÓN Y TRABAJOS ASÍNCRONOS

Emisión, actualización y revocación de pases pueden fallar por credenciales, cuotas o disponibilidad externa.

Implementar:

- Estado de trabajo.
- Reintentos limitados con backoff.
- Idempotencia.
- Registro seguro de errores.
- Posibilidad de reintentar desde el panel.
- No marcar como emitido un pase hasta tener confirmación del proveedor.
- No revertir un movimiento de puntos solo porque falle la actualización visual de Wallet.
- Un panel de trabajos fallidos y pendientes para administración.

Estados sugeridos: queued, running, succeeded, partial, retrying, failed, cancelled.

No mantener una solicitud web abierta durante una operación externa lenta. Devolver un ID de trabajo y permitir consultar el estado.

# 16. SEGURIDAD TÉCNICA

## 16.1 Secretos

Nunca añadir claves/certificados reales al repositorio. El .env.example contiene solo nombres y valores vacíos/ficticios.

Variables potenciales:

```dotenv
APP_ENV=development
APP_SECRET_KEY=
DATABASE_URL=
AUTH_ENABLED=true
AUTH_SESSION_SECRET=
PUBLIC_BASE_URL=
APPLE_PASS_TYPE_IDENTIFIER=
APPLE_TEAM_IDENTIFIER=
APPLE_PASS_CERT_PATH=
APPLE_WWDR_CERT_PATH=
APPLE_PASS_CERT_PASSWORD=
APPLE_APNS_KEY_PATH=
APPLE_APNS_KEY_ID=
GOOGLE_WALLET_ISSUER_ID=
GOOGLE_WALLET_SERVICE_ACCOUNT_JSON=
GOOGLE_WALLET_ENVIRONMENT=test
NFC_REDIRECT_SIGNING_SECRET=
LOG_LEVEL=INFO
```

La implementación final puede variar. Nunca colocar contenido de certificados, contraseñas o JSON de cuenta de servicio dentro del frontend ni subirlo a Git.

## 16.2 Controles de acceso

- Fail-closed para entornos de producción.
- Cookies de sesión seguras.
- Autorización multiempresa en cada endpoint.
- Protección CSRF según el patrón de auth.
- Rate limits para autenticación, altas y operaciones sensibles.
- Límites de archivos subidos.
- Validación de schemas en entradas y salidas.
- SQL parametrizado/ORM.
- No exponer documentación/debug en producción sin decisión explícita.

## 16.3 SSRF y URLs

Las URLs de reseñas y cualquier URL que la plataforma recupere deben validarse. No crear funciones generales que hagan fetch a cualquier destino proporcionado por el cliente.

La ruta de redirección no debe abrir redirecciones arbitrarias. Las URLs de destino deben ser HTTPS y estar en los dominios/protocolos aprobados tras verificación. Si se admite un dominio externo para una función legítima, definir allowlist o validación específica.

## 16.4 Protección contra doble operación

- Idempotency keys únicas en acumulaciones/canjes.
- Transacciones atómicas.
- Bloqueos/optimistic concurrency para saldos.
- Constraints en base de datos.
- Tests de concurrencia para doble canje.

## 16.5 Uploads

- Tamaño máximo.
- Validación de contenido real.
- Renombrado interno y claves no controladas por el usuario.
- Escaneo/normalización de imágenes si procede.
- No servir archivos activos con scripts.
- Separación por comercio en permisos de almacenamiento.

## 16.6 Seguridad del logging

No registrar contraseñas, tokens, cookies, claves privadas ni URLs que contengan tokens de membresía. Usar identificadores internos y correlation IDs. Limitar el acceso a logs.

## 16.7 Cabeceras y navegador

Configurar HTTPS en despliegue público, CSP, X-Content-Type-Options, Referrer-Policy, protección de framing, cache control para páginas sensibles y CORS mínimo. Probar la compatibilidad CSP con Next.js en la configuración real. No añadir unsafe-inline sin evaluar alternativas y documentar el riesgo.

## 16.8 Threat modeling

Antes de producción, evaluar al menos:

- Usuario de un comercio accediendo a otro comercio.
- Empleado que intenta concederse/canjear recompensas indebidamente.
- Replay de solicitudes.
- Doble canje concurrente.
- Adivinación de IDs públicos.
- Robo de credenciales.
- Claves de Wallet filtradas.
- Redirecciones abiertas.
- Uso malicioso de URLs NFC.
- Spam en alta pública.
- Falsificación de saldo mostrado en una tarjeta cacheada.
- Fallo del proveedor Wallet.
- Pérdida o compromiso de copia de seguridad.
- Inyección de archivos/HTML en branding.
- Enumeración de clientes.

# 17. COSTES Y ESTRATEGIA DE PROVEEDORES

## 17.1 Regla de transparencia

Priorizar herramientas de código abierto y autoalojables, pero no afirmar que todo es gratis si existe hardware, dominio, electricidad, certificado/inscripción de proveedor, cuenta de desarrollador, servicio externo o cuota real.

Antes de tomar decisiones comerciales sobre precios, verificar las tarifas vigentes en las páginas oficiales.

## 17.2 Modo desarrollo

El sistema debe arrancar sin credenciales Apple/Google mediante proveedores simulados. El modo simulado nunca debe confundirse con una tarjeta emitida realmente.

Mostrar SIMULATED o equivalente en la UI y en logs cuando se usen providers fake.

## 17.3 Modo pruebas

Permitir configurar proveedores en entorno de test, sin datos reales ni credenciales de producción. No mezclar identificadores de prueba y producción.

## 17.4 Modo producción

Antes de activar Wallet real:

- Verificar requisitos de cuenta/emisor/certificados.
- Verificar secreto/permiso de claves.
- Verificar HTTPS público.
- Verificar política de actualización.
- Verificar condiciones de uso y marca.
- Estimar volumen, cuotas y costes.
- Documentar proceso de rotación de credenciales.

No bloquear el programa de fidelización manual por estar Wallet sin configurar; las opciones deben comunicar sus límites.

# 18. DESPLIEGUE Y RED

## 18.1 Entornos

Distinguir desarrollo local, pruebas y producción. No copiar datos reales a un entorno de pruebas sin justificación y minimización.

## 18.2 Servidor doméstico

El proyecto puede desarrollarse y ejecutarse inicialmente en Docker en un servidor propio. Documentar puertos, volúmenes, variables, copias y restauración.

Importante: un panel de administración privado puede ser accesible solo por Tailscale; pero las páginas de alta públicas, enlaces NFC/QR usados por clientes externos y los servicios de Wallet que deban ser alcanzados por teléfonos/proveedores necesitan HTTPS y conectividad pública apropiada. Una app accesible exclusivamente dentro de tailnet no basta para un producto usado por clientes externos.

La exposición pública se debe decidir de forma explícita. No abrir puertos ni configurar un túnel público automáticamente. Evaluar dominio, proxy inverso, certificados, firewall, backups, autenticación y ataque de superficie antes del despliegue.

No usar Tailscale Funnel ni otro método de publicación pública sin autorización explícita del usuario.

## 18.3 Docker

Usar contenedores no privilegiados siempre que resulte práctico, healthchecks, redes internas para base de datos, volúmenes persistentes y límites razonables. No publicar PostgreSQL a Internet. Exponer solo lo estrictamente necesario.

## 18.4 Backups

Implementar copia de seguridad y recuperación documentadas:

- Backup automatizable.
- Retención definida.
- Integridad comprobada.
- Restauración probada en instancia aislada.
- Comparación de datos esenciales.
- Protección de los ficheros de backup.
- No incluir claves privadas si existe una alternativa más segura; documentar cómo recuperarlas mediante gestor de secretos.

Una copia no se considera validada solo porque el comando haya creado un archivo. Debe existir al menos una prueba de restauración completa.

## 18.5 Observabilidad

Registrar errores de proveedor Wallet, trabajos retrasados, acumulaciones/canjes fallidos, salud de base de datos y errores de autenticación. Evitar datos personales en logs. Añadir alertas cuando el uso real lo requiera.

# 19. TESTING Y CRITERIOS DE CALIDAD

## 19.1 Unit tests

Cubrir:

- Reglas de puntos y sellos.
- Canjes y validación de saldo.
- Idempotencia.
- Reversión de movimientos.
- Permisos multiempresa.
- Estados de programas.
- Validación de destinos de reseñas.
- Generación de slugs/tokens.
- Restricciones de URLs de redirección.
- Conversión de zonas horarias.
- Cálculo de estadísticas.

## 19.2 Integración

Cubrir:

- Migraciones.
- PostgreSQL real de test.
- Ledger y canje en transacción.
- Aislamiento entre comercios.
- Adaptadores Wallet con mocks.
- Fallos y reintentos de trabajos.
- Endpoints públicos.
- Emisión de QR.
- Redireccionamiento de etiquetas.

## 19.3 E2E mínimo

- Crear un comercio.
- Crear un usuario merchant_owner.
- Login.
- Crear un programa.
- Publicar el programa.
- Abrir página pública de alta.
- Crear una membresía con datos mínimos.
- Obtener las opciones de Wallet simuladas.
- Abrir la tarjeta web/fallback.
- Registrar una acumulación desde cuenta staff.
- Verificar ledger y nuevo saldo.
- Canjear una recompensa.
- Intentar canjear otra vez con la misma idempotency key y comprobar que no duplica el efecto.
- Probar doble canje concurrente.
- Configurar un enlace de reseña de prueba.
- Generar QR/enlace NFC lógico.
- Abrir el redirect y comprobar que lleva al destino exacto permitido.
- Comprobar que no existe selección por satisfacción ni incentivo de reseña.
- Verificar estadísticas con datos reales de prueba.
- Confirmar que un comercio no puede leer datos de otro.

## 19.4 Integración real Wallet

No hacer pruebas reales de emisión hasta tener credenciales legítimas y un dispositivo/cuenta de prueba. La suite ordinaria usa mocks y no depende de Internet.

Checklist manual para cada proveedor:

- Emisión.
- Instalación.
- Visualización.
- QR/identificador.
- Actualización tras una operación.
- Fallo/reintento.
- Revocación o estado inactivo.
- No filtración de credenciales.

## 19.5 Calidad

Antes de cerrar cada fase, ejecutar herramientas pertinentes, corregir fallos y resumir qué se ha comprobado. No afirmar “todo funciona” por haber compilado. Separar unit tests, integración, E2E y pruebas manuales reales.

# 20. PLAN DE DESARROLLO POR FASES

El agente debe mantener un docs/IMPLEMENTATION_PLAN.md con tareas, estado y criterios de aceptación. Una fase no está completa solo por escribir código.

## FASE 0 — Inspección y plan

Objetivo: comprender el repositorio y confirmar los requisitos.

Tareas:

- Inspeccionar Git, archivos, dependencias y convenciones.
- Revisar si existe código previo.
- Detectar secretos sin imprimir sus valores.
- Confirmar stack actual.
- Identificar decisiones que bloquean el MVP.
- Convertir este documento en tareas verificables.
- Documentar decisiones de arquitectura importantes en ADR cuando sea necesario.

Aceptación:

- Existe resumen del estado real.
- Existe plan ordenado.
- No se sobrescribió trabajo útil.
- Se identificaron las credenciales externas que no están configuradas.
- No se ha implementado más de lo autorizado.

## FASE 1 — Esqueleto y entorno local

Objetivo: app ejecutable en local.

Tareas:

- Configurar frontend y backend.
- Configurar PostgreSQL y migraciones.
- Añadir .env.example.
- Configurar Docker Compose.
- Añadir healthcheck/readiness.
- Configurar logging y correlation ID.
- Configurar herramientas de calidad.
- Documentar arranque y test.

Aceptación:

- Arranque repetible.
- DB persistente.
- Migraciones funcionan.
- Tests básicos ejecutan sin secretos reales.

## FASE 2 — Autenticación, comercios y aislamiento

Objetivo: base multiempresa segura.

Tareas:

- Modelar usuarios, comercios y roles.
- Implementar login/logout/me.
- Implementar sesiones seguras.
- Implementar permisos de plataforma y comercio.
- Añadir auditoría mínima.
- Implementar las pantallas básicas.
- Añadir tests de acceso cruzado entre comercios.

Aceptación:

- Usuarios no ven datos ajenos.
- Producción no arranca con auth desactivada.
- Sesiones invalidables.
- Hay pruebas negativas de autorización.

## FASE 3 — Programa básico de fidelización

Objetivo: configurar un programa sin Wallet todavía.

Tareas:

- Crear programas y ubicaciones.
- Crear modo stamps y reglas mínimas.
- Crear modo points si no añade complejidad excesiva; si la añade, posponerlo explícitamente.
- Crear recompensas.
- Crear página del programa.
- Añadir estados draft/active/paused/archived.
- Versionar condiciones visibles.
- Validar reglas y límites.

Aceptación:

- Comercio crea/edita/publica/pausa un programa.
- Reglas se validan en backend.
- La página pública muestra las condiciones correctas.

## FASE 4 — Alta de clientes y membresías

Objetivo: incorporar a clientes al programa de forma segura.

Tareas:

- Crear members y memberships.
- Diseñar formulario mínimo.
- Mostrar aviso de privacidad y consentimientos necesarios.
- Crear identificadores/token opacos.
- Añadir rate limiting y controles antiabuso.
- Crear vista de membresía web.
- Añadir flujo de gestión/eliminación conforme a política.

Aceptación:

- Cliente se registra en el programa correcto.
- Un comercio no puede consultar miembros de otro.
- No aparecen datos personales en URLs o QR.
- Alta pública no permite enumeración.

## FASE 5 — Ledger, acumulación y canje

Objetivo: operar realmente los puntos/sellos sin Wallet.

Tareas:

- Crear ledger inmutable.
- Implementar acumulación autorizada.
- Implementar canje transaccional.
- Implementar idempotencia.
- Implementar reversión/ajuste con motivo.
- Añadir auditoría.
- Añadir UI móvil para staff.
- Añadir tests de concurrencia y doble canje.

Aceptación:

- El saldo es derivable del ledger.
- Canje no permite saldo negativo ni doble gasto.
- Reintentos no duplican operaciones.
- Correcciones generan movimientos trazables.

## FASE 6 — Tarjeta web y códigos QR

Objetivo: disponer de un identificador usable antes de Wallet.

Tareas:

- Generar identificador público opaco.
- Mostrar tarjeta web en móvil.
- Crear QR con el identificador seguro.
- Validar token y estado con backend.
- Crear interfaz staff para escanear/introducir código; si el escaneo de cámara requiere permisos o librería, documentarlo y dar fallback manual.
- Añadir branding básico.

Aceptación:

- El personal identifica una membresía sin revelar datos innecesarios.
- QR no concede privilegios administrativos.
- El backend valida saldos y transacciones.

## FASE 7 — Adaptador Apple Wallet

Objetivo: emitir una tarjeta de prueba Apple Wallet real.

Prerequisitos: cuenta/certificados legítimos, HTTPS accesible y documentación vigente revisada.

Tareas:

- Implementar configuración por entorno.
- Implementar generación/firmado de .pkpass.
- Validar recursos y estructura.
- Asociar pase a membership.
- Probar descarga e instalación.
- Implementar endpoints de actualización si el alcance lo incluye.
- Gestionar APNs y registros de dispositivo conforme a documentación.
- Añadir estados de error y retry.

Aceptación:

- Pase de test firmado e instalable.
- No se filtran claves/certificados.
- La operación de fidelización no depende de que el pase se actualice.
- Fallos de actualización son visibles.

## FASE 8 — Adaptador Google Wallet

Objetivo: emitir una tarjeta Google Wallet de prueba real.

Prerequisitos: issuer/configuración y credenciales legítimas, documentación vigente.

Tareas:

- Implementar clases/objetos del modelo de Google.
- Crear flujo seguro de Add to Google Wallet.
- Firmar/emitir los JWT en backend.
- Actualizar objetos según reglas del proveedor.
- Gestionar estados, errores y reintentos.
- Añadir UI condicional.

Aceptación:

- Flujo probado en entorno habilitado.
- Claves solo en backend.
- Identificadores sin duplicación.
- Provider deshabilitado no rompe el resto de la aplicación.

## FASE 9 — NFC/QR para alta de fidelización

Objetivo: ayudar al comercio a instalar y distribuir enlaces.

Tareas:

- Crear URL pública estable para alta.
- Registrar tags lógicos.
- Generar QR imprimible.
- Mostrar instrucciones para programar etiqueta NFC.
- Probar URL en teléfonos compatibles.
- Permitir desactivar/cambiar destino controladamente.
- Preparar plantillas para mostrador.

Aceptación:

- El tag de fidelización lleva al programa correcto.
- Los tags no contienen PII.
- Se puede desactivar una URL comprometida.
- Las instrucciones dejan clara la prueba física.

## FASE 10 — Google Reviews NFC/QR

Objetivo: gestionar el enlace oficial de reseñas de cada comercio.

Tareas:

- Crear configuración review_destinations.
- Permitir introducir un enlace oficial y comprobarlo manualmente.
- Añadir estado de verificación y fecha.
- Crear tag lógico separado de los de fidelización.
- Generar QR/material imprimible.
- Crear redirect fijo/allowlisted opcional.
- Registrar métricas mínimas de clics si se decide que son útiles.
- Añadir copy neutral de solicitud de opinión.
- Añadir validaciones/tests que impidan review gating e incentivos.
- Documentar qué representan y qué no representan las métricas.

Aceptación:

- Tag lleva a destino de reseña verificado.
- No hay filtros de satisfacción.
- No hay incentivos ni asociación de reward con reseña.
- No se intenta publicar reseñas mediante API.
- Métrica denominada clic/visita al enlace.

## FASE 11 — Paneles, analítica y exportación

Objetivo: dar al comercio visibilidad útil.

Tareas:

- Implementar dashboard de fidelización.
- Añadir métricas de miembros y movimientos.
- Añadir recompensas/canjes.
- Añadir errores de sincronización Wallet.
- Añadir clics NFC/QR con minimización.
- Implementar filtros temporales.
- Añadir exportación solo de datos propios y permitidos.

Aceptación:

- Todos los valores proceden de la base de datos.
- Las definiciones están documentadas.
- No se presenta clic como reseña recibida.

## FASE 12 — Seguridad, privacidad y pruebas preproducción

Objetivo: revisión completa previa a usar datos reales.

Tareas:

- Revisar RBAC/aislamiento multiempresa.
- Revisar CSRF, cookies, rate limits y cabeceras.
- Revisar URLs/redirects/SSRF.
- Revisar uploads.
- Revisar secretos y rotación.
- Revisar ledger y operaciones concurrentes.
- Revisar cumplimiento del flujo de reseñas.
- Ejecutar pruebas E2E completas.
- Preparar backups y restauración.
- Definir retención/eliminación/exportación.
- Preparar monitorización y alertas.
- Completar documentación de despliegue.

Aceptación:

- Checklist cerrado con evidencias.
- Restauración de backup probada.
- Ningún secreto en Git.
- Pruebas de acceso cruzado aprobadas.
- Integraciones fallidas no corrompen el ledger.
- Revisión legal adecuada antes de producción con datos reales.

## FASE 13 — Piloto comercial

Objetivo: probar el producto en un establecimiento real.

Tareas:

- Definir condiciones y precio de piloto.
- Preparar contrato/condiciones con revisión adecuada.
- Preparar programa real con consentimiento y aviso correctos.
- Instalar etiqueta de alta y etiqueta de reseñas por separado.
- Probar ambos flujos con iOS y Android.
- Entrenar al personal.
- Registrar incidencias y feedback.
- Medir altas, uso real y canjes.
- Revisar si el flujo de reseñas sigue siendo neutral y voluntario.
- Corregir antes de escalar.

Aceptación:

- Un establecimiento puede operar un programa real de principio a fin.
- Datos y recompensas son coherentes.
- El negocio sabe realizar copia/soporte de sus operaciones según el servicio contratado.
- Los fallos tienen procedimiento operativo.

# 21. CRITERIOS DE ACEPTACIÓN DEL MVP COMPLETO

El MVP no se considera terminado hasta poder demostrar, con tests y pruebas manuales apropiadas, este recorrido:

- Platform owner crea un comercio.
- El comercio inicia sesión.
- Configura un programa de sellos.
- Publica la página de alta.
- Cliente se registra con datos mínimos.
- El cliente ve una tarjeta web y las opciones Wallet configuradas.
- En el modo simulado queda claro que no se ha emitido un pase real.
- El personal registra una visita/sello con autorización.
- El sistema registra un movimiento y actualiza saldo.
- El cliente alcanza y canjea una recompensa.
- El sistema impide doble canje.
- La vista de tarjeta refleja los datos disponibles o indica la última sincronización.
- El comercio configura enlace verificado de Google Reviews.
- La plataforma produce QR/link separado para fidelización y reseñas.
- Tocar la etiqueta de reseñas abre el enlace correcto de Google.
- No se solicita ni filtra por satisfacción.
- No se entrega incentivo por reseñar.
- El dashboard refleja datos reales.
- Un usuario de otro comercio no puede leer/editar datos.
- Backup y restauración están probados y documentados.

# 22. DEFINICIÓN DEL PILOTO COMERCIAL

Antes de construir funcionalidades avanzadas, definir la oferta inicial. El código no debe fijar precios comerciales como constantes inmutables.

El piloto debe poder configurar:

- Precio de instalación opcional.
- Cuota mensual opcional.
- Número de ubicaciones.
- Número de programas activos.
- Volumen aproximado de membresías o límites técnicos.
- Soporte incluido.
- Material NFC/QR incluido o vendido por separado.
- Servicios Wallet incluidos y dependencias de certificados/cuentas.
- Política de cancelación y exportación.

No inventar métricas de aumento de ventas ni prometer ROI garantizado.

Recomendar validar con uno o dos establecimientos antes de convertir planes comerciales en lógica de facturación automática.

# 23. GESTIÓN DE ERRORES

Definir errores de dominio legibles, por ejemplo:

- program_not_active
- membership_not_found
- membership_inactive
- insufficient_points
- reward_not_available
- duplicate_operation
- merchant_access_denied
- wallet_provider_not_configured
- wallet_issue_failed
- wallet_update_pending
- review_destination_not_verified
- tag_disabled
- invalid_redirect_destination

Las respuestas no deben filtrar si una membresía privada de otro comercio existe. Utilizar status codes coherentes y respuestas uniformes donde ayude a evitar enumeración.

Los errores de proveedor externo deben transformarse en códigos internos sin exponer tokens, certificados ni detalles secretos.

# 24. EVALUACIÓN DE CALIDAD Y OPERACIÓN

## 24.1 Métricas operativas

- Altas completadas/fallidas.
- Tiempo de emisión de pase.
- Trabajos Wallet pendientes/fallidos.
- Actualizaciones de pase exitosas.
- Operaciones de puntos/sellos.
- Canjes rechazados/aceptados.
- Errores de idempotencia.
- Latencia de API.
- Errores de base de datos.
- Clics de tags por tipo.

## 24.2 Métricas de negocio

- Miembros registrados por programa.
- Miembros activos según una definición explícita.
- Recompensas canjeadas.
- Frecuencia de transacción agregada.
- Uso de etiquetas de alta.
- Clics en enlaces de reseñas.

No asociar clics individuales a identidades de miembros salvo que exista una necesidad legítima, base apropiada y diseño documentado. No declarar que un aumento de clics equivale a un aumento de reseñas o de valoración.

## 24.3 Calidad de sincronización

Wallet puede estar temporalmente desactualizado. Mostrar en panel el estado del proveedor y permitir reintentar de manera segura. La operación de fidelización confirmada se mantiene en backend aunque una actualización de pass falle.

# 25. DOCUMENTACIÓN DEL REPOSITORIO

Mantener de manera progresiva:

- README.md: instalación, arranque, variables, pruebas y estado real.
- docs/IMPLEMENTATION_PLAN.md: fases y estado.
- docs/ARCHITECTURE.md: componentes y flujos.
- docs/DATA_MODEL.md: entidades, relaciones y constraints.
- docs/API_SPEC.md: endpoints implementados.
- docs/SECURITY.md: autenticación, autorización, amenazas, secretos.
- docs/PRIVACY.md: datos, finalidades, retención, exportación, borrado.
- docs/WALLET_INTEGRATIONS.md: precondiciones y flujos Apple/Google.
- docs/NFC_AND_REVIEWS.md: tags, URLs, políticas de reseñas y materiales.
- docs/DEPLOYMENT.md: desarrollo, staging, producción, TLS, backup y restauración.
- docs/TEST_STRATEGY.md: suites y criterios.
- docs/ADR/: decisiones con consecuencias importantes.

No crear documentación que afirme que una integración está completa si solo hay un mock.

# 26. REGLAS PARA EL AGENTE DE PROGRAMACIÓN

## 26.1 Antes de cambiar código

- Leer este documento completo o las secciones aplicables.
- Inspeccionar el repositorio y el estado de Git.
- Identificar la fase actual.
- Revisar código y tests existentes.
- Formular un plan de cambios pequeño y verificable.
- Detectar requisitos externos y dependencias.
- No volver a preguntar información que ya está en el repositorio/documentación.
- Si falta un detalle no bloqueante, elegir la opción conservadora y documentarla.
- Si una decisión afecta a legalidad, seguridad, coste o arquitectura de forma importante, documentar la incertidumbre antes de activar la funcionalidad real.

## 26.2 Forma de trabajar

- Implementar una fase a la vez.
- Trabajar en unidades pequeñas.
- No borrar funcionalidades existentes sin una razón clara.
- No reescribir todo el repo para introducir una preferencia tecnológica.
- No incorporar dependencias sin evaluar mantenimiento/licencia/seguridad.
- No crear agentes autónomos innecesarios.
- No usar datos ficticios como si fueran reales.
- No llamar “Wallet integrado” a un mock.
- No activar una integración real sin sus credenciales y pruebas requeridas.

## 26.3 Código

- Tipos y esquemas estrictos.
- Lógica de dominio separada de infraestructura.
- Manejo explícito de errores.
- Timeouts en llamadas externas.
- Transacciones para operaciones de fidelización.
- Idempotencia en comandos repetibles.
- Ninguna clave en frontend.
- Validación de todas las entradas externas.
- Sin acceso directo desde frontend a DB.
- Sin SQL dinámico no parametrizado.
- No capturar excepciones y continuar silenciosamente.

## 26.4 Seguridad por función

Toda nueva ruta debe documentar:

- Si es pública o autenticada.
- Rol requerido.
- Límite de peticiones.
- Datos que devuelve.
- Riesgo de enumeración.
- Si necesita idempotencia.
- Efectos secundarios.

Toda nueva operación de saldo o recompensa debe añadir tests de integridad y concurrencia adecuados.

## 26.5 Cierre de cada tarea

Al terminar:

- Ejecutar pruebas relevantes.
- Ejecutar formatter/linter/types.
- Revisar migraciones.
- Comprobar criterios de aceptación.
- Actualizar documentación y plan.
- Resumir archivos modificados.
- Indicar qué pruebas se ejecutaron realmente.
- Indicar limitaciones y pasos externos pendientes.

No afirmar éxito si los tests no se han ejecutado o fallan.

# 27. PRIMER PROMPT DE ARRANQUE DEL REPOSITORIO

Cuando este archivo esté en la raíz del nuevo repositorio, la primera instrucción que debe recibir el agente de programación es:

```text
Lee AGENTS.md completo. Vamos a construir LocalAI Fidelity de forma incremental, con el documento como fuente de verdad.

PRIMERA TAREA: FASE 0 — INSPECCIÓN Y PLANIFICACIÓN. No implementes todavía funcionalidades de producto.

1. Inspecciona el repositorio, Git, stack, dependencias y convenciones.
2. Identifica si existe código previo y consérvalo salvo razón justificada.
3. Busca secretos expuestos sin mostrar sus valores.
4. Compara el estado del repositorio con los objetivos y fases de AGENTS.md.
5. Propón una arquitectura concreta para el MVP, proporcionada al problema.
6. Define el esquema inicial mínimo y sus decisiones importantes.
7. Identifica qué componentes podrán probarse con mocks y qué requerirá credenciales/cuentas reales de Apple o Google.
8. Identifica los riesgos que bloquean un producto público: aislamiento multiempresa, seguridad, privacidad, actualización de Wallet y políticas de Google Reviews.
9. Crea o actualiza docs/IMPLEMENTATION_PLAN.md con tareas ordenadas, dependencias y criterios de aceptación comprobables.
10. Documenta las decisiones arquitectónicas relevantes en ADR si procede.

No construyas todas las fases ni generes archivos vacíos para aparentar avance.
No actives emisión real de Wallet, redirecciones públicas ni manejo de datos reales hasta que sus requisitos estén definidos.

Al finalizar, presenta un resumen del estado real, las decisiones propuestas, los riesgos y la siguiente tarea concreta. Espera a que la fase 0 esté revisada antes de iniciar la implementación de la fase 1.
```

# 28. DECISIÓN FINAL DE PRODUCTO

LocalAI Fidelity debe convertirse en una plataforma sencilla para fidelizar clientes y facilitar reseñas auténticas, no en una colección de integraciones desconectadas.

El núcleo del producto es:

- Programa de fidelización por comercio.
- Alta del cliente y membresía.
- Tarjeta web y Wallet.
- Ledger seguro de puntos/sellos.
- Registro y canje de recompensas.
- Etiqueta NFC/QR para el alta de fidelización.
- Etiqueta NFC/QR independiente que abre el enlace de reseñas de Google.
- Panel de negocio y estadísticas reales.

Regla irrenunciable del módulo de reseñas: facilitar el acceso a Google Reviews de forma neutral, voluntaria y sin incentivos, sin filtrar clientes por satisfacción y sin automatizar la creación de reseñas.

Regla irrenunciable del módulo de fidelización: el backend es la fuente de verdad; las operaciones de puntos/sellos son auditables, idempotentes y autorizadas; Wallet es una representación sincronizada, no la base contable.

Construye primero el flujo completo más pequeño que demuestre esas dos reglas. Después, amplía el producto con evidencia de uso real.

# 29. REFERENCIAS OFICIALES TÉCNICAS

Antes de implementar o actualizar integraciones, consultar las versiones vigentes de estas fuentes; las APIs y políticas pueden cambiar.

### Apple Wallet

- Wallet Passes: https://developer.apple.com/documentation/walletpasses
- Añadir servicio web de actualización: https://developer.apple.com/documentation/walletpasses/adding-a-web-service-to-update-passes
- Distribuir y actualizar pases: https://developer.apple.com/documentation/walletpasses/distributing-and-updating-a-pass

### Google Wallet

- Tarjetas de fidelización: https://developers.google.com/wallet/retail/loyalty-cards
- Clases y objetos: https://developers.google.com/wallet/retail/loyalty-cards/overview/how-classes-objects-work
- Flujo Add to Google Wallet: https://developers.google.com/wallet/retail/loyalty-cards/overview/add-to-google-wallet-flow
- Portal principal: https://developers.google.com/wallet

### Google Reviews

- Política de contenido prohibido/restringido: https://support.google.com/contributionpolicy/answer/7400114?hl=es
- Guía para conseguir más reseñas de Google Business Profile: https://support.google.com/business/answer/3474122?hl=es
- API de datos de reseñas de Business Profile: https://developers.google.com/my-business/content/review-data

### Privacidad

- RGPD: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- Agencia Española de Protección de Datos: https://www.aepd.es/

No considerar un resultado de búsqueda, un artículo de terceros o una memoria del modelo suficiente para resolver un requisito de integración: verificar la documentación oficial vigente.
