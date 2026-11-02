# Frontend de BioGaMed

Aplicación Next.js con React, TypeScript y Tailwind CSS.

## Ejecución local

Desde `frontend/`, con Node.js y las dependencias instaladas:

```sh
npm ci
npm run dev
```

Abre `http://localhost:3000`. El backend debe estar disponible en
`http://localhost:8000`. Para utilizar Docker, consulta `docker-compose.yml`
en la raíz del repositorio.
`NEXT_PUBLIC_API_BASE_URL` permite apuntar el cliente a otro backend en un
entorno de pruebas; sin ella se usa `http://localhost:8000`.

## Comprobaciones

```sh
npm run lint
npx next typegen
npx tsc --noEmit
```

## Panel del estudiante

`/dashboard` comprueba el token con `/auth/me`, carga temáticas desde `/topics/`
y muestra hasta cinco partidas recientes desde `/game/history`. Sin token
redirige al login; una sesión rechazada utiliza el interceptor compartido.
El cierre de sesión elimina la clave `token` sin borrar otros datos del navegador.

## Primera pantalla de gestión de contenidos

El panel muestra «Gestión de contenidos» solo si `/auth/me` devuelve el rol
`teacher` o `admin`. `/gestion/asignaturas` funciona por acceso directo y
recarga: vuelve a comprobar sesión y rol antes de consultar `GET /subjects`.
Un estudiante ve un aviso de acceso no permitido. El backend autoriza también
cada operación; ocultar el enlace no sustituye esa comprobación.

La lista muestra nombre y descripción disponible, ordenada por ID desde el
servidor. `?page=N` conserva la página. Se solicitan 13 elementos mediante
`skip` y `limit` para mostrar 12 y saber si existe «Siguiente», ya que la API
no devuelve un total. El formulario envía `POST /subjects` con nombre
obligatorio de hasta 255 caracteres y descripción opcional. Bloquea envíos
repetidos; ante un error conserva los campos. Tras crear, confirma la entidad
devuelta por el servidor sin asumir que corresponde a la página visible.
La pantalla contempla carga, lista vacía, reintento, sesión caducada y pérdida
de permisos. Todavía no ofrece edición ni eliminación.

Validación visual: «Pruebas UI» no vio el acceso y recibió «Acceso no permitido»
al abrir la ruta directamente. En una pila aislada con PostgreSQL desechable,
una cuenta docente ficticia comprobó acceso, recarga, lista vacía, validación
de nombre, creación, confirmación, paginación, foco y diseño móvil. Una doble
pulsación creó una sola fila. Un fallo de red simulado deteniendo solo el
backend temporal conservó los campos y permitió reintentar. No se midió una
concurrencia de solicitudes con respuestas deliberadamente retrasadas ni se
comprobó visualmente una sesión docente caducada. Las pruebas automatizadas
de cliente y backend cubren los contratos y permisos; la pila se retiró.

### Consulta de partidas anteriores

Las partidas completadas de «Tus últimas partidas» ofrecen el enlace «Ver
resultado» a `/partidas/{id}`. La ruta admite acceso directo y recarga, consulta
`GET /game/history/{id}` con el cliente autenticado y solo muestra partidas del
usuario actual. Presenta modalidad, temática, fecha de inicio, puntuación y el
contexto de categoría y dificultad guardado al iniciar, si existe. Las
respuestas, correcciones y soluciones proceden de los datos conservados en el
historial; no se recalculan a partir del banco actual. La misma presentación de
correcciones se utiliza al finalizar una partida de Trivial.

«Ver todo el historial» abre `/historial`, accesible también directamente.
Consulta `/game/history` con `skip` y `limit` para mostrar diez partidas por
página; `?page=N` conserva la página al recargar. El servidor devuelve una
lista ordenada, pero no indica total ni metadatos de paginación. Se solicita
un elemento adicional para habilitar «Siguiente» solo cuando existe, sin
mostrar un número total de páginas. La clasificación se toma del
`content_context` histórico; las partidas anteriores sin él indican que no
consta. La temática usa su nombre actual o su ID si no está disponible.

Las partidas antiguas sin `content_context` muestran que no consta esa
clasificación; si faltan respuestas detalladas, se indica cuántas se conservan
o que no hay corrección disponible. Las partidas sin finalizar se identifican
como tales y no ofrecen reanudación ni corrección. La pantalla contempla carga,
reintento tras fallo de consulta, sesión rechazada y partida no disponible.

