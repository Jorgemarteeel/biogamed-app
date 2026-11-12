> Instalación nueva y primer administrador: consulta [la guía de instalación de la raíz](../README.md). Los apartados históricos siguientes registran entregas anteriores y no sustituyen esa guía.

# Frontend de BioGaMed

Aplicación Next.js con React, TypeScript y Tailwind CSS.

## Pasapalabra local jugable

Disponible preparación, dos roscos numerados, respuesta/paso, relojes de servidor,
recuperación y resultado. [Detalles y verificación](docs/pasapalabra-local.md).
Actualización del 5 de noviembre de 2026: sustituye los avisos históricos siguientes
que describían la interfaz como «En preparación». Las salas en línea siguen pendientes.

## Historial de Pasapalabra compartido

El backend incorpora el motor y la API local; la tarjeta sigue «En preparación»
y no existe todavía interfaz jugable ni salas. El historial acepta los campos
aditivos de las sesiones compartidas: muestra aciertos, fallos y pendientes
por separado y distingue en curso y finalización por abandono, conservando
el comportamiento de Trivial y partidas antiguas. No interpreta pendientes
como errores. Contratos: [API local](../backend/docs/pasapalabra-local.md).

## Estado de preguntas del banco docente

El listado por categoría muestra «Activa» o «Retirada» y permite retirar o
reactivar. Antes de retirar, una confirmación en la tarjeta explica que se
excluirá de partidas nuevas y se conservarán las anteriores, sus correcciones
y el historial. Se puede cancelar con el botón o Escape; el foco vuelve al
control de origen. Los controles usan botones y selectores nativos, etiquetas
accesibles, avisos de estado/error y los estilos adaptables existentes.
El envío bloquea acciones simultáneas; ante un fallo se permite repetir la
petición explícita de forma segura o actualizar para comprobar el estado.

El filtro «Estado» permite activas, retiradas y todas (valor predeterminado).
`state=active|retired|all`, modalidad, dificultad y página se conservan en la
URL; aplicar filtros vuelve a la primera página. Guardar o cancelar una
edición conserva esta selección, y editar una retirada no la reactiva.
Una pregunta creada es activa: si el filtro de retiradas la excluye, se avisa.
Tras cambiar estado se vuelve a consultar el listado para rellenar la página
y recalcular «Siguiente». Si desaparece la última coincidencia de una página
posterior, se vuelve a la primera con los mismos filtros y un aviso
(`adjusted=1`). Las retiradas siguen accesibles para consulta y edición.

Verificación del 4 de noviembre de 2026: tipos (`tsc --noEmit`), lint y
20 pruebas frontend pertinentes aprobados, incluyendo confirmación,
cancelación, Escape, foco programático, doble envío, error recuperable,
reactivación, filtros de URL, paginación y edición. Se ejecutaron con las
dependencias de la demo aislada:

```sh
node --test tests/question-retirement.test.mjs tests/category-edit-navigation.test.mjs tests/question-creation.test.mjs tests/content-navigation.test.mjs tests/question-exposure.test.mjs
```

El usuario revisó personalmente la interfaz anterior de consulta, creación y
edición docente y la considera correcta; esta comprobación se registra como
**revisión del usuario** y no se repitió. Para los nuevos controles de retirada,
el navegador integrado respondió `The browser access host is unavailable`.
Por ello quedan pendientes la revisión visual, el recorrido real de teclado
y la comprobación móvil de esta funcionalidad. Las pruebas de componentes
y HTTP no se presentan como revisión visual. Demo disponible en
`localhost:13004`, con API `localhost:18004`; sin Opera GX ni cuentas personales.

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

El menú del usuario muestra «Gestión de contenidos», separado de la navegación
personal, solo si `/auth/me` devuelve el rol `teacher` o `admin`. Este acceso
compartido está disponible en las cabeceras autenticadas; el panel ya no muestra
una tarjeta docente. `/gestion/asignaturas` funciona por acceso directo y
recarga: vuelve a comprobar sesión y rol antes de consultar `GET /subjects`.
Un estudiante ve un aviso de acceso no permitido. El backend autoriza también
cada operación; ocultar el enlace no sustituye esa comprobación.
En la demostración aislada se comprobó el enlace docente, la separación visual,
la apertura con teclado, el cierre con Escape y al pulsar fuera, y el menú móvil
sin desbordamiento a 390 px. La prueba automatizada de roles comprueba que
`student` no recibe el acceso; el usuario confirmó además el resultado en su
revisión manual. El agente no pudo repetir esa comprobación visual con la
cuenta estudiante porque la pestaña autenticada no estaba disponible para
control.

