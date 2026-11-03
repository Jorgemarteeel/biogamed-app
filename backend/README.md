# Base de datos y banco de preguntas

## Organización académica de contenidos

`Subject` (asignatura) contiene bloques `ContentBlock`; cada bloque puede
contener categorías `Category`. Una categoría puede quedar temporalmente sin
bloque hasta validar su ubicación académica. Cada pregunta puede señalar una
categoría mediante `category_id`; las existentes mantienen `NULL` y conservan
su `topic_id`, su dificultad y sus identificadores.

`Topic` sigue siendo la agrupación heredada que utilizan la API, el importador
y los juegos. No representa todavía un nivel académico fijo: sus nombres
actuales pueden describir materias o categorías del prototipo. Esta estructura
no clasifica preguntas ni crea asignaturas, bloques o categorías automáticamente.
Las claves foráneas impiden borrar un elemento académico referenciado; no hay
borrado en cascada de preguntas o actividad.

### Consulta y creación de asignaturas

`GET /subjects?skip=0&limit=100` devuelve una lista ordenada por ID ascendente.
`skip` admite desde 0 y `limit` de 1 a 100; la lista vacía se devuelve como `[]`.
`POST /subjects` crea una asignatura y devuelve `201` con el ID generado:

```json
{"name": "Bioinformática", "description": "Fundamentos de la asignatura"}
```

La respuesta contiene `id`, `name` y `description`; esta última puede ser
`null` y omitirse al crear. El nombre es obligatorio, se recortan sus espacios
exteriores y debe tener entre 1 y 255 caracteres después del recorte. La
descripción utiliza el campo de texto del modelo, sin límite específico. No se
admiten campos adicionales como rol, propietario o permisos; no hay regla de
unicidad de nombre.

Ambas rutas requieren token y el rol **actual** `teacher` o `admin` en la base
de datos: sin autenticación responden `401`, y para `student`, `403`. No hay
todavía interfaz de gestión, edición, retirada ni eliminación de asignaturas.
La conexión usa `DATABASE_URL` si se configura; en el entorno local conserva
el valor existente por defecto. `BIOGAMED_CORS_ORIGIN` permite añadir un origen
local adicional para una instancia de pruebas separada.

Las partidas nuevas conservan una copia privada del contenido al inicio,
descrita en «Conservación del contenido de una partida». La edición docente
desde una categoría conserva esas copias; no hay retirada ni eliminación.
Las partidas antiguas sin esa copia no
pueden reconstruirse; las claves foráneas de preguntas e historial siguen
protegiendo sus referencias frente al borrado físico.

### Bloques dentro de una asignatura

`GET /subjects/{id}` consulta nombre y descripción de una asignatura.
`GET /subjects/{id}/blocks?skip=0&limit=100` lista sus bloques por ID ascendente,
con los mismos límites de paginación que asignaturas. `POST /subjects/{id}/blocks`
crea uno y devuelve `201`, por ejemplo:

```json
{"name": "Genómica", "description": "Conceptos básicos"}
```

El `subject_id` se toma de la ruta y no puede enviarse en el cuerpo. Nombre
recortado de 1 a 255 caracteres; descripción opcional sin límite específico
en el modelo. Se rechazan campos adicionales. Las tres rutas requieren rol
actual `teacher` o `admin`; una asignatura inexistente devuelve `404`.
No se impone unicidad ni se modifican preguntas o juegos.

### Categorías de un bloque

`GET /subjects/{subject_id}/blocks/{block_id}` devuelve el bloque y su
asignatura. `GET /subjects/{subject_id}/blocks/{block_id}/categories?skip=0&limit=100`
lista sus categorías por ID; `POST` a la misma ruta crea una categoría con
`{"name":"Inmunología","description":"Conceptos"}`. El ID de bloque se toma
de la ruta; el cuerpo no admite `block_id` ni otros campos adicionales. Nombre
recortado de 1 a 255 caracteres y descripción opcional. Requieren rol actual
`teacher` o `admin`; bloque inexistente o ajeno a la asignatura devuelve `404`.
Las categorías existentes sin bloque (`block_id=NULL`) permanecen intactas,
con sus IDs y preguntas, y no aparecen en la lista de un bloque concreto.