La fecha disponible es la de **inicio**, no la de finalización. El nombre de
la temática se consulta en la lista actual de temáticas; si ya no se obtiene,
se muestra su ID. No es una copia histórica del nombre. En el navegador
integrado aislado se comprobó el enlace desde el panel, el acceso directo y
la recarga de una partida existente, sus diez correcciones, el contexto,
la navegación por teclado entre correcciones y la adaptación a escritorio y
móvil (390 px, sin desbordamiento horizontal). También se observó el mensaje
de una partida inexistente. **No se comprobaron en navegador** partidas
antiguas sin contexto o con respuestas incompletas, partidas sin finalizar,
errores de red ni sesión caducada; estos estados se trataron en el código y
las pruebas pertinentes.

El panel muestra primero Trivial y Pasapalabra. Al elegir un juego, consulta
`/topics/?mode=TRIVIAL` o `mode=PASAPALABRA` y muestra solo temáticas con
preguntas disponibles. Se puede volver a cambiar de juego; las respuestas
tardías de una selección anterior no sustituyen los temas del modo actual.
Las tarjetas de temática enlazan a `/game?topicId=…&mode=TRIVIAL` o `mode=PASAPALABRA`.
No se muestran números de preguntas por temática porque la respuesta actual
de temas no los incluye.

Las tarjetas de juegos usan ilustraciones SVG y una única acción para Trivial;
Pasapalabra indica «En preparación» sin abrir temáticas. La selección de
temáticas presenta los iconos transparentes copiados del prototipo para
Erlenmeyer, Jeringuilla, Linfocito y Macrófago. La correspondencia visual está
en `src/lib/topic-presentation.ts`; las temáticas nuevas o desconocidas usan
un SVG genérico y la lista disponible sigue procediendo de la API. Las tarjetas
se centran en filas de hasta tres en escritorio, dos en tamaños intermedios y
una en móvil. «Mis últimas partidas» es una sección plegable inicialmente
cerrada bajo los juegos; sus elementos son recientes, no el total histórico.

## Partidas de Trivial

`/game` valida los parámetros y comprueba la sesión. Antes de iniciar consulta
`GET /game/availability/{topicId}?mode=TRIVIAL` con el cliente autenticado.
Muestra los nombres de categoría recibidos, los niveles disponibles y el número
de preguntas de la selección (hasta diez). Si solo hay una categoría, la muestra
como contexto. «Sin filtrar dificultad» incluye todos los niveles y es distinta
de «Dificultad sin clasificar». «Todas las categorías» mantiene el acceso a las
preguntas sin categoría. Las respuestas tardías de una consulta anterior no
habilitan un inicio para otra temática. La carga y los errores impiden comenzar
hasta recibir una disponibilidad válida; se ofrece reintento de consulta.

Al pulsar «Comenzar partida», envía `POST /game/start/{topicId}` con
`mode=TRIVIAL` y los filtros elegidos (`category_id`, `difficulty` o
`difficulty_unknown=true`). Abrir la página o cambiar filtros no crea partidas.
El inicio bloquea el doble clic; si falla, conserva la selección para corregirla
o reintentar. Durante la partida y en el resultado se muestran temática,
categoría y dificultad según el `content_context` recibido, con etiquetas para
preguntas mixtas o sin clasificación.

Se puede avanzar y retroceder conservando las selecciones, y cambiarlas antes
de finalizar. Es necesario responder todas las preguntas. Al terminar se envía
una respuesta por pregunta a `POST /game/submit/{sessionId}`; la puntuación y
la corrección proceden del backend. El resultado muestra los aciertos, la
respuesta elegida y la correcta para cada pregunta.

El envío bloquea los controles para evitar duplicados. Si falla, conserva las
respuestas para reintentar. Si el backend ya había guardado la partida pero se
perdió la respuesta, un reintento recupera el resultado desde el historial.
Cada respuesta de Trivial envía `response_time_ms`: suma los intervalos en que
su pregunta está mostrada con la pestaña visible, incluidas las revisitas.
El reloj monotónico del cliente se detiene durante el envío y se reanuda tras
un fallo; la espera de red no cuenta. Es **tiempo de exposición medido por el
cliente**, no una medida garantizada de atención. Los registros antiguos con
`NULL` indican tiempo desconocido, no cero.
Recargar o abandonar la página pierde las selecciones no enviadas. Pasapalabra
muestra un aviso de preparación sin crear ninguna partida.

Validación manual en navegador integrado aislado (cuenta de estudiante de
pruebas): Linfocito, nivel 2 anunció diez preguntas y no creó la partida hasta
pulsar «Comenzar partida». Se completó una sola partida con cuatro aciertos;
el resultado, las diez correcciones y el contexto coincidieron con lo guardado,
y apareció en «Tus últimas partidas». Se comprobó el recorrido en escritorio y
móvil, la conservación de selecciones al navegar y cambiarlas, y que no hubo
desbordamiento horizontal en un viewport móvil de 390 px. También se observó
la preparación de una temática sin clasificación y un error de disponibilidad.
**Los errores de envío y la recuperación del resultado no se comprobaron en
navegador**; están cubiertos por pruebas del cliente.