La lista muestra nombre y descripción disponible, ordenada por ID desde el
servidor. `?page=N` conserva la página. Se solicitan 13 elementos mediante
`skip` y `limit` para mostrar 12 y saber si existe «Siguiente», ya que la API
no devuelve un total. El formulario envía `POST /subjects` con nombre
obligatorio de hasta 255 caracteres y descripción opcional. Bloquea envíos
repetidos; ante un error conserva los campos. Tras crear, confirma la entidad
devuelta por el servidor sin asumir que corresponde a la página visible.
La pantalla contempla carga, lista vacía, reintento, sesión caducada y pérdida
de permisos. Todavía no ofrece edición ni eliminación.

Cada asignatura ofrece «Ver bloques», también tras crearla. La ruta
`/gestion/asignaturas/{id}` consulta el detalle y los bloques de esa asignatura,
admite recarga y `?page=N`, y permite crear bloques con el mismo tratamiento de
permisos, validación, errores y confirmación. Solicita un elemento adicional
para saber si existe otra página sin inventar un total. Si el listado precede
a la creación, ofrece actualizarlo sin ocultar la confirmación.

Cada bloque ofrece «Ver categorías», también en su confirmación de creación.
`/gestion/asignaturas/{id}/bloques/{blockId}` muestra asignatura y bloque,
pagina las categorías de ese bloque y permite crear una. Reutiliza los estados
de sesión, permisos, vacío, error y confirmación de la gestión anterior. Las
categorías aún sin bloque no se muestran como pertenecientes a ninguno.
La sección «Vincular categoría existente» consulta únicamente las categorías
sin bloque, muestra sus IDs para distinguir nombres iguales y pide confirmar
el bloque y la asignatura. Tras vincular, actualiza ambos listados. Un conflicto
con otra vinculación muestra el error y permite elegir de nuevo.
La vinculación se revisó en navegador aislado con categorías ficticias: paginación,
confirmación persistente, actualización de ambos listados y conflicto simulado
entre bloques. No se forzaron caducidad de sesión ni error de red en navegador;
la repetición al mismo destino y la concurrencia se comprobaron en pruebas de
API y PostgreSQL temporal, respectivamente.
La ruta de categorías se validó en una pila temporal con docente y contenidos
ficticios: acceso desde bloques, recarga directa, vacío, nombre en blanco,
creación, paginación, separación entre bloques, referencia incompatible,
vista de escritorio y móvil sin desbordamiento, y foco de teclado visible.
No se forzaron errores de red ni caducidad de sesión en el navegador; esos
estados conservan el tratamiento compartido con la gestión anterior.

La gestión usa una ruta de navegación común desde Panel hasta asignatura y
bloque, con nombres obtenidos de la API. Los formularios de asignatura, bloque
y categoría empiezan plegados; el botón comunica su estado y lleva el foco al
primer campo al abrir, y de vuelta al botón al cerrar. Las confirmaciones se
mantienen visibles fuera del panel plegable.
En la demostración aislada se comprobaron los tres recorridos, apertura y
cierre, foco, una creación de categoría ficticia con confirmación persistente,
escritorio y móvil (390 px) sin desbordamiento. La pérdida de permisos, errores
de red y una pantalla táctil física no se probaron visualmente en esta revisión.
El usuario revisó después personalmente las mejoras y confirmó su conformidad.
Cada categoría del bloque, incluida la confirmación de una recién creada,
ofrece «Ver preguntas». La ruta
`/gestion/asignaturas/{id}/bloques/{blockId}/categorias/{categoryId}` admite
acceso directo y recarga. Conserva la ruta de navegación y permite filtrar por
modalidad y por dificultad sin filtrar (incluidas las preguntas sin clasificar),
uno de los niveles 1–4 o solo dificultad sin clasificar. «Aplicar filtros»
vuelve a la primera página; `mode`, `level` y
`page` permanecen en la URL. Se solicitan 13 preguntas al servidor para
mostrar 12 y detectar la página siguiente, sin inventar un total.
La pantalla muestra las soluciones solo tras verificar la sesión docente;
el backend vuelve a autorizar cada lectura. Identifica Topic como temática
heredada de juego, distinta de la categoría académica. Incluye vacío, filtros
sin resultados, error con reintento, acceso no permitido y ruta inexistente.
Ofrece creación y edición de preguntas, descritas más abajo, sin retirada ni
eliminación.