`GET /subjects/categories/unassigned?skip=0&limit=100` lista por ID solo esas
categorías sin bloque. `PUT /subjects/{subject_id}/blocks/{block_id}/categories/{category_id}`
con cuerpo `{}` vincula una categoría existente; exige docente o administrador
y comprueba el destino. Repetirlo en el mismo bloque devuelve la categoría sin
crear otra; si pertenece a otro bloque devuelve `409`. Se actualiza solo
`block_id`, mediante una condición atómica que impide que dos destinos distintos
ganen a la vez. No se trasladan ni desvinculan categorías.

### Consulta docente de preguntas por categoría

`GET /subjects/{subject_id}/blocks/{block_id}/categories/{category_id}`
devuelve el detalle de la categoría, su bloque y su asignatura. `GET` a la misma
ruta seguida de `/questions` lista las preguntas cuyo `category_id` coincide,
ordenadas por ID. Ambos endpoints exigen el rol actual `teacher` o `admin`
mediante la dependencia compartida; `401` indica falta de autenticación y
`403` un rol sin permiso. Una relación de IDs inexistente o incompatible
devuelve `404`; una categoría válida y vacía devuelve `[]`.

La lista admite `skip` desde 0 y `limit` de 1 a 100. `mode` puede ser
`TRIVIAL` o `PASAPALABRA`; omitirlo incluye ambas modalidades. Omitir
`difficulty` incluye todos los niveles, `difficulty=1` a `4` selecciona uno,
y `difficulty_unknown=true` selecciona preguntas sin dificultad. Combinar
un nivel con `difficulty_unknown=true` devuelve `422`, al igual que filtros
fuera de rango. Por ejemplo:

```text
GET /subjects/1/blocks/2/categories/3/questions?mode=TRIVIAL&difficulty=2&skip=0&limit=13
```

Cada pregunta incluye los campos del contrato docente existente —opciones y
posición correcta de Trivial, o letra, solución y respuestas alternativas de
Pasapalabra—, su `category_id` y su temática `topic` actual. Esta temática
heredada se muestra como contexto de juego y no sustituye la categoría
académica. Las soluciones no se exponen por esta ruta a estudiantes.
Las pruebas aisladas cubren roles, jerarquía completa, categoría vacía,
separación entre categorías, modalidades, dificultad y paginación. No se ha
modificado el esquema ni los endpoints de partida.

### Creación docente de preguntas por categoría

`POST /subjects/{subject_id}/blocks/{block_id}/categories/{category_id}/questions`
crea una pregunta y devuelve `201` con el contrato de consulta docente,
incluidos `id`, `category_id` y `topic`. Valida la jerarquía completa (`404`
si falta un elemento o no pertenece al padre indicado) y exige el rol actual
`teacher` o `admin` (`401` anónimo, `403` estudiante). El cuerpo no admite
`category_id`, ni siquiera si coincide con la ruta, ni campos adicionales.

Elige `topic_id` explícitamente de `GET /topics/`: es obligatorio, una
temática inexistente devuelve `404` y no se deduce de la categoría académica.
Ejemplo de cuerpo Trivial (el ID de temática debe proceder de esa consulta):

```json
{"text":"Pregunta ficticia","topic_id":1,"question_type":"TRIVIAL","options":["A","B","C","D"],"correct_option_index":1,"difficulty":2}
```

Pasapalabra utiliza `question_type: "PASAPALABRA"`, `letter`, `exact_word`
y, opcionalmente, `accepted_answers`. La solución debe empezar por la letra,
salvo si el enunciado empieza por `Contiene la letra `, cuando debe contenerla.
Se reutilizan la normalización y los límites de alternativas existentes.
Trivial requiere cuatro opciones de hasta 255 caracteres y posición correcta
0–3. Se rechazan enunciados/opciones en blanco, campos de solución de la otra
modalidad y dificultades distintas de `null` o entero estricto 1–4 (`422`).

