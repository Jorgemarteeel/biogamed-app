# Selección académica por categoría — backend

Entrega del 6 de noviembre de 2026. No incluye pantallas ni navegación de catálogo.

## Selección y contratos

La selección académica contiene `subject_id`, `block_id`, `category_id` y, opcionalmente, `difficulty` (1–4) o `difficulty_unknown:true`. Sin ambos filtros se admiten todos los niveles, incluido NULL. No admite `topic_id` junto a la jerarquía; puede omitirse o ser null en la selección académica. Una selección heredada sigue exigiendo `topic_id`, con categoría/dificultad opcionales y sin asignatura ni bloque. IDs positivos estrictos, campos desconocidos y filtros contradictorios producen 422. Una relación inexistente o cruzada produce 404. Se comprueba la jerarquía al preparar y al iniciar, sin deducir relaciones por nombres.

Ejemplo de cuerpo académico (los IDs deben existir y pertenecer a esa jerarquía):

```json
{"subject_id": 1, "block_id": 2, "category_id": 3, "difficulty": 2}
```

Todos los endpoints siguientes requieren autenticación; no cambian los permisos de gestión docente.

| Contrato | Comportamiento |
| --- | --- |
| POST `/game/academic/preparations?mode=TRIVIAL` | Disponibilidad agrupada por dificultad dentro de la categoría. `mode` admite también PASAPALABRA. Devuelve `academic`, `topic_id:null`, modalidad, total y combinaciones sin preguntas ni soluciones. |
| POST `/game/academic/start` | Inicia **Trivial** con el cuerpo académico. Hasta diez preguntas elegibles, sin reemplazo. 409 si no hay ninguna. No se inicia Pasapalabra mediante esta ruta. |
| POST `/pasapalabra/preparations` | Acepta ambas variantes de selección. Devuelve contexto académico cuando corresponde, cantidad, mínimo 40 y `can_start`. |
| POST `/pasapalabra/local/start` | Selección académica o heredada + `guest_name` + `operation_id` UUID. |
| POST `/pasapalabra/rooms` | Selección académica o heredada + `operation_id`. Unión, confirmación e inicio conservan sus contratos. |

Las rutas heredadas `/game/availability/{topic_id}` y `/game/start/{topic_id}` siguen siendo selecciones por temática. Las nuevas rutas académicas rechazan cuerpos exclusivamente heredados. No se amplían permisos para consultar contratos docentes con soluciones.

## Motores, privacidad y persistencia

Se reutiliza `selectable_questions` para disponibilidad e inicio, retiradas, modalidad y filtros. La categoría académica puede reunir preguntas de varios Topic: no hay filtro por Topic en esa variante y no se buscan otras categorías para completar un banco. Pasapalabra sigue necesitando exactamente cuarenta IDs distintos, veinte por participante, con selección sin reemplazo. Trivial conserva su límite de diez. No cambian turnos, relojes, normalización, puntuación, abandono ni privacidad de los rivales.

Las sesiones académicas guardan `topic_id:null`, incluso si las preguntas finalmente seleccionadas proceden de una sola temática. Así no se representa falsamente la selección como un banco heredado. `question_snapshot` mantiene el Topic real de cada pregunta; `content_context.questions` conserva además Topic y clasificación académica reales al iniciar. `content_context.academic` guarda IDs y nombres académicos. La corrección de Trivial comprueba la correspondencia de las copias y clasificaciones guardadas, sin volver al banco actual.

La sala guarda `configuration.academic` al crearla, lo expone a ambos participantes y lo conserva al iniciar, incluso si después cambia un nombre. Se revalida la relación real de los IDs y el banco antes de iniciar. La clasificación de cada pregunta se copia en el momento del inicio. `MatchState.academic` y el resultado contienen solo los seis campos públicos de la jerarquía: no se usan para publicar IDs de preguntas futuras, copias ni soluciones del rival.

Los cuerpos idempotentes heredados conservan su forma anterior: no se añaden claves `subject_id:null` o `block_id:null` a los recibos existentes. Un cambio de selección con el mismo UUID continúa produciendo conflicto. Los bloqueos de cuenta, sala y partida y el control de versión siguen siendo los del motor común.

## Historial y progreso

`GameSessionStartResponse`, historial, disponibilidad y mejores marcas admiten `topic_id:null`. Historial conserva `content_context.academic` guardado, sin rellenar relaciones históricas con el catálogo actual. Contextos antiguos sin `academic` o Topic por pregunta mantienen sus campos ausentes al serializarse. Las correcciones y resultados siguen siendo personales.

Las mejores marcas académicas se agrupan por selección académica (asignatura/bloque/categoría), modalidad, dificultad homogénea, cantidad y formato local/en línea; no se mezclan con las heredadas por temática. Se devuelve contexto académico guardado para identificar cada grupo. Se mantienen las restricciones anteriores de resultados completos, dificultad/categoría homogéneas y cierre normal: no se inventan nuevas marcas para dificultad mixta o sin clasificar. Abandono sigue excluido. El contador de actividad no duplica la partida compartida.

