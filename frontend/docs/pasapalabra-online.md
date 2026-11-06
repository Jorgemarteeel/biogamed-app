# Interfaz de Pasapalabra en línea

Revisión posterior de distribución: [espacio disponible, matriz de tamaños y límites](pasapalabra-layout.md).
Incluye preparación, sala, juego y resultado compartiendo presentación con local.

Contratos, persistencia y verificación: [documentación backend](../../backend/docs/pasapalabra-online.md).
Reutiliza el componente de juego local y su presentación aprobada, sin cambiar
Trivial. `/pasapalabra` ofrece modo local, creación online por temática o unión
por código. Preparación online conserva categoría/dificultad y disponibilidad,
sin campo de invitado. `/pasapalabra/rooms/{id}` recupera sala; al iniciarse
navega a `/pasapalabra/{match_id}` para ambas cuentas.

HTTP secuencial: sala cada 1500 ms, partida cada 1000 ms, timeout 10 s. Foco y
visibilidad solicitan refresco; un poll pendiente impide otro. Versión y fecha
de servidor descartan estados antiguos. Reintentos inciertos conservan UUID y
carga y bloquean acciones diferentes. 409 actualiza estado sin repetir acción.
No hay indicador de presencia: error de conexión no afirma ausencia del rival.
Al recuperarse se retira el aviso. Relojes extrapolados desde fechas de servidor;
no deciden corrección o vencimiento. Polls no limpian borrador de la misma pregunta
ni enfocan controles. Pregunta privada ausente implica espera sin formulario;
solo puede abandonarse la participación propia. También se filtran correcciones
por `self_position` en cliente como defensa adicional.

401 de un token vigente guarda la ruta de Pasapalabra en sessionStorage antes
de redirigir al login. Reentrada admite únicamente rutas internas validadas,
consume el destino y recupera partida/sala. El formulario de login usa método
POST también antes de hidratar, evitando credenciales en query string.
Si otra pestaña ya eliminó el token, sala y partida ofrecen un enlace a iniciar
sesión que también conserva el destino. Este caso y la expiración natural se
verificaron visualmente tras la pausa de uso, recuperando los resultados propios.

Sala y juego conservan controles táctiles, teclado, nombres, símbolos y leyendas.
Móvil prioriza pregunta y ambos relojes; roscos informativos, sin saltos de
pregunta. Las correcciones y el historial son propios, el rival solo tiene
resumen público. Celebración únicamente al observar RUNNING→FINISHED normal,
finita y respetando CSS de movimiento reducido. Resultado inicial/recargado y
abandono no la disparan. Se conservan las limitaciones de revisión y la aprobación
del usuario de la presentación local previamente documentadas.

Revisión real: dos autenticaciones separadas por origen, en un equipo, no dos
dispositivos físicos. Flujo completo y resultado normal/abandono, recarga,
interrupción y recuperación, escritorio y viewport móvil comprobados. No hay
emulación nativa del ajuste de movimiento reducido ni lector de pantalla físico.
102 tests frontend aprobados; 25 específicos comprobados tras el último ajuste de mensajes y refresco;
tipos, lint y build aprobados. UUID pendientes y borradores viven en pestaña:
recargar recupera estado confirmado, no texto no enviado ni operación incierta.

## Probar la demo

1. Abrir `http://localhost:13004/pasapalabra` con la cuenta docente demo existente.
2. Abrir `http://127.0.0.1:13004/pasapalabra` con la segunda cuenta ficticia. Ambos
   orígenes tienen almacenamiento de autenticación separado. No usar dos pestañas
   del mismo origen con cuentas distintas, porque compartirían su token.
3. Credenciales fuera de Git: fichero docente local habitual y fichero
   `C:\Users\Jorge\Documents\Playground\online-demo-credentials.json` para la
   segunda cuenta. No copiarlas a documentación o repositorio.
4. En docente: «En línea», temática ficticia «Pasapalabra - prueba API aislada
   2026-11-04», conservar filtros disponibles, crear sala y compartir código.
5. En rival: unir con código; confirmar ambos, iniciar con creador. En este banco
   ficticio la respuesta de verificación es `Aorta`. Probar responder, pasar,
   recargar y consultar el historial propio; ambos pueden preparar otra partida.

La demo permanece limitada a loopback. Probar dos dispositivos reales requiere
un despliegue accesible y configurar URL pública de API/CORS; esta tarea no
publica servicios. No hay lista de salas pendientes: conservar su URL para
recuperarla; la consulta del historial permite recuperar partidas ya iniciadas.

## Revisión del selector, sala y unión — 5 de noviembre de 2026

Selector compacto con dos tarjetas SVG: una cuenta y un invitado junto al mismo
dispositivo, o dos cuentas con dispositivos separados. Etiquetas completas,
`aria-pressed`, marca «Seleccionado» y foco visible. En línea requiere elegir
«Crear sala» o «Unirme con código»; nunca muestra catálogo y unión a la vez.
Crear conserva temática y filtros existentes. Elegir unión enfoca su campo;
las consultas de sala no mueven el foco.