La nueva operación reutiliza el esquema y el servicio de creación existente.
`POST /questions/` conserva su ruta y respuesta, crea sin categoría y admite
los mismos cuerpos válidos; comparte el rechazo reforzado de blancos y
combinaciones incoherentes. La creación no exige migración ni reclasifica datos;
la edición se describe a continuación. Las preguntas válidas amplían el banco que
consulta la selección de juego existente, sin cambios en esa selección.

Verificación del 3 de noviembre de 2026: suite backend completa, **175
aprobadas y 4 omitidas** (comprobaciones opcionales de migración PostgreSQL
sin su configuración de pruebas), con una advertencia de deprecación del
cliente Starlette/httpx. Las pruebas usan SQLite aislado y cubren permisos,
rol actual, jerarquía, temática inexistente, rechazo de `category_id`, ambas
modalidades, dificultad, persistencia, consulta y compatibilidad de creación.

En la demo `biogamed_docente_demo`, tras verificar su configuración, se
reutilizó la cuenta docente de prueba sin exponer credenciales. Se crearon
por HTTP las preguntas ficticias **16 (Trivial, nivel 2)** y **17
(Pasapalabra, sin dificultad)** en la categoría 5; se comprobaron `422`,
`201`, persistencia, consulta y exclusión por filtros. La base fue
`biogamed_demo`, con volumen propio; partidas antes/después: **0/0**.
No se escribió en la base habitual. La demo sigue disponible en
`http://localhost:13004`, con API en `http://localhost:18004`.

### Edición docente dentro de una categoría

`PUT /subjects/{subject_id}/blocks/{block_id}/categories/{category_id}/questions/{question_id}`
sustituye los campos editables de una pregunta y devuelve `200` con el mismo
contrato docente que la creación (`id`, `category_id` y `topic` incluidos).
Comprueba el rol **actual** `teacher` o `admin` mediante la dependencia
compartida: `401` anónimo y `403` estudiante. La jerarquía completa y la
pertenencia de la pregunta a esa categoría deben ser válidas (`404` en caso
contrario, incluso si la pregunta existe en otra categoría).

El cuerpo es completo, con las reglas de `QuestionCreate` reutilizadas:
enunciado no vacío, temática existente elegida explícitamente, dificultad
nullable o entero estricto 1–4 y campos coherentes con cada modalidad. Trivial
requiere cuatro opciones y posición correcta; Pasapalabra requiere letra y
solución, con las alternativas y normalización existentes. Se sincroniza
también `correct_answer`, igual que al crear. Omitir dificultad o alternativas
las deja sin valor; no es una operación de actualización parcial.

`question_type` es obligatorio y verifica la modalidad existente: cambiarla
devuelve `422`. No se admite `category_id` en el cuerpo, ni otros campos ajenos
como `id`, `subject_id` o `block_id`; la categoría y el ID se conservan.
Una temática inexistente devuelve `404`. Se bloquea la fila durante la edición
y se confirma una sola transacción; no se escribe en sesiones ni respuestas.
Las partidas ya iniciadas conservan su copia; las siguientes seleccionan el
banco actualizado sin cambios en selección o puntuación. No se incorporan
retirada, eliminación, traslado de categoría ni cambio de modalidad.

No se necesita migración nueva. Las copias de sesión requieren la migración
ya incorporada en `b7df60c`. No hay control de versión optimista del formulario:
si dos docentes guardan sobre la misma pregunta, prevalece el último guardado.
La interfaz evita envíos simultáneos, pero no impide ediciones concurrentes
desde navegadores distintos.

### Código específico de partida antigua incompatible

Solo una partida abierta sin copia al inicio devuelve `409` con:

```json
{"detail":{"code":"LEGACY_SESSION_NO_SNAPSHOT","message":"Esta partida se inició con una versión anterior y ya no puede continuarse. Puedes empezar una nueva"}}
```

El detalle de historial de esa partida añade
`continuation_error_code: "LEGACY_SESSION_NO_SNAPSHOT"`; para partidas con
copia o completadas devuelve `null`. No se deduce la incompatibilidad a partir
de cualquier `409`: una copia dañada, un modo inválido o un segundo envío
mantienen sus conflictos existentes. La recuperación de un resultado ya
guardado sigue funcionando para los conflictos ordinarios; el cliente no la
intenta ante este código específico.

