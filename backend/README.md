# Base de datos y banco de preguntas

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