Las pruebas automatizadas comprueban el cliente autenticado, los parámetros
enviados y la navegación jerárquica; las pruebas de backend cubren permisos,
relaciones y filtros. En el navegador aislado con docente ficticio se comprobó
el enlace desde la categoría, acceso directo y recarga, segunda página, filtros,
ausencia de resultados, categoría vacía y soluciones de ambas modalidades.
La pantalla móvil a 390 px no desbordó horizontalmente; el foco recorrió los
dos selectores y el botón con indicador visible. No se forzaron errores de red,
caducidad de sesión ni cambios de rol durante esta revisión visual.
En una pila temporal con PostgreSQL desechable se comprobaron acceso desde
asignaturas, ruta directa y recarga, vacío, validación, creación, doble
pulsación sin duplicado, separación entre asignaturas, segunda página, ruta
inexistente y adaptación móvil con controles de teclado. No se simularon en
navegador una sesión caducada, pérdida de permisos ni un fallo de red al crear
bloques; los contratos y permisos se cubren con pruebas aisladas.

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
consta. La temática usa el nombre conservado al inicio cuando existe; en
partidas antiguas se indica que el nombre procede del catálogo actual, o su ID
si no está disponible.

Las partidas antiguas sin `content_context` muestran que no consta esa
clasificación; si faltan respuestas detalladas, se indica cuántas se conservan
o que no hay corrección disponible. Las partidas sin finalizar se identifican
como tales y no ofrecen reanudación ni corrección. La pantalla contempla carga,
reintento tras fallo de consulta, sesión rechazada y partida no disponible.

La fecha disponible es la de **inicio**, no la de finalización. Solo se usa el
catálogo actual como alternativa explícita si no se conservó el nombre de la
temática al inicio. En una verificación anterior en el navegador
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

## Creación docente desde una categoría

La consulta de preguntas incluye «Crear pregunta», un formulario inicialmente
plegado con etiquetas y controles nativos. Permite elegir temática de juego
desde la API (todas las páginas, sin filtrar por modalidad), modalidad,
enunciado y dificultad opcional 1–4. Trivial muestra cuatro opciones y la
selección explícita de la correcta; Pasapalabra muestra letra, solución y
alternativas, una por línea. Solo se envían los campos de la modalidad activa;
la categoría se fija en la ruta, nunca en el cuerpo.

El envío bloquea controles y envíos simultáneos, conserva los campos ante
errores y muestra la confirmación con el ID y temática recibidos del backend.
Tras el éxito, «Crear otra pregunta» habilita un formulario nuevo. «Actualizar
listado» vuelve a consultar la página con sus filtros y paginación actuales:
no cambia la selección. La confirmación explica si la pregunta queda excluida
por esos filtros o puede aparecer en una página posterior por el orden por ID.
Cerrar y abrir el panel conserva los campos mientras se mantiene la pantalla;
no se guarda un borrador al recargar o salir.

Validación del 3 de noviembre de 2026: tipos (`npx.cmd tsc --noEmit`), lint
(`npm.cmd run lint`) y las 54 pruebas frontend anteriores aprobadas; las dos
pruebas nuevas de `node --test tests/question-creation.test.mjs` también
aprobaron. Cubren peticiones autenticadas, paginación de temáticas, doble envío,
campos conservados ante un error del servidor, envío de campos según modalidad,
confirmación con ID y aviso de exclusión por filtros. Estas pruebas del
componente simulan hooks y eventos; no sustituyen una revisión en navegador.