No se reconstruye contenido, no se borra la sesión ni se marca completada.
Las antiguas completadas conservan la consulta de sus registros reales.
Las pantallas de envío de Trivial e historial ofrecen el mensaje indicado,
preparación de otra partida e historial. La preparación no crea una sesión
automáticamente. Pasapalabra mantiene su flujo backend y su aviso de interfaz
en preparación, sin añadir juego nuevo.

Verificación de esta tarea, 3 de noviembre de 2026: **101 pruebas backend
pertinentes aprobadas** en SQLite aislado (edición, creación con lógica
compartida, permisos y copias de partida). Un fallo inicial de la prueba de
jerarquía al leer un objeto ORM expirado se corrigió; se repitió solo ese caso.
Se comprobaron permisos actuales, jerarquía, separación entre categorías,
modalidad/categoría fijas, temática, dificultad estricta, validación de ambas
modalidades, alternativas, persistencia y sincronización de solución. Mediante
la operación real `PUT` se verificó que la partida previa conserva contenido,
contexto y corrección y que la posterior usa el banco editado. También se
comprobaron el código específico, la continuidad de registros completados y que
las copias dañadas no reciben ese código. Persiste la advertencia existente de
deprecación de Starlette/httpx. No se repitieron pruebas de migraciones porque
no cambió el esquema.

Antes de escribir se verificaron los puertos de la demo, su conexión a
`biogamed_demo` y el volumen exclusivo `biogamed_docente_demo_demo_data`.
Por HTTP se crearon y editaron las preguntas ficticias **20 (Trivial)** y
**21 (Pasapalabra)**: partidas previas **3 y 5**, posteriores **4 y 6**, todas
corregidas con 1/1 según su propia copia. La partida ficticia antigua **7**
devolvió el código específico y siguió abierta con cero puntos y sin registros.
Solo se usaron la demo y sus credenciales locales; no hubo escrituras ni
migraciones en la base habitual. La demostración sigue disponible en
`localhost:13004`, con API en `localhost:18004`.

## Dificultad opcional de las preguntas

`difficulty` es opcional en la creación y consulta del banco de preguntas,
tanto para Trivial como para Pasapalabra. Admite `null` o enteros del 1 al 4;
la API rechaza booleanos, decimales (incluido `2.0`) y cadenas como `"2"`.
Omitir el campo conserva la compatibilidad y guarda `NULL`: dificultad desconocida.

La escala representa los niveles de origen del prototipo. Su significado
académico está pendiente de validación; no equivale todavía a etiquetas como
«básico» o «avanzado». No se deduce dificultad de la modalidad ni del contenido.

La migración `f86ec0153249`, posterior a `e75dbf042138`, añade una columna
entera nullable, sin valor por defecto, y la restricción `ck_question_difficulty`
(`NULL` o rango 1–4). No rellena preguntas existentes ni modifica sus IDs,
contenidos, partidas o historial. El downgrade elimina solo esta restricción
y columna, perdiendo cualquier dificultad que se haya asignado después.

FastAPI valida `QuestionCreate` con Pydantic; el servicio existente pasa sus
campos a `Question`, SQLAlchemy persiste el valor y PostgreSQL comprueba el
rango. `QuestionResponse` lo devuelve en el banco autorizado. El entero estricto
se exige en la API; la restricción SQL protege el rango, no la sintaxis del JSON.
No cambia el contrato de preguntas del juego, la selección ni la puntuación.
`seed.py` no asigna dificultad: las nuevas preguntas importadas quedan en `NULL`
y repetir la carga no sustituye dificultades existentes.

La prueba `tests/test_difficulty_migration.py` requiere una URL explícita en
`TEST_DIFFICULTY_POSTGRES_URL`, de PostgreSQL con nombre de base que empiece por
`test_biogamed_`. Debe apuntar a una base **desechable**, nunca a la de desarrollo.
Sin esa variable, se omite. Crea y elimina únicamente su esquema temporal y
comprueba la conservación de datos, ausencia de valores por defecto y rango SQL.
Para ejecutarla dentro de ese entorno de pruebas:

```sh
python -m pytest -q tests/test_difficulty_migration.py
```

## Corrección de Pasapalabra

La comparación ignora mayúsculas, tildes de vocales, diéresis y espacios
sobrantes (también espacios repetidos dentro de una expresión). Conserva la
diferencia entre `n` y `ñ`, la puntuación y las palabras completas: no utiliza
coincidencias aproximadas ni deduce equivalencias médicas automáticamente.

Cada pregunta puede tener `accepted_answers`, una lista de hasta 30 respuestas
alternativas aprobadas por el docente, además de `exact_word`. Se pueden
especificar al crearla o sustituir mediante la API autenticada:

```text
PATCH /questions/{question_id}/accepted-answers
{"accepted_answers": ["glóbulo blanco"]}
```

Solo profesores y administradores pueden realizar esta operación. Una lista
vacía elimina las alternativas; la respuesta principal continúa siendo válida.
La alternativa puede empezar por otra letra, pues se acepta explícitamente
como equivalente para esa pregunta. El docente debe decidir si eso encaja con
la pista. No se generan sinónimos automáticamente para el banco existente.
El importador conserva las alternativas configuradas al repetir la carga.

Las alternativas no se envían al comenzar una partida. Se guarda una copia en
el historial junto con la respuesta original del jugador, sin modificar esta.
Las partidas ya corregidas no se recalculan. Para instalaciones existentes,
aplicar `alembic upgrade head` antes de arrancar el backend actualizado.

Desde la raíz del repositorio, con Docker disponible:

```sh
docker compose up -d db
docker compose run --rm --no-deps backend alembic upgrade head
docker compose run --rm --no-deps backend python seed.py
```

Alembic prepara la estructura. `seed.py` carga los HTML y TXT de `raw_data`
y sincroniza las preguntas importadas con el formato del motor actual:

- Trivial: enunciado separado, cuatro opciones e índice de la correcta.
- Pasapalabra: tipo `PASAPALABRA`, letra y palabra exacta. Se conserva el
  prefijo del enunciado para distinguir «Empieza» de «Contiene».

También se mantienen `correct_answer` y `game_letter` por compatibilidad.
El importador reconoce el texto del formato anterior y actualiza esas filas
sin cambiar sus identificadores. Repetirlo con las mismas fuentes no añade
duplicados; vuelve a sincronizar sus campos con los archivos originales.
Las preguntas ajenas a esas coincidencias no se modifican ni se eliminan.
Cambiar el enunciado de una fuente puede hacer que se considere otra pregunta.

La carga completa se confirma en una transacción; ante errores se revierte.
Esta adaptación de datos no necesita otra migración de estructura: las
columnas ya están incluidas en las migraciones existentes.

Pruebas (usan una base SQLite aislada, sin modificar PostgreSQL):

```sh
docker compose run --rm --no-deps backend python -m pytest -q
```

## Historial de partidas

### Filtros de contenido para juegos nuevos

`GET /game/availability/{topic_id}` (autenticado) devuelve `total_questions`
y las combinaciones `category_id`, `category_name`, `difficulty` y `count`
para una temática y modalidad. El nombre procede de `categories`; para
preguntas sin categoría, ID y nombre son `null`. No devuelve preguntas ni
soluciones. `POST /game/start/{topic_id}`
acepta los mismos parámetros y selecciona hasta diez preguntas distintas:

```text
GET  /game/availability/6?mode=TRIVIAL&category_id=3&difficulty=2
POST /game/start/6?mode=TRIVIAL&category_id=3&difficulty=2
```

`mode` admite `TRIVIAL` (por defecto) y `PASAPALABRA`; `category_id` es un ID
positivo opcional. Para dificultad se puede omitir el filtro, indicar
`difficulty=1` a `4` o elegir solo las preguntas sin nivel con
`difficulty_unknown=true`. Indicar simultáneamente un nivel y dificultad
desconocida devuelve `422`. Una combinación sin preguntas devuelve `409` al
iniciar; disponibilidad devuelve un total de cero. Omitir los filtros mantiene
el comportamiento anterior, incluidas preguntas sin clasificación.

