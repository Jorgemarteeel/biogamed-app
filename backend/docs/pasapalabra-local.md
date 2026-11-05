# Pasapalabra: motor compartido y API local

Actualización del 5 de noviembre de 2026: disponible la interfaz jugable local,
preparación, roscos numerados y recuperación por identificador. Véase
[interfaz y verificaciones](../../frontend/docs/pasapalabra-local.md).
Las referencias siguientes a la interfaz pendiente describen la entrega original
del motor del 4 de noviembre; se mantienen como registro histórico. Salas en línea
siguen pendientes. No cambia el contrato ni las reglas del motor.

Primera fase: motor persistente y API. No incluye pantalla jugable, rosco de
frontend, salas, códigos, confirmaciones ni sincronización en línea. La tarjeta
de Pasapalabra continúa «En preparación». La siguiente fase en línea reutilizará
el motor, con dos cuentas distintas y salas sin iniciar que caduquen a los 30
minutos; esos endpoints aún no existen.

## Reglas y almacenamiento

Dos participantes: posición 1 es el usuario autenticado; posición 2, invitado
con nombre. Solo el anfitrión consulta y opera cualquiera de las dos posiciones.
No se crea cuenta ni sesión personal para el invitado. Se sortean el primer
turno y el reparto de 40 IDs distintos mediante `SystemRandom.sample` sin
reemplazo. Cada jugador recibe 20 preguntas numeradas y 600000 ms. No se
impone cobertura alfabética ni se deduplican soluciones equivalentes.

Los filtros son temática (`topic_id`), categoría opcional, dificultad 1–4 o
`difficulty_unknown`. Las retiradas quedan excluidas. Preparación e inicio usan
los mismos filtros; inicio los revalida y bloquea las filas elegibles mientras
crea las copias. Si no hay 40, devuelve conflicto con recuentos: no reduce el
rosco ni relaja filtros. La preparación no reserva preguntas.

`pasapalabra_matches` guarda autoridad, versión, turno, fechas y desenlace;
`pasapalabra_participants`, identidad, cursor y tiempo;
`pasapalabra_questions`, copia privada inmutable, casilla, estado y respuesta;
`pasapalabra_commands`, operaciones idempotentes. Las copias incluyen soluciones,
alternativas y clasificación al inicio. Una edición o retirada posterior del
banco no afecta a corrección, tiempo ni historial de la partida.

Estados de casilla: `PENDING`, `PASSED`, `CORRECT`, `WRONG`. Solo las dos primeras
vuelven en recorrido circular. Acierto conserva turno; fallo y paso lo ceden.
Si el rival terminó, sigue el único participante que puede jugar. Al resolver
todas o agotar tiempo termina el participante antes de seleccionar otra
pregunta. Con ambos terminados, `outcome=NORMAL`; gana el mayor número de
aciertos y `winner_position=null` indica empate. Las pendientes no son fallos.

`abandon` cierra inmediatamente con `outcome=ABANDONMENT` y victoria del rival,
incluso si este tenía menos aciertos. Conserva respuestas y pendientes; excluye
todo el enfrentamiento de mejores marcas. Un cierre ya consumado no cambia.

Se reutiliza la corrección de BioGaMed: palabra exacta o alternativas configuradas,
ignorando mayúsculas y tildes y unificando espacios; `ñ` es distinta de `n`.
No se emplean coincidencias difusas ni servicios externos. Una entrada vacía se
rechaza; pasar es una acción explícita y no una palabra reservada.

## Contratos

Todos requieren `Authorization: Bearer …`. Las partidas ajenas devuelven 404,
sin conceder excepciones por rol docente o administrador. Los cuerpos rechazan
campos desconocidos. Los identificadores de operación son UUID generados por el
cliente y conservados durante los reintentos.

| Método y ruta | Cuerpo / resultado |
|---|---|
| `POST /pasapalabra/preparations` | `{topic_id, category_id?, difficulty?, difficulty_unknown?}` → `available`, `required:40`, `questions_per_player:20`, `time_per_player_ms:600000`, `can_start`, `selection`. |
| `POST /pasapalabra/local/start` | Selección + `{operation_id, guest_name}` → estado, HTTP 201. Repetir la misma operación devuelve la misma partida y su estado actual. |
| `GET /pasapalabra/matches/{id}` | Estado recuperable y reconciliado. |
| `POST /pasapalabra/matches/{id}/answer` | `{operation_id, expected_version, participant, number, text_answer}`. |
| `POST /pasapalabra/matches/{id}/pass` | `{operation_id, expected_version, participant, number}`. |
| `POST /pasapalabra/matches/{id}/abandon` | `{operation_id, expected_version, participant}`; puede abandonar cualquiera de los dos. |
| `GET /pasapalabra/matches/{id}/result` | Estado final; 409 `MATCH_NOT_FINISHED` si sigue en curso. |