Se actualizó únicamente la demo docente aislada en `localhost:13004` y la
ruta de categoría respondió HTTP 200. La API de esa demo creó las preguntas
ficticias 16 y 17 y verificó su consulta, sin crear partidas. **No se pudo
iniciar sesión ni revisar visualmente formulario, confirmación, listado,
teclado o móvil en el navegador integrado**: el servicio devolvió
`The browser access host is unavailable`, confirmado por el inventario de
navegadores. No se utilizó Opera GX ni ninguna cuenta personal. Esas
comprobaciones manuales quedan pendientes; la demo sigue disponible.

El bloqueo de doble envío es del cliente, no una clave de idempotencia del
servidor. Si se pierde la respuesta tras persistir, un reintento podría crear
otra pregunta: el error recomienda actualizar el listado antes de reintentar.
La edición utiliza el mismo formulario, descrito a continuación. No hay
retirada ni eliminación; las partidas antiguas no se reconstruyen.

## Edición docente de preguntas y guía de partidas antiguas

Cada pregunta del listado de categoría ofrece «Editar». El formulario compartido
con creación se precarga y permite cambiar enunciado, temática de juego obtenida
de la API, dificultad y los campos de solución propios de Trivial o Pasapalabra.
La modalidad permanece visible y bloqueada; no hay selector de categoría.
El backend verifica ambas restricciones. Mientras se edita se ocultan el
listado y sus controles; la URL, filtros y página se conservan.

«Guardar cambios» bloquea controles y dobles envíos; los errores mantienen el
borrador. La confirmación muestra el ID guardado y recibe el foco. Si la nueva
dificultad deja la pregunta fuera de los filtros, se explica sin cambiarlos.
«Volver al listado» consulta la misma página y filtros; el foco vuelve a
«Editar» o al título del listado si la pregunta ya no aparece. «Cancelar» pide
confirmar el descarte o seguir editando, y no envía modificaciones al servidor.
El aviso al regresar confirma la cancelación. Si un envío falló sin poder
confirmar si persistió, la cancelación lo advierte y vuelve a consultar el banco;
no afirma que el servidor no guardó cambios. No se conserva el borrador al salir
de la pantalla o recargar, ni hay detección de edición concurrente entre docentes.

El cliente reconoce exclusivamente el `409` cuyo `detail.code` es
`LEGACY_SESSION_NO_SNAPSHOT`. La pantalla activa sustituye el envío por el aviso:
«Esta partida se inició con una versión anterior y ya no puede continuarse.
Puedes empezar una nueva». El detalle de historial usa el mismo aviso solo
cuando la API devuelve ese `continuation_error_code` para una partida abierta.
El aviso recibe el foco y ofrece «Preparar otra partida» y «Ver historial».
La preparación usa navegación completa para reiniciar el estado local incluso
si ya se estaba en esa URL; no inicia automáticamente una sesión. Otros `409`
mantienen su manejo de conflicto y la recuperación del resultado completado.
No se elimina ni completa la partida antigua y su contenido no se reconstruye.

Verificación de esta tarea, 3 de noviembre de 2026: tipos y lint aprobados;
**37 pruebas frontend pertinentes aprobadas**. Incluyen formulario compartido,
precarga de ambas modalidades, errores, doble envío, guardado, confirmación de
cancelación y envío incierto, cliente autenticado, mantenimiento de filtros y
página al guardar/cancelar, foco alternativo simulado, mensaje/acciones en partida
activa e historial, código específico frente a otros conflictos y recuperación
de resultados ya guardados. Son pruebas automatizadas con hooks/servicios
simulados donde corresponde; no equivalen a revisión visual de teclado o foco.

La demo aislada en `localhost:13004` se mantuvo disponible. Se verificaron por
HTTP la creación y edición real de preguntas 20 y 21, las partidas antes y
después del cambio (3–6), su corrección e historial estable, y el código de la
partida antigua ficticia 7 sin completarla. La ruta docente respondió HTTP 200.
Se reutilizaron credenciales locales de la demo sin exponerlas; no se escribió
en la base habitual.