Cada partida nueva guarda `content_context`: los filtros elegidos y una copia
del `category_id`, nombre de categoría y dificultad de cada pregunta al inicio.
La respuesta de inicio y las consultas de historial exponen ese contexto sin
soluciones. Reclasificar posteriormente el banco no cambia la interpretación
de la partida. La migración `c8e54b739a21` añade la columna JSON nullable;
las partidas anteriores conservan `NULL`.

El banco completo (`GET /questions/topic/{topic_id}`) incluye soluciones y
requiere un usuario con rol de profesor o administrador: sin credenciales
válidas responde `401` y para estudiantes responde `403`. Los jugadores
obtienen las preguntas sin soluciones al iniciar una partida y la corrección
al enviarla. El rol se comprueba contra el usuario actual de la base de datos.

`game_engine_sessions` es el único modelo de partidas. `User.game_sessions`
apunta a esas partidas y `GameSession.answer_logs` / `Question.answer_logs`
permiten consultar sus respuestas en la nueva tabla `answer_logs`.

Al corregir una partida nueva se utilizan sus preguntas conservadas al inicio,
sin volver a consultar el banco. Respuestas, puntuación y registros históricos
se guardan en la misma transacción. Cada registro conserva enunciado, opciones,
letra, respuesta enviada y corrección de esa copia. Los cambios posteriores
del banco no alteran la corrección ni el historial. La pareja partida/pregunta
es única.

### Conservación del contenido de una partida

La migración `d9f65a827bc1`, posterior a `c8e54b739a21`, añade
`game_engine_sessions.question_snapshot`, JSON nullable, sin valor por defecto
ni relleno de partidas anteriores. Aplicar `alembic upgrade head` en el destino
autorizado **antes** de arrancar el backend actualizado. En esta tarea se aplicó
solo a la demostración aislada, nunca a la base habitual.

Cada inicio nuevo guarda, en la misma transacción que la sesión, una copia
privada versionada (`version: 1`) de las preguntas seleccionadas: ID, temática,
modalidad, enunciado, opciones, posición correcta, letra, solución y alternativas.
Se conservan los campos usados por el motor, sin deducir respuestas ni copiar
columnas heredadas que no intervienen en la corrección. `content_context` mantiene
los filtros, categoría y dificultad ya conservados y añade el nombre de la
temática y los IDs/nombres de bloque y asignatura de cada pregunta cuando existen.
Una categoría sin bloque o una pregunta sin categoría conserva esos valores
ausentes; no se inventa jerarquía.

La presentación inicial se proyecta desde la copia hacia `QuestionForGame`.
Este contrato público continúa incluyendo únicamente ID, enunciado, opciones,
modalidad y letra. La columna privada no aparece en inicio, disponibilidad,
historial ni progreso; su carga es diferida para evitar leer soluciones en
los listados de sesiones y el cálculo de marcas. La corrección valida versión,
campos e identidad de la copia y reutiliza las reglas de selección, corrección,
normalización y puntuación existentes. No consulta la pregunta actual, aunque
se hayan cambiado su temática, modalidad, enunciado, clasificación o solución.
Las nuevas partidas posteriores siguen seleccionando el banco vigente.

El resultado revela la corrección solo tras el envío completo, igual que antes.
Los registros históricos se generan desde la copia de inicio y continúan siendo
la fuente de revisión. El detalle de una partida sin finalizar devuelve siempre
`answer_logs: []`, incluso ante un registro parcial inconsistente; las soluciones
no se anticipan por esa vía. Se mantienen autenticación, propiedad de la sesión,
bloqueo de segundo envío y rollback conjunto de puntuación e historial.

Compatibilidad explícita en el detalle de historial:

- `question_content_source: "session_start"`: partida con copia al inicio.
- `question_content_source: "legacy"`: partida anterior sin copia. Si está
  completada, se muestran solo los registros realmente guardados al corregir,
  que no garantizan el contenido que se vio al inicio. Si faltan registros o
  contexto, siguen ausentes; no se rellenan con datos actuales.