El estado contiene `id`, `version`, `play_mode:LOCAL`, `rules_version`, `status`,
`server_now`, `turn_deadline_at`, `active_participant`, `active_question`,
`participants`, `outcome`, `winner_position`, `finished_at` y
`personal_session_id`. Cada participante incluye nombre, identidad registrada o
invitada, motivo de finalización, tiempo y contadores separados, casillas
numeradas y correcciones de las preguntas ya resueltas.

Actualización de presentación (5 de noviembre de 2026): cada elemento de
`participants[].resolved` incorpora `resolution_order`, la versión de la acción
de respuesta guardada en `pasapalabra_commands`. Es un orden global del
enfrentamiento, independiente del jugador, número de casilla y resolución
temporal del reloj. Puede tener huecos por pasos u otras acciones. La proyección
incluye la acción que se está confirmando y conserva el mismo valor al recuperar
estado o reintentar. No requiere migraciones, no entrega soluciones futuras y
no modifica turnos, reloj, corrección o puntuación. La interfaz lo usa para
identificar la última respuesta real, también tras una vuelta circular.

`active_question` contiene exclusivamente participante, número, enunciado y
letra. No se entregan las preguntas futuras, las copias privadas ni sus
soluciones. Las correcciones resueltas contienen respuesta, solución exacta y
alternativas; el anfitrión local puede ver las de ambos jugadores. Tras finalizar,
las preguntas que quedaron pendientes siguen sin revelarse.

Las acciones devuelven `{operation, state}`: `operation` es el recibo durable de
la acción y `state`, el estado actual. Un reintento puede recuperar un estado
más reciente que el original; el recibo conserva su versión original. Errores
409 principales: `INSUFFICIENT_QUESTIONS`, `IDEMPOTENCY_CONFLICT`,
`STALE_VERSION`, `OUT_OF_TURN`, `STALE_QUESTION`, `MATCH_FINISHED`.
Los errores de versión incluyen la versión actual; el cliente debe consultar
estado antes de una acción nueva. No debe convertir un reintento en una nueva
operación automáticamente.

Ejemplo de inicio (sustituir temática y credencial por las del entorno aislado):

```json
{
  "operation_id": "95b28609-0850-49be-a421-60bf099b3c70",
  "topic_id": 1,
  "guest_name": "Invitada",
  "difficulty_unknown": true
}
```

## Consistencia y reloj

Cada acción bloquea la partida con `SELECT FOR UPDATE`. Operaciones con la misma
clave y contenido no vuelven a responder ni pasar; con distinto contenido se
rechazan. Operaciones concurrentes distintas con la misma versión solo permiten
aplicar una. El inicio se serializa por usuario para garantizar también sus
reintentos. Los comandos rechazados no generan respuestas ni cambian el turno.

La hora autoritativa procede de PostgreSQL (`clock_timestamp`) después de
adquirir el bloqueo. SQLite solo sirve para pruebas funcionales con reloj
controlable. Se consolida tiempo real transcurrido desde el tramo anterior,
sin intervalos del navegador; el tiempo de transporte y espera de bloqueo
cuenta. En el instante exacto del vencimiento gana el reloj: no se acepta una
respuesta tardía ni una hora declarada por el cliente.

Antes de validar una acción o devolver estado se reconstruyen vencimientos.
El rival empieza en la fecha exacta en que venció el anterior, no en la fecha
de reconexión. Se pueden reconstruir ambos vencimientos tras veinte minutos
sin tráfico. Una acción rechazada conserva mediante commit los vencimientos
detectados y el tiempo realmente consumido. Recarga, cierre de pestaña,
desconexión, autenticación caducada o reinicio no pausan ni abandonan.

No se necesita un scheduler: el estado vencido se materializa al consultar o
actuar, incluyendo consultas de historial/progreso. La fecha lógica de cierre
sigue siendo el vencimiento exacto. Para la futura interfaz bastan comandos
HTTP y consulta de estado aproximadamente cada segundo; los relojes se animan
localmente y se resincronizan al recuperar foco.

