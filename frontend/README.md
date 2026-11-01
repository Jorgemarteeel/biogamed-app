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

### Consulta de partidas anteriores

Las partidas completadas de «Tus últimas partidas» ofrecen el enlace «Ver
resultado» a `/partidas/{id}`. La ruta admite acceso directo y recarga, consulta
`GET /game/history/{id}` con el cliente autenticado y solo muestra partidas del
usuario actual. Presenta modalidad, temática, fecha de inicio, puntuación y el
contexto de categoría y dificultad guardado al iniciar, si existe. Las
respuestas, correcciones y soluciones proceden de los datos conservados en el
historial; no se recalculan a partir del banco actual. La misma presentación de
correcciones se utiliza al finalizar una partida de Trivial.

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