- Una partida antigua abierta sin copia devuelve `409` con el código específico
  `LEGACY_SESSION_NO_SNAPSHOT` al enviar respuestas,
  sin crear registros ni puntuación; requiere iniciar otra partida. No es
  posible asegurar qué contenido vio su jugador. Una copia dañada o de versión
  desconocida también devuelve `409`, sin recurrir al banco como alternativa.

El downgrade se bloquea si cualquier sesión conserva una copia no nula, para
evitar perder esta garantía. Requiere un plan explícito de archivo previo;
no elimina sesiones automáticamente. Las claves foráneas actuales siguen
vigentes: esto no habilita borrado físico, eliminación ni reanudación de
partidas. La edición del banco se ofrece por la ruta docente descrita arriba.
No protege frente a alteraciones directas de las
propias copias o registros por un administrador de la base de datos, ni congela
el código de las reglas para cambios futuros del motor.

Verificación del 3 de noviembre de 2026: **47 pruebas backend pertinentes**
aprobadas en SQLite aislado. Cubren ambas modalidades de API, cambios del banco
entre inicio y envío y después de corregir, sinónimos, puntuación, contexto,
revisión, nuevas selecciones, copia incompleta/dañada, compatibilidad antigua,
privacidad, propiedad y transacción. La interfaz jugable sigue siendo solo
Trivial; Pasapalabra se verifica en su flujo backend implementado.

Dos pruebas de migraciones aprobaron en PostgreSQL en la base desechable
`test_biogamed_session_snapshot`, con esquemas únicos y limpieza: upgrade,
conservación de todas las columnas previas, ausencia de relleno y valores por
defecto, correspondencia con el ORM, downgrade sin copias y bloqueo del
downgrade cuando las hay. Para repetir exclusivamente esta prueba se exige
`TEST_GAME_SNAPSHOT_POSTGRES_URL` apuntando explícitamente a PostgreSQL con
nombre de base `test_biogamed_*`; no hay fallback a la URL habitual:

```sh
python -m pytest -q tests/test_game_snapshot_migration.py
```

En la demo `biogamed_demo` se crearon por HTTP preguntas ficticias 18 y 19 y
partidas 1 (Trivial) y 2 (Pasapalabra). Solo se modificaron esas preguntas de
prueba tras iniciar; ambas obtuvieron 1/1 con la solución original, conservando
enunciado y contexto en el historial. La demo continúa en `localhost:13004`
(API `localhost:18004`). No se escribió en la base habitual. Sigue pendiente
la comprobación visual de creación de preguntas: el navegador integrado volvió
a informar `The browser access host is unavailable`; no se usó Opera GX ni
cuentas personales. Las pruebas emitieron la advertencia ya existente de
deprecación de Starlette/httpx.

La API autenticada permite consultar el historial del propio usuario:

- `GET /game/history?skip=0&limit=20`: partidas, de más reciente a más antigua.
- `GET /game/history/{session_id}`: detalle con `answer_logs`.
- `POST /game/submit/{session_id}` admite `response_time_ms` opcional en cada
  respuesta. Es un tiempo declarado por el cliente, no una medición del servidor.
  Si el cliente no lo envía, se guarda como `null`, sin inventar una duración.

No se ha añadido una pantalla de historial al frontend. Las partidas anteriores
a esta funcionalidad conservan sus puntuaciones y tienen el historial de
respuestas vacío; no es posible reconstruir respuestas que no se registraron.

La migración `d64caef31027` sustituye las tablas antiguas únicamente si están
vacías. Si otra instalación contiene registros antiguos, se detiene antes de
eliminarlos: será necesario trasladarlos o archivarlos explícitamente. También
impide revertir la migración si el nuevo historial ya contiene respuestas.

Para probar además la migración sobre PostgreSQL (crea y elimina un esquema
temporal aislado, sin modificar las tablas de la aplicación):

```sh
docker compose run --rm --no-deps -e TEST_POSTGRES_MIGRATIONS=1 backend python -m pytest -q
```

## Metadatos de origen de Trivial

Desde `backend/`, ejecutar la simulación (solo lectura):