## Sesiones rechazadas por el backend

El cliente compartido de Axios añade el token almacenado a las peticiones,
excepto al login y al registro. Si una petición con el token actual recibe
`401`, elimina ese token y redirige a `/login?session=expired`, donde se pide
iniciar sesión de nuevo. El mensaje indica que la sesión ha caducado o ya no
es válida: el backend usa `401` para ambos casos.

Un login incorrecto conserva su mensaje de credenciales incorrectas. Los
errores `403`, de servidor o de red no cierran la sesión. Una respuesta tardía
de un token anterior no elimina uno nuevo. Esta gestión ocurre al recibir un
`401`; no hay temporizador ni renovación automática del token.

Pruebas del interceptor (tras instalar las dependencias con `npm ci`):

```sh
node --test tests/session-expiry.test.mjs
```

## Historial de partidas

«Mis últimas partidas» enlaza con `/historial`, que consulta la API paginada
sin descargar todo el historial. La página se conserva en la URL y las partidas
completadas permiten revisar las respuestas guardadas en `/partidas/{id}`.
Las tarjetas compartidas muestran la temática, el contexto histórico disponible,
la fecha de inicio y el estado. En partidas nuevas completadas, el backend exige
una respuesta por pregunta: la barra y los errores se calculan con el número de
preguntas y los aciertos guardados. En partidas antiguas sin contexto o sin
finalizar se muestran solo los datos conocidos.

Se verificaron las tarjetas en escritorio (1280 px) y móvil (390 px), sin
desbordamiento horizontal, con foco de teclado visible. La cuenta de pruebas
solo tenía una página de resultados: la navegación entre páginas y los estados
de error, vacío y sesión caducada están cubiertos por pruebas o lectura del
código, pero no se comprobaron todos en navegador.

## Mi progreso

El panel enlaza con `/progreso`, que también admite acceso directo y recarga.
La pantalla consulta `GET /game/progress` con el cliente autenticado y muestra
partidas iniciadas, completadas y sin finalizar, en total y por modalidad.
Son recuentos de actividad, no de aciertos; Pasapalabra figura «En preparación».
Los ceros aparecen solo tras una respuesta correcta del servidor. Ante un error
se ofrece reintento y un `401` utiliza la redirección compartida al login.

Se comprobó en navegador aislado con «Pruebas UI» el enlace del panel y la
presentación a 1280 y 390 px, sin desbordamiento horizontal y con foco visible.
Los recuentos visibles (5 iniciadas, 5 completadas, 0 sin finalizar) coincidieron
con una lectura del servicio backend para esa cuenta. La petición autenticada
del cliente y la gestión compartida de `401` tienen pruebas automatizadas;
la autenticación, el aislamiento entre usuarios, los ceros sin actividad y más
de una página de partidas se probaron en el backend. Los estados de error,
reintento, sesión caducada y usuario sin partidas no se verificaron en navegador.

«Mis mejores marcas» utiliza directamente los grupos `best_marks` del servidor.
Cada tarjeta compara partidas de igual modalidad, temática, categoría y nivel
históricos, y número de preguntas; muestra la mejor puntuación, fecha de inicio,
partidas válidas del grupo, empates y enlace a la partida elegida. El backend
desempata por fecha e ID, nunca por tiempo. Las partidas antiguas sin contexto,
mixtas o con registros incoherentes siguen en actividad aunque no tengan marca.
La temática muestra su nombre actual; la categoría usa el histórico cuando
existe e indica si su nombre procede del catálogo actual.

Con «Pruebas UI» se comprobó una marca real en escritorio y móvil y se contrastó
con una lectura del servicio backend. Los casos de lista vacía con actividad,
empate, singular/plural y nombres históricos o actuales se probaron mediante
renderizado estático de los componentes (31 pruebas frontend aprobadas en total).
No se comprobaron visualmente en navegador porque la cuenta no tenía esos
casos. Tipos y lint pasaron.

«Evolución de resultados» permite elegir un grupo comparable y representa sus
resultados en orden de inicio. Con dos o más partidas muestra puntos conectados
y una lista accesible; con una indica que hacen falta más resultados. La lista
vacía tiene un aviso propio. No une grupos diferentes ni interpreta las
puntuaciones como prueba de mejora del aprendizaje. Los puntos proceden del
backend, sin recalcular ni paginar en el navegador.