La sala deriva del servidor el recuento «Jugadores · 1/2» o «2/2», incluye creador,
marca «Tú», plaza vacante y estados «Sin confirmar»/«Preparado». No muestra
presencia ni interpreta pertenencia como conexión. Explica qué falta para iniciar.
Salida y nueva unión actualizan plaza y eliminan ambas confirmaciones mediante
el mismo polling/versiones, sin cambios de reglas ni recarga manual.

Diagnóstico reproducido en navegador: sin sesión, POST `/pasapalabra/rooms/join`
devolvía 401 y `{"detail":"Not authenticated"}`; antes se rotulaba erróneamente
como caducidad. Ahora distingue sesión ausente de credencial no válida/caducada.
Los rechazos de sala mantienen su causa, sin pedir login por un 404 o 409.
`localhost` y `127.0.0.1` usan almacenamientos de autenticación independientes:
identificarse en uno no identifica en el otro. Ambos preflight CORS devolvieron
200 con su origen exacto; no se encontró un defecto de CORS en esta demo.
No es posible atribuir retrospectivamente el token de la prueba original del
usuario: lo reproducido identifica condiciones y defectos comprobados, no supone
que todas las causas de 401 sean vencimiento.

El código se guarda en sessionStorage de pestaña/origen al escribir y antes de
enviar. Sobrevive al redirect del interceptor y al login. Al volver selecciona
«En línea → Unirme con código», recupera el campo y explica que debe confirmarse
otra vez. Nunca se une automáticamente. Lo borra únicamente al vaciar el campo
o confirmar una unión exitosa; almacenamiento bloqueado no rompe la operación.
No cambia el TTL de autenticación ni añade renovación de tokens. Los UUID de
operaciones inciertas siguen conservándose en memoria y bloquean otras acciones.

En desarrollo, `[Pasapalabra:join]` registra solo estado HTTP, si se envió Bearer
y causa permitida de respuesta. Nunca registra token, contraseña, invitación ni
carga enviada; no se ejecuta en producción. Se comprobaron en peticiones reales:

| Condición | HTTP / respuesta | Verificación |
| --- | --- | --- |
| Sin sesión | 401 / `Not authenticated`, Bearer ausente | Navegador y HTTP |
| JWT vencido firmado | 401 / `No se pudieron validar las credenciales.`, Bearer presente | Navegador y HTTP |
| Creador con su código | 409 / `DISTINCT_ACCOUNT_REQUIRED` | HTTP y prueba de interfaz |
| Sala llena | 409 / `ROOM_FULL` | FastAPI automatizada con tercera cuenta ficticia |
| Código incorrecto | 404 / `ROOM_UNAVAILABLE` | Navegador, HTTP y pruebas |
| Sala cancelada | 409 / `ROOM_CANCELLED` | HTTP y pruebas |
| Sala caducada | 409 / `ROOM_EXPIRED` | HTTP y pruebas |

Revisión visual: dos cuentas demo distintas, sesiones separadas por origen en un
equipo; selector, creación, código, login, retorno sin auto unión, listado en ambos
clientes, confirmar, salir y volver a entrar e iniciar la misma partida 13.
Se cerró esa partida ficticia por abandono. Se dejó sala 8 sin iniciar, con ambas
cuentas sin confirmar, para revisión (caduca a los treinta minutos originales).
Escritorio 1280×900 y móvil 390×844 comprobados; sin desbordamiento horizontal.
Enter activa tarjetas y envío, el foco llega a código y permanece estable.

Para probar vencimiento sin esperar treinta minutos se emitió una única credencial
de cinco segundos a la cuenta rival mediante instrumentación temporal del contenedor
demo; se restauró el módulo original y su duración habitual inmediatamente tras
emitirla. Al vencer se observó el 401 real, login y recuperación del código, y la
sala siguió con una plaza hasta la confirmación explícita. No se modificó el módulo
de autenticación del repositorio ni la base habitual. Las salas ficticias 6/7
se usaron para cancelación/caducidad HTTP; no se alteraron salas ajenas.

Comprobaciones de esta revisión: 42 pruebas frontend relacionadas (selector,
errores, participantes, reintentos, borrador y retorno seguro), nueve backend
de salas, tipos, lint y build. Se reutiliza la concurrencia anterior: no cambian
sus bloqueos, reglas ni esquema y no se repitió toda la batería del motor.
Se conservan límites de revisión física, lectores de pantalla y movimiento reducido
anteriores. La revisión autónoma no equivale a aprobación visual del usuario.

## Aprobación visual del usuario — 6 de noviembre de 2026

El usuario revisó personalmente la demo y aprobó el modo en línea, el selector
visual, la sala de jugadores, las correcciones de autenticación y la distribución
adaptable local/en línea. Autorizó el commit del conjunto pendiente. Esta revisión
se atribuye al usuario y se añade a la revisión autónoma descrita anteriormente;
se conserva también la atribución de su aprobación previa del pulido local.

Para preparar el commit solo se actualizó documentación: se reutilizaron las
comprobaciones vigentes descritas en este documento y en la revisión de
distribución, sin repetir pruebas ni modificar código o bases de datos. Se
mantienen las limitaciones de dos dispositivos físicos, lector de pantalla,
movimiento reducido nativo, zoom nativo al 200 % y teclado virtual móvil real;
la aprobación visual no se presenta como verificación técnica de esos casos.