```sh
python -B tools/assign_trivial_metadata.py
```

El diagnóstico detallado escribe un informe en la ruta indicada; se recomienda
una ubicación fuera del repositorio:

```sh
python -B tools/diagnose_trivial_sources.py --output /ruta/externa/informe.md
```

Tras verificar un respaldo de la base, aplicar las asignaciones:

```sh
python -B tools/assign_trivial_metadata.py --apply
```

La herramienta vuelve a comparar los TXT y las preguntas antes de escribir.
Exige 160 correspondencias únicas, cero incidencias y diez preguntas por cada
combinación de cuatro categorías de origen y niveles 1–4. Rechaza categorías
ambiguas y metadatos incompatibles. En una sola transacción crea o reutiliza
las cuatro categorías sin bloque y modifica únicamente `category_id` y
`difficulty` de las preguntas identificadas. Puede repetirse sin duplicados.
No ejecuta el importador de escritura ni clasifica Pasapalabra. Los niveles son
los del prototipo; su significado académico sigue pendiente de validación.

## Resumen de actividad

`GET /game/progress` requiere autenticación y no acepta un ID de usuario.
Devuelve `started`, `completed` y `unfinished`, además de `by_mode` con los
mismos recuentos para `TRIVIAL` y `PASAPALABRA`. Cuenta todas las partidas del
usuario mediante agregación en la base; una partida completada con cero aciertos
cuenta como completada. Un usuario sin actividad recibe ceros conocidos.

Las mejores marcas no agrupan todas las partidas mixtas como equivalentes.
La primera versión se limita a partidas con categoría y
dificultad históricas únicas y conocidas, e igual modalidad, temática y número
de preguntas.

La respuesta añade `best_marks` (lista vacía cuando no hay resultados válidos).
Cada elemento incluye `game_mode`, `topic_id`, `topic_name`, `category_id`,
`category_name`, `category_name_source`, `difficulty`, `total_questions`,
`best_score`, `session_id`, `started_at`, `valid_results` y
`tied_best_results`. `topic_name` utiliza el nombre conservado en la partida
ganadora (`topic_name_source: "historical"`). En partidas antiguas utiliza el
catálogo actual (`"current"`) o `null` si no está disponible; no se presenta
como nombre original. `category_name` procede de `content_context` cuando existe
(`category_name_source: "historical"`); si falta, se consulta el nombre actual
(`"current"`) o se devuelve `null` si no está disponible.

Las marcas se calculan para todo el historial del usuario autenticado mediante
consultas por conjuntos, sin cargar enunciados ni la copia privada de inicio;
comprueba los campos de corrección del historial. Solo entran
partidas completadas con preguntas distintas, puntuación entre cero y el total,
contexto que cubre exactamente esas preguntas, categoría única con ID conocido,
dificultad única entre 1 y 4, y un registro de respuesta coherente por pregunta.
Se agrupan por modalidad, temática, categoría histórica, nivel y número de
preguntas. Gana la mayor puntuación; el empate se resuelve por primera fecha de
inicio y después por ID, y `tied_best_results` indica cuántas comparten la
mejor puntuación. No se usa el tiempo. Partidas excluidas de marcas siguen
contando en `started`, `completed` y `unfinished`.
Las partidas antiguas sin `content_context`, las mixtas, las que carecen de
categoría o nivel y las que tienen respuestas incompletas o incoherentes no
aportan marcas. El nombre de temática histórico solo existe para partidas
nuevas que lo conservaron al inicio.
Las pruebas relacionadas se ejecutaron en bases aisladas (20 aprobadas); no se
crearon partidas en la base habitual para verificar estos casos.

Cada marca incluye `results`, con `session_id`, `started_at`, `score` y
`total_questions` de todas sus partidas válidas. La lista usa exactamente los
mismos criterios de clasificación y respuesta que la marca y se ordena por
fecha de inicio e ID. No se limita ni trunca: el contrato entrega el historial
comparable completo. Si el volumen llegara a hacer excesiva la respuesta, se
necesitaría paginar los puntos por grupo mediante un endpoint específico,
indicando el total y la continuación; no se perderían resultados en silencio.