## Migración y despliegue

`b31c40d52e63`, posterior a `a21b30c41d52`, amplía el esquema permitiendo NULL en `game_engine_sessions.topic_id`; conserva columna, FK, valores y relaciones existentes. No modifica filas ni reconstruye copias. Downgrade rechaza bases con sesiones académicas para no perder historial.

Ensayada únicamente en `biogamed_pasapalabra_test`, usuario `codex_test`, con esquemas temporales únicos y comprobación de identidad. Se verifican migración, `alembic check`, conservación íntegra de una sesión anterior, ausencia de backfill y bloqueo del downgrade con historial académico. Los motores de Trivial y Pasapalabra se prueban también sobre ese esquema PostgreSQL migrado. No se aplicó esta migración en la base habitual ni se escribieron datos en ella.

Para desplegar la futura interfaz se necesitará aplicar esta migración en cada base autorizada, tras su copia y ensayo correspondientes. La demo no se ha migrado ni poblado para esta entrega exclusivamente backend; conserva su versión de interfaz. El cliente actual aún no presenta la selección académica ni sus nuevas etiquetas: esas pantallas y la revisión visual corresponden a la siguiente entrega. No se declara revisión de navegador en esta entrega.

## Dependencias de Topic conservadas

- `questions.topic_id` y sus copias privadas: origen real de cada pregunta y corrección histórica.
- `game_engine_sessions.topic_id`: FK opcional, presente en todas las sesiones heredadas; las nuevas académicas no dependen de ella.
- Endpoints, filtros y catálogo de temáticas de los accesos anteriores.
- Recibos y selecciones históricas de salas/partidas y grupos de marcas heredadas.
- Frontend existente, cuyo tratamiento de `topic_id:null` y nombres académicos se implementará en la siguiente fase antes de ofrecer la nueva selección.

Retirar Topic requeriría acordar el tratamiento del contenido sin categoría/bloque, sustituir los accesos heredados y sus clientes, versionar contratos y copias, preservar los recibos idempotentes y definir una migración explícita para las relaciones históricas. Esta entrega no elimina tablas, no reasigna preguntas y no completa automáticamente su clasificación.

## Verificación

Pruebas nuevas: selección entre Topic, jerarquía cruzada, categoría y dificultad, retirada, clasificación ausente, límites 39/40 y diez, autenticación, permisos del historial, copias inmutables, contexto de sala acordado y reintentos compatibles. Regresiones generales en SQLite sin red; carreras y migración en PostgreSQL aislado. Suite general: 262 aprobadas y 20 omitidas por requisitos opcionales o PostgreSQL no configurado en esa ejecución sin red. PostgreSQL explícito: 15 aprobadas (migración, motores académicos, bloqueos y concurrencia). Tras tipar el contexto público, 34 regresiones afectadas aprobadas. Después del último refuerzo de validación de copias académicas: 38 pruebas relacionadas aprobadas, incluyendo progreso y protección frente a contexto manipulado. No se instalaron dependencias.
## Segunda entrega de catálogo e interfaz

El texto anterior conserva el registro de la primera entrega backend. Se ha añadido después el catálogo autenticado `/practice` y la interfaz `/practicar`, con contexto guardado en juegos e historial. `b31c40d52e63` se ha aplicado únicamente en la demo previa copia verificable; no en la base habitual. Véanse [contratos del catálogo, estado de la demo, comprobaciones y revisión visual pendiente](../../frontend/docs/academic-practice.md). La restricción actual a herramientas específicas de navegador impide completar aquí la revisión visual móvil y la unión/confirmación/inicio de sala; las pruebas HTTP/componentes no se presentan como revisión visual.

## Aprobación y estado de integración — 9 de noviembre de 2026

El usuario autorizó guardar el conjunto pendiente en commits locales, tras revisar personalmente los cambios visuales y confirmar la corrección del acceso duplicado. El backend académico, catálogo, migración aditiva y compatibilidad heredada se incluyen en el primer commit; la interfaz y herramientas se organizan en commits posteriores dependientes. No se añadieron reglas ni funcionalidades durante esta revisión.

La base habitual biogamed ya fue actualizada mediante una autorización separada a b31c40d52e63: copia completa externa, restauración en base nueva, ensayo correcto y comparación de todas las filas mediante huellas antes y después. Conservó 5 usuarios, 371 preguntas, 19 sesiones y 111 respuestas; disponibilidad e historial autenticados de lectura verificados. La demo también está en b31. Este registro corrige las referencias históricas a migración habitual pendiente; no significa que exista clasificación académica en la habitual (siguen cero asignaturas y bloques). La operación de commit no vuelve a conectar ni escribir en bases. Evidencias privadas de migración y copias permanecen fuera del repositorio; no se incorporan sus contenidos.