## Historial y compatibilidad

Al iniciar se crea exactamente un `GameSession`, del anfitrión, enlazado por
`shared_match_id`. Conserva contexto y snapshot privado versión 2 de exactamente
20 preguntas; `QuestionSnapshot` versión 1 y los envíos antiguos mantienen el
límite de diez, incluido Trivial. El endpoint antiguo `/game/submit/{id}` rechaza
sesiones compartidas con `SHARED_MATCH_REQUIRES_COMMANDS`.

Cada respuesta del anfitrión genera un solo `AnswerLog`; las del invitado quedan
en sus casillas compartidas. No se crean registros ficticios para pendientes.
Historial añade campos nullable, sin reinterpretar filas previas: `format_key`,
`match_status`, `completion_reason`, `wrong_count`, `pending_count` y
`shared_match_id`. Mientras el enfrentamiento sigue en curso no se serializan
los logs históricos. Al cerrar por abandono se conservan y permiten consulta.

`is_completed` es true solo al cerrar normalmente todo el enfrentamiento.
Los abandonos permanecen en `unfinished` para conservar la definición de los
contadores existentes; `match_status=FINISHED` y `completion_reason=ABANDONMENT`
los distinguen de una partida en curso y no permiten reanudarlos. Los contadores
cuentan únicamente sesiones del usuario, nunca también la fila compartida.

Mejores marcas: solo cierres normales con logs y contadores coherentes, misma
temática, categoría y dificultad homogéneas, cantidad y `format_key`. Este
formato es `pasapalabra-local-v1` (20 preguntas y diez minutos); queda separado
de formatos heredados y del futuro formato en línea. Como antes, selecciones
sin clasificación homogénea no generan mejores marcas. No se comparan victorias
contra el invitado como si fueran su progreso personal.

Los pequeños ajustes del frontend son exclusivamente de historial: distinguen
pendientes, en curso y abandono. No habilitan la tarjeta ni implementan el rosco.

## Migración y verificación aislada

Migración aditiva `f17a20b30c41`, posterior a `e2b47c91a306`. Ninguna copia o
respuesta antigua se reconstruye. El downgrade se bloquea si hay partidas
compartidas, para evitar perder historial. No ejecutar contra la base habitual
sin un despliegue autorizado.

Pruebas funcionales: `python -m pytest -q tests/test_pasapalabra.py`.
Pruebas de concurrencia y migración:
`python -m pytest -q tests/test_pasapalabra_postgres.py`.
Estas últimas exigen `TEST_POSTGRES_URL` explícita con PostgreSQL desechable,
base exacta `biogamed_pasapalabra_test` y usuario `codex_test`. Verifican la
conexión efectiva antes de crear esquemas únicos; aplican Alembic completo en
cada esquema y solo eliminan ese esquema al terminar. Sin variable se omiten,
sin fallback a la base de aplicación. No introducir credenciales en Git.

Se cubren selección, filtros, retirada, insuficiencia, turnos, pasos repetidos,
cierre de última pendiente, empate, abandono, ventanas temporales, recuperación,
privacidad, copias, permisos, invitado sin progreso y mejores marcas. En
PostgreSQL se prueban doble respuesta idempotente, dos respuestas distintas,
respuesta/paso simultáneos, versiones obsoletas y migración/downgrade protegido.

Verificación del 4 de noviembre de 2026: suite backend general, 246 aprobadas
y seis omitidas por variables específicas de otras pruebas de migración;
tras añadir dos casos finales, las 20 pruebas específicas de Pasapalabra
(16 funcionales y cuatro PostgreSQL) aprobaron. `alembic check` no detectó
desajustes entre modelos y migración. Se ejecutaron también tests completos
de frontend, TypeScript y lint, sin instalar ni actualizar dependencias.

Se verificó la demo docente por puertos `127.0.0.1:13004` y `:18004`, volumen
`biogamed_docente_demo_demo_data` y conexión efectiva a `biogamed_demo` antes
de migrar únicamente esa demo. Se reutilizó su credencial local sin imprimirla.
La prueba HTTP creó la temática ficticia 6 (40 preguntas), enfrentamiento 1 y
sesión personal 12; comprobó preparación, inicio y respuesta idempotentes,
paso, recuperación, abandono, resultado e historial. El enfrentamiento quedó
cerrado por abandono y excluido de marcas. La demo sigue disponible; la base
habitual no recibió migraciones ni escrituras.