**Revisión visual pendiente:** el navegador integrado volvió a devolver
`The browser access host is unavailable`. No se pudo iniciar sesión en él.
Quedan sin comprobar visualmente creación de Trivial y Pasapalabra, sus
validaciones y confirmaciones; edición de ambas modalidades, errores, guardado,
cancelación y retorno con filtros; el aviso de la partida antigua y sus enlaces;
y los recorridos de teclado, foco real y adaptación móvil de esos flujos.
No se usó Opera GX ni ninguna cuenta personal. Las comprobaciones HTTP anteriores
no se presentan como revisión visual.

## Contenido conservado de las partidas

Las partidas nuevas reciben las preguntas públicas proyectadas desde la copia
privada que guarda el backend al inicio. Trivial presenta y revisa ese mismo
enunciado y opciones; la solución de la corrección procede de la copia del
servidor. El historial utiliza sus registros guardados, sin consultar el banco
actual. El nombre de temática conservado en `content_context` tiene prioridad
sobre el catálogo en partida, tarjetas de historial y detalle. Las marcas usan
el nombre guardado en la partida ganadora; cuando falta, indican su procedencia
del catálogo actual. No cambian la agrupación, puntuación ni reglas de juego.

El detalle distingue partidas con contenido conservado al inicio de partidas
antiguas mediante `question_content_source`. Para las antiguas completadas se
aclara que sus registros corresponden a la corrección y que no hay una versión
original verificable. Para las antiguas abiertas sin copia se pide empezar otra
partida: la API rechaza su corrección con `409` y el código específico descrito
arriba. Datos ausentes siguen ausentes. No se ha incorporado reanudación ni
eliminación; la edición del banco reutiliza estas copias. Pasapalabra continúa
sin interfaz jugable; su protección se comprueba mediante la API implementada.

La copia con soluciones nunca llega al navegador: el inicio mantiene su
contrato público, y la corrección solo aparece tras enviar todas las respuestas.
El detalle de partidas sin finalizar no incluye registros de corrección. El
resultado y la revisión completada conservan el momento de exposición ya
permitido por el motor.

Verificación del 3 de noviembre de 2026: tipos y lint aprobados; **40 pruebas
frontend pertinentes** aprobadas entre revisión, resumen, presentación de
marcas, cliente de partidas y compatibilidad de sesiones. Incluyen renderizado
del historial y tarjetas con nombres originales frente a un catálogo cambiado,
contenido de respuestas guardado y avisos de compatibilidad antigua. Son pruebas
automatizadas, con servicios/hooks simulados donde corresponde, no una revisión
visual. No se repitieron las pruebas de creación ajenas a este cambio.

La revisión visual pendiente de `b45b8d7` (formulario Trivial y Pasapalabra,
validación, confirmación, teclado y móvil) continúa pendiente: al intentar abrir
`localhost:13004`, el navegador integrado devolvió
`The browser access host is unavailable`. No se usó Opera GX ni ninguna cuenta
personal. Se reutilizaron las credenciales locales solo desde el backend de la
demo para comprobar HTTP, sin exponerlas ni guardarlas en Git. Se verificó su
base y volumen separados antes de escribir; las preguntas ficticias 18 y 19
permitieron completar las partidas 1 y 2 tras modificar sus originales, con
historial estable y 1/1 en ambas. La página docente respondió HTTP 200. La demo
sigue disponible y la base habitual quedó intacta.

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
La temática usa el nombre conservado en la partida ganadora cuando existe;
temática y categoría indican si su nombre procede del catálogo actual.

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

La cabecera autenticada comparte el menú del nombre obtenido de `/auth/me`
(`Mi cuenta` si falta): abre «Mi historial» y «Mi progreso», se cierra con
Escape o al pulsar fuera y abrevia visualmente nombres largos en móvil.
La gráfica indica aciertos de 0 al total, anota cada puntuación y numera las
partidas de acuerdo con la lista. Para muchos resultados, el desplazamiento
queda dentro de la gráfica y conserva todos los puntos. En navegador aislado
se comprobaron el menú, foco, enlaces y cuatro resultados reales en escritorio
y móvil; quince puntos se verificaron mediante prueba de presentación, no con
datos reales en navegador. No se probó un dispositivo táctil físico.
