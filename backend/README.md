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

**Pendiente antes de editar preguntas:** durante una partida abierta, el envío
vuelve a leer la pregunta actual para corregirla. Una edición entre inicio y
envío podría cambiar la corrección respecto al enunciado visto; cambiar
temática o modalidad podría impedir el envío. Hay que resolver el versionado o
la protección de esas partidas antes de ofrecer edición general. Un bloqueo
basado solo en partidas sin finalizar no basta: algunas pueden quedar así
indefinidamente.

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

Al corregir una partida se guardan las respuestas y la puntuación en la misma
transacción. Cada respuesta conserva el enunciado, opciones, letra, respuesta
enviada y corrección de ese momento. Los cambios posteriores del banco no
alteran ese historial. La pareja partida/pregunta es única.

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
`tied_best_results`. `topic_name` procede de la tabla actual de temáticas porque
no se guarda una copia histórica de ese nombre; puede ser `null` si ya no está
disponible. `category_name` procede de `content_context` cuando existe
(`category_name_source: "historical"`); si falta, se consulta el nombre actual
(`"current"`) o se devuelve `null` si no está disponible.

Las marcas se calculan para todo el historial del usuario autenticado mediante
consultas por conjuntos, sin cargar enunciados ni soluciones. Solo entran
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
aportan marcas. El nombre de temática no tiene versión histórica guardada.
Las pruebas relacionadas se ejecutaron en bases aisladas (20 aprobadas); no se
crearon partidas en la base habitual para verificar estos casos.

Cada marca incluye `results`, con `session_id`, `started_at`, `score` y
`total_questions` de todas sus partidas válidas. La lista usa exactamente los
mismos criterios de clasificación y respuesta que la marca y se ordena por
fecha de inicio e ID. No se limita ni trunca: el contrato entrega el historial
comparable completo. Si el volumen llegara a hacer excesiva la respuesta, se
necesitaría paginar los puntos por grupo mediante un endpoint específico,
indicando el total y la continuación; no se perderían resultados en silencio.
