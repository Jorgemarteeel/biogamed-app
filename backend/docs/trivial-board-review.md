# Trivial — Entrega A: tablero y cobertura verificable

## Alcance

Vista docente `/gestion/trivial`, accesible desde el menú personal de docentes y administradores: tablero versionado, revisión de casillas/efectos y cobertura de contenido. No es una partida ni un editor persistente. No existen dado, comandos de juego, sesiones nuevas ni endpoint de inicio. El Trivial individual, preparación académica e historial mantienen sus contratos.

## Recurso y versiones

`app/data/trivial_board_v1.json` es una definición derivada y versionada (`trivial-original-board-v1`) de `raw_data/Trivial_Pursuit/Juego_tipo_Trivial_Pursuit/Posiciones/posiciones.json`. Incluye sus 140 polígonos, dimensiones de la imagen original, número/orden, tipo, banco visual y nivel. Conserva el SHA-256 del archivo de posiciones y el nombre original de cada casilla. Los originales no se modifican ni se necesitan en tiempo de ejecución. No se incorpora la imagen original de 13 MiB: el mapa de revisión dibuja las geometrías en SVG; la tabla paginada ofrece el detalle legible.

Corrección explícita del recurso: casilla 14, `source_label=Jeriguinlla`, `label=Jeringuilla`, banco `SYRINGE`. No reclasifica preguntas. Los niveles son 1–57 → 1, 58–98 → 2, 99–123 → 3 y 124–140 → 4. El validador exige exactamente 1–140 en orden, tipos/bancos coherentes con las etiquetas originales, niveles por tramo y geometría finita dentro del tablero. Solo Salida y Llegada pueden ocupar los extremos.

Los efectos declarados como OBSERVED describen el código del prototipo, no ejecutan transiciones. Cerebro es PENDING y no admite parámetros provisionales. Bazo, Cerebro, continuidad del turno tras acertar, participantes/identidad, agotamiento/reutilización, abandono y desconexión permanecen pendientes. No se fijan cantidad de jugadores, bancos de Cerebro ni políticas de salida.

Esta versión no se sobrescribirá para representar reglas futuras de partidas: cuando existan partidas habrá que conservar su versión/copia. La Entrega A no crea esa persistencia ni necesita migraciones.

## API y permisos

Todas las rutas exigen `require_content_staff`: usuario autenticado, versión de credenciales y rol teacher/admin vigentes en base. Sin sesión: 401; estudiante: 403. Metadatos y recuentos únicamente; sin enunciados, opciones, soluciones, copias privadas ni identificadores de preguntas. Respuestas `Cache-Control: no-store`.

- `GET /trivial-board`: definición y cobertura inicial sin vinculaciones. No intenta descubrir bancos por nombres.
- `GET /trivial-board/destinations?kind=category|topic&skip=0&limit=50`: nombres/IDs existentes y ruta académica real cuando exista. Orden ascendente por ID, límite máximo 100, total y paginación. No se filtran categorías vacías; no se inventa jerarquía para categorías sin bloque.
- `POST /trivial-board/coverage`: cálculo de lectura, no creación. Ejemplo de estructura con ID ficticio: `{"bindings":[{"bank":"LYMPHOCYTE","kind":"category","id":123}]}`. El cliente selecciona el registro por nombre; no se deducen asociaciones por ese nombre. Se rechazan campos adicionales, IDs inválidos, bancos desconocidos, duplicación de un banco y vincular Bazo mientras siga pendiente. Registro inexistente: 404; cuerpo inválido: 422.

Los bancos consultables son LYMPHOCYTE, MACROPHAGE, FLASK y SYRINGE. Cada uno puede vincularse expresamente a una categoría (incluye sus distintos Topic) o a una temática existente. No se crea, vincula o mueve contenido en base. La ruta académica se obtiene de las relaciones reales, no de nombres ni padres enviados por el navegador. Bazo se muestra pendiente, sin selector ni sustitución.

La vista es exploratoria: las elecciones solo duran en la memoria de la página; recargar vuelve a sin vincular. No hay configuración de bancos aprobada/persistida: `binding_version=null`, `bindings_persisted=false`. Cambiar un selector marca los recuentos como pendientes de actualizar; solo Consultar cobertura los recalcula. Se conservan las elecciones ante errores de consulta.

## Qué significan los recuentos

Se reutiliza `playable_question_filter('TRIVIAL')`, combinado con el ID explícitamente seleccionado: preguntas activas, modalidad Trivial, opciones e índice de solución no nulos. Se agrupa por dificultad en SQL; niveles 1–4 y sin clasificar se muestran separados. Esta entrega no cambia el filtro existente ni garantiza con él la suficiencia de una partida completa.

- UNBOUND: sin vinculación, recuentos null (— en pantalla), nunca cero inventado.
- PENDING: Bazo, recuentos null, pendiente de confirmación.
- EMPTY: destino consultado sin preguntas elegibles, recuentos cero.
- COUNTS_AVAILABLE: recuentos conocidos, **no significa suficiente ni listo para jugar**.

Se señalan niveles sin preguntas. Si dos selecciones comparten IDs se informa su intersección, sin repartir, fusionar ni duplicar un supuesto total global. Cada consulta representa el contenido disponible al consultar; puede cambiar posteriormente. No hay umbral 10/40 heredado de otros formatos: `sufficiency=UNDETERMINED` y `can_start=false` siempre, aunque todos los niveles tengan preguntas. No se añade un botón de inicio.

## Verificación (16-11-2026)

- Backend: 15 casos específicos de definición, corrupción, niveles, tipos, bancos, corrección, permisos de estudiante/docente/admin, campos adicionales, destinos paginados, filtros/retiradas, categoría con varios Topic, ausencia de inferencia por nombres, vacíos, solapamientos y privacidad. Una escucha SQL comprueba que la consulta no emite INSERT/UPDATE/DELETE/DDL; tampoco crea sesiones ni respuestas. Se aprobaron además nueve regresiones de motor individual y filtros: 24 casos únicos relacionados en total. Tras reforzar dos casos de definición se repitió solo el archivo afectado. Pruebas con SQLite en memoria en contenedor desechable, sin conexión a habitual/demo.
- Frontend: 53 casos relacionados aprobados (vista, menú y recorrido académico), tipos y lint. Tras corregir incidencias locales de lint y el tratamiento de reintentos, se repiten únicamente los casos afectados. Cobertura de selección explícita, permisos, pendientes, guardia de doble consulta, error recuperable, vacíos, paginación de destinos/casillas y ausencia de inicio. Avisos existentes: TestClient/httpx y atributo scroll del mock Link en pruebas académicas; sin nuevos fallos.
- Navegador integrado, solo demo: cuenta administradora existente, entrada desde menú por teclado; selección explícita de las categorías existentes para los cuatro bancos consultables (diez preguntas por nivel), categoría vacía (cero real), solapamiento (40 compartidas), mapa de 140 polígonos y paginación. Cuenta estudiante existente en sesión independiente: acceso rechazado. Sin crear cuentas, contenido, partidas o respuestas.
- Escritorio 1366×768: scrollWidth/clientWidth 1351/1351. Móvil 390×844: 375/375; tabla de cobertura desplazable internamente, tabla de casillas legible. Selectores con teclado y Escape. No hay prueba con lector de pantalla real, zoom 200 % ni pruebas de carga; no se afirma conformidad completa o capacidad de producción.

## Cómo revisar

Abrir <http://localhost:13004/gestion/trivial> con la cuenta docente/administradora existente. Inicialmente todo está sin vincular o pendiente, aunque haya destinos con nombres similares. Elegir explícitamente categoría o temática para un banco y pulsar Consultar cobertura; revisar niveles y bloqueos. Probar un destino vacío si se desea, abrir el mapa y recorrer las siete páginas de casillas. Recargar elimina las elecciones exploratorias; no escribe datos.

La demo conserva su configuración privada y no recibe migraciones. El repositorio habitual monta los mismos archivos de frontend/backend: la edición puede reflejarse allí, pero no se consulta ni modifica su base para esta revisión. No se introducen secretos, capturas o temporales en Git. Los datos y recursos originales permanecen intactos.

## Aprobación del usuario

El usuario revisó manualmente la demo y aprobó la Entrega A: diez preguntas por nivel en Linfocito, Macrófago, Erlenmeyer y Jeringuilla (160 en esos cuatro bancos), Bazo pendiente, mapa, tabla y descripción de efectos. Esta es una revisión del usuario, distinta de las pruebas automatizadas. Los recuentos no acreditan suficiencia para completar una partida ni resuelven las reglas pendientes.

## Motor parcial de movimiento (sin integración)

`app/domain/trivial_movement.py` incorpora una lógica determinista independiente de HTTP, ORM y frontend. Recibe el modelo validado del mismo JSON versionado mediante `MovementEngine(load_board())`; no importa el servicio de cobertura, autenticación ni modelos de base de datos. La carga lee únicamente ese recurso. Las funciones de transición no realizan I/O, no generan azar y no modifican el estado recibido.

Estado mínimo inmutable: versión del tablero, posición (inicial 1), fase, penalización del siguiente turno propio, requisito de pregunta y regla pendiente cuando proceda. No representa participantes, una partida completa ni resultados educativos. Cada transición devuelve un nuevo estado y una tupla ordenada de eventos; la traza vive en memoria, no es un historial persistente.

- `move(state, roll)`: acepta únicamente enteros 1–6 (rechaza también booleanos), desde READY. Mueve hasta `min(140, posición + tirada)` y resuelve solo la llegada; pasar por una casilla no ejecuta su efecto.
- ADN avanza tres, limitado a 140, y resuelve de nuevo la llegada. Virus retrocede tres (mínimo 1), no resuelve ese destino, termina el turno y marca la penalización.
- QUESTION_REQUIRED indica casilla, banco y nivel, sin escoger contenido ni procesar respuestas. Bazo conserva ese descriptor, pero queda en RULE_PENDING/BAZO_PENDING. Cerebro queda en RULE_PENDING/BRAIN_PENDING. Ninguno permite otra tirada o apertura de turno para eludir el bloqueo.
- GOAL_REACHED se emite después del evento LANDED de Llegada, también si se llegó mediante ADN. Solo identifica la meta; no asigna ganador ni cierra una partida persistida.
- `begin_own_turn` solo admite TURN_ENDED. Si hay penalización, la consume y conserva el turno terminado, sin tirada; la siguiente llamada corresponde a otro turno propio futuro y podrá devolver READY. Un futuro coordinador deberá invocarlo una sola vez por turno propio programado. Este módulo no define orden de participantes, identificadores de turno, idempotencia de comandos ni continuidad tras responder.

Ejemplos reproducibles: posición 1 + tirada 1 → casilla 2, pregunta de Linfocito nivel 1, espera sin contestar. Posición 2 + tirada 6 → Virus en 8 → retroceso a Erlenmeyer en 5 sin pregunta, turno terminado y penalización para el próximo turno propio. Además, posición 131 + 6 → ADN en 137 → Llegada en 140.

### Contraste con las fuentes y límites

Fuente conservada: `raw_data/Trivial_Pursuit/Juego_tipo_Trivial_Pursuit/INMUNOQUEST.html`: posición inicial y penalización inicial (490–493), avance limitado (581–593), Virus sin recursión (756–763), ADN con resolución recursiva (765–771), Cerebro y selección de banco/nivel (773–786), niveles (801–806), consumo del siguiente turno propio (1037–1043) y comprobación de meta **después** de resolver llegada (1050–1061). El JSON de Entrega A conserva la corrección documentada de Jeringuilla; no se modifica el recurso original.

No se traslada la rama genérica del prototipo como una regla de «casilla vacía»: el tablero validado solo tiene los tipos conocidos. Tampoco se adopta su interfaz ambigua de continuación de turno (1062–1067). En el tablero real, las cadenas de ADN desembocan en una pregunta o Llegada; se comprueban esas cadenas, sin inventar nuevos tableros o efectos. En particular, 9 → 12 lleva a Bazo y se bloquea, aunque el prototipo intentase cargar ese banco ausente. La suficiencia de contenido y las reglas pendientes de Entrega A siguen sin resolver. No hay política de respuestas, reto Cerebro, agotamiento, participantes, abandono ni desconexión.

### Comprobaciones de esta parte

52 pruebas del motor aprobadas, con un caso exhaustivo que recorre las 834 combinaciones de origen 1–139 y tirada 1–6. Cubren determinismo, inmutabilidad, entradas inválidas, fases, niveles por destino, ADN → pregunta pendiente, ADN → meta, Virus sin resolver retroceso, consumo de penalización, bloqueos Cerebro/Bazo, Jeringuilla corregida y rechazo de efectos incompatibles con la versión. Dos expectativas iniciales de pruebas se corrigieron contrastando los bancos exactos del recurso: casilla 12 Bazo y casilla 5 Erlenmeyer; no se alteró el tablero para satisfacerlas.

Comando reproducible (desde `backend`, con las dependencias fijadas instaladas): `python -m pytest --noconftest -p no:cacheprovider tests/test_trivial_movement.py -q`. `--noconftest` excluye el arranque de FastAPI y las fixtures de bases; un caso comprueba que no se han importado FastAPI, SQLAlchemy ni los módulos de arranque/base. Ejecución realizada en contenedor desechable con imagen existente, sin red, sistema de archivos de solo lectura y montaje del backend de solo lectura. Sin instalar dependencias, conectar bases, arrancar/recrear servicios ni escribir datos de aplicación. Las comprobaciones previas de Entrega A se mantienen; no hay cambios de frontend que requieran repetir tipos, lint o revisión visual. Sin endpoints, migraciones ni integración en el Trivial individual.

## Persistencia interna del motor parcial

Esta ampliación **no inicia partidas jugables ni incorpora endpoints**. Solo permite construir y recuperar un agregado interno de movimiento mediante un servicio probado con datos sintéticos. No integra preguntas reales, respuestas, resultados, salas, GameSession ni seguimiento. No deben publicarse estos métodos como inicio de partida mientras sigan pendientes Bazo, Cerebro, continuidad tras acertar, agotamiento y abandono. Una desconexión no tiene transición ni se interpreta como abandono.

Las decisiones de participantes actualizan lo que figuraba pendiente en Entrega A: LOCAL admite 1–4 plazas (cuenta anfitriona primero y hasta tres invitados con nombre); ONLINE, 2–4 cuentas distintas. Las plazas quedan cerradas al crear el agregado. Los nombres de cuentas se copian desde la cuenta, nunca se aceptan del solicitante; invitados solo tienen identidad de participante. No existe servicio para incorporar, sustituir o editar participantes posteriormente.

### Archivos y reutilización

- `app/models/trivial_board.py`: cuatro tablas propias: `trivial_board_matches`, `trivial_board_participants`, `trivial_board_turns`, `trivial_board_operations`. Se registran en `app/models/__init__.py`.
- `app/schemas/trivial_persistence.py`: preparación interna y comando estricto, sin campo para una tirada del cliente; rechaza cuentas repetidas, invitados online y plantillas inválidas.
- `app/services/trivial_persistence.py`: `create_internal`, `read_state`, `execute_move`; cada método posee su transacción y exige una Session dedicada sin escrituras pendientes. Usa el motor puro sin modificarlo.
- `alembic/versions/f75e841962a7_trivial_partial_persistence.py`: migración aditiva desde e64f73085196; exclusivamente cuatro tablas e índices nuevos, sin alterar las tablas previas. El downgrade rechaza descartar registros internos existentes.
- `tests/test_trivial_persistence_postgres.py`: integración y concurrencia real sobre PostgreSQL de pruebas.

Reutilización directa: modelos User/Base, definición y validador del tablero, motor parcial y reloj `server_now` de Pasapalabra. La autenticación HTTP seguirá siendo `get_current_user`, con su verificación JWT y versión de credenciales; no se añade otro parser JWT. Al no existir endpoints, los llamadores internos deben aportar un User previamente autenticado; el servicio vuelve a consultar su versión de credenciales y no confiere permisos por ser docente/administrador. Este contrato interno no es un sustituto de autenticación de red.

Patrones adaptados de Pasapalabra: bloqueo de fila, permisos de pertenencia, versión esperada, recibos y copias inmutables. Son propios de Trivial el máximo de cuatro plazas, posición/fase/penalización, turnos correlativos y efectos del motor. No se modifican Pasapalabra, sus salas, sus contratos ni sus datos. No se amplía `shared_match_id`, AnswerLog o GameSession.

### Estado canónico y recuperación

La partida conserva copia íntegra y versión del tablero, versión de reglas `trivial-movement-partial-v1`, versión de estructura del estado (1), configuración efectiva de alcance parcial/plantilla cerrada/orden de plazas, versión de concurrencia y número de turno actual. La copia/configuración solo se insertan; los comandos no las actualizan. El agregado guarda su tablero, de modo que recuperar o mover no vuelve a cargar el recurso actual del disco.

Cada participante conserva posición, fase y penalización. El turno referencia una plaza de esa partida y tiene inicio, fin y estado OPEN/ENDED/SKIPPED. **No se guarda un segundo JSON de posiciones/fases ni otro participante activo**: se obtiene del turno actual. Banco, nivel y regla pendiente se reconstruyen de posición, fase y tablero guardado; no hay pregunta seleccionada ni plazo que iniciar. `question_requirement` es solo el descriptor del motor, nunca una consulta al banco.

La lista inicial recibe un orden explícito del llamador interno (anfitrión primero). No implementa ni sustituye el sorteo inicial del prototipo o sus empates: un futuro coordinador deberá proporcionar el orden definitivo aprobado antes de usarlo en partidas reales. La configuración registra el orden utilizado para estas pruebas parciales, no una nueva regla de producto.

### Operaciones y penalización

`execute_move` recibe UUID idempotente, versión esperada, plaza y número de turno. El actor es siempre una cuenta; la plaza identifica al participante al que pertenece el movimiento. En LOCAL solo opera el anfitrión, también para invitados. En ONLINE cada miembro puede recuperar la partida pero solo actuar por su propia plaza en turno. Personas ajenas reciben 404; el rol docente/admin no concede acceso a partidas ajenas.

Orden: comprobar cuenta/versión de credenciales, bloquear partida, buscar recibo, validar actor y contenido del recibo, comprobar versión/turno/plaza/fase y, solo entonces, sortear en servidor mediante SystemRandom. El proveedor `roller` es una dependencia interna para pruebas, sin endpoint ni campo de petición que acepte la cara del dado. Una operación ya confirmada devuelve su recibo original junto con el estado actual, sin volver a sortear; mismo UUID con contenido o actor diferentes devuelve conflicto. Cada movimiento confirmado incrementa una vez la versión, incluidos los turnos perdidos que resuelva su efecto.

El cierre por Virus permite avanzar al siguiente turno de la lista cíclica observada en el prototipo. Se crea un registro por cada turno propio perdido, consume su bandera y sigue al próximo participante. El turno perdido no permite tirada. En LOCAL con una sola plaza, Virus deja consecutivamente un turno ENDED, uno SKIPPED y otro OPEN. Con varias plazas, cada penalización se consume al corresponder a su participante, no al consultar el estado. Turnos y recibos se guardan en la misma transacción que posiciones y versión.

Cerebro/Bazo y el requisito de pregunta bloquean nuevas tiradas. No se añade una acción genérica «siguiente» que permita saltarlos. Llegada registra GOAL_REACHED y cierra ese turno por GOAL_IDENTIFIED, sin ganador, puntuación ni resultado final. No hay reanudación desde decisiones pendientes. Una transacción fallida no deja movimiento confirmado; una futura repetición tras rollback podría sortear de nuevo porque no hubo recibo comprometido, nunca dos movimientos confirmados.

### Verificación de persistencia

- 28 casos nuevos aprobados: recuperación con otra conexión y sin volver a cargar el tablero del disco, idempotencia de creación/movimiento, contenido/actor incompatibles, permisos local/online, cuenta revocada, tamaños 1/4 local y 2/4 online, plantillas inválidas, fase/turno/versión, azar inválido, meta sin resultado, bloqueo pendiente y atribución actor/plaza sin sesiones ni respuestas personales.
- PostgreSQL real: dos comandos simultáneos con la misma versión ejecutan una sola tirada; mismo UUID concurrente devuelve el mismo recibo. Creación concurrente con la misma operación produce un solo agregado. Virus se consume una vez y no añade turnos al reintentar. Fallos inyectados al construir recibo y al confirmar transacción revierten posiciones, turnos, versión y recibo.
- Migración ensayada desde base vacía y desde e64f73085196 con cuentas/roles/hashes sintéticos, pregunta retirada, sesión/respuesta individual y una partida Pasapalabra con sus copias/comandos. Comparación íntegra de filas antes/después, no solo recuentos, y comprobación de columnas/nullabilidad de las cuatro tablas nuevas. No se reconstruye historia.
- Regresiones aprobadas: 52 del motor puro y 48 de Trivial individual, Pasapalabra, salas y Entrega A (128 casos únicos en total contando los nuevos). Tras ampliar la prueba de conservación y simplificar sus datos se repiten solo los casos afectados. Único aviso de esas regresiones: deprecación TestClient/httpx ya existente.
- Sin frontend nuevo: no se repiten tipos, lint de frontend ni recorridos visuales. Sin pruebas de carga ni afirmaciones sobre capacidad en producción.

Aislamiento antes de escribir: contenedor PostgreSQL 15 nuevo, base `biogamed_trivial_test`, usuario de pruebas `trivial_test`, volumen/red propios con etiqueta `biogamed.scope=trivial-persistence-test`, red Docker interna y ningún puerto publicado. Se verificaron identidad de base/usuario y cero tablas públicas antes del primer ensayo. Las pruebas exigen esos nombres/host, una referencia explícita al recurso y crean un esquema aleatorio propio por caso; solo eliminan ese esquema al terminar. Contenedores ejecutores con montaje de código de solo lectura y sin credenciales personales. No se aplicó la migración ni se escribió en habitual, demo o instalación limpia; tampoco se modificaron sus servicios.

Comando de pruebas, exclusivamente dentro de ese entorno aislado: `python -m pytest --noconftest -p no:cacheprovider tests/test_trivial_persistence_postgres.py -q`, configurando TRIVIAL_TEST_DATABASE_URL y TRIVIAL_TEST_RESOURCE para el recurso exclusivo. Las variables no deben apuntar a un entorno existente. No se necesita una restauración de datos privados para estas pruebas sintéticas.

Al terminar se retiraron únicamente el contenedor, volumen y red desechables creados para el ensayo, comprobando antes sus etiquetas e identidad. No quedó ningún esquema de prueba pendiente. La migración f75e841962a7 queda sin aplicar en habitual, demo e instalación limpia. En ese punto, el código quedó pendiente de revisión antes de confirmarlo.

### Revisión acotada de autorización y recuperación (16-11-2026)

Se detectaron y corrigieron dos defectos: el reintento de `create_internal` no recorría la comprobación común de versiones guardadas, y `next_turn` calculaba el siguiente participante por número de plaza en código en vez de consultar `configuration.turn_order`. Ahora la lectura, creación repetida, ejecución y devolución de recibos validan las versiones/copia/configuración conservadas; el avance utiliza el orden guardado. No se cambia el orden de las configuraciones existentes ni se añade un editor o sorteo inicial.

Se valida `SavedMovementConfiguration` para esta única versión parcial. Las nuevas copias incluyen `schema_version=1`; las copias originales sin esa clave se reconocen como el formato original v1, sin escribirles el campo ni regenerarlas. Versiones futuras/incompatibles devuelven un conflicto explícito (`UNSUPPORTED_SAVED_VERSION` o `UNSUPPORTED_SAVED_CONFIGURATION`), nunca sustituyen la copia con valores actuales. Configuración o tablero inválidos también se rechazan. La definición del disco solo se carga al construir un agregado nuevo. Se comprueban roster cerrado, modalidad y correspondencia del orden con las plazas existentes.

Autorización por operación:

| Camino | Garantías internas |
|---|---|
| Creación interna | Cuenta existente y versión de credenciales contrastadas en DB, plantilla validada, anfitrión como primera cuenta, límites e identidades de la modalidad. Un reintento comprueba además pertenencia y versiones guardadas antes de devolver estado. |
| Consulta | Cuenta vigente, pertenencia según modalidad y versiones/configuración guardadas. No exige que el solicitante tenga el turno: ambos participantes registrados online pueden recuperar el estado. |
| Movimiento nuevo | Lo anterior, más participante autorizado (local: anfitrión opera sus invitados; online: solo plaza propia), versión, turno actual, fase READY y turno OPEN. Todo antes del sorteo o los efectos. |
| Recibo confirmado | Cuenta vigente y pertenencia antes de buscar/devolverlo; mismo actor y contenido, participante autorizado y coherencia con su turno original. No exige que ese turno histórico siga abierto o activo: el recibo acredita una acción anterior, no autoriza una nueva. |

La consulta de vigencia lee columnas actuales de User sin refrescar en el mismo objeto ORM la versión que aportaba el actor autenticado. No se añade otra autenticación. Este contraste **no valida firma ni caducidad JWT**, no convierte un User aportado por código en prueba de autenticación y no reemplaza a `get_current_user`. La futura API deberá ejecutarlo en cada petición, obtener de esa dependencia el actor (nunca de un ID enviado por el cliente), usar sesiones de DB por petición y delegar estas reglas al servicio. Tampoco deberá publicar `create_internal` como inicio online libre: salas, incorporación/confirmación de cuentas y orden inicial continúan fuera de alcance. El proveedor de azar seguirá siendo una dependencia interna, nunca un dato aceptado del cliente.

Pruebas de esta revisión: **37 aprobadas** en `tests/test_trivial_persistence_review.py` con SQLite en memoria y ejecución sin red, sin conftest HTTP ni servicios de bases. Incluyen 27 comprobaciones específicas (versiones incompatibles en cuatro caminos, cuenta revocada antes de cada camino, recibo ajeno, turno histórico recuperable, copia guardada y orden 1–3–2, configuración inválida y compatibilidad sin reescritura) y diez regresiones que reutilizan las funciones/assertions existentes de persistencia. La prueba de copia impide cargar el tablero actual tanto al recuperar y reintentar la creación como al ejecutar un movimiento nuevo y consultar su recibo. No se vuelve a sortear ni se crean operaciones adicionales.

Comando desde backend: `python -m pytest --noconftest -p no:cacheprovider tests/test_trivial_persistence_review.py -q`, con DATABASE_URL=sqlite:// y una clave de prueba explícita para los módulos existentes que se importan. No se reutilizan credenciales reales.

En la revisión acotada anterior no se repitieron carreras PostgreSQL: se mantenían las evidencias previas de ese ensayo; las pruebas SQLite de esta revisión no se presentan como evidencia de bloqueos PostgreSQL. Tampoco se repitieron las baterías de juegos o frontend no modificados. No hay una prueba HTTP de la futura API, porque no existe, ni una nueva implementación de autenticación. Bazo, Cerebro y las otras decisiones siguen bloqueados. Migración f75e841962a7 intacta y sin aplicar a habitual/demo/instalación limpia; ningún cambio en servicios de esos entornos.


### Cierre de validación en PostgreSQL tras las correcciones (16-11-2026)

Resultado nuevo: **19 casos aprobados y 16 no seleccionados** en `test_trivial_persistence_postgres.py`. Se ejecutó solo la selección pertinente al servicio modificado; no se repitieron baterías de frontend, juegos o rendimiento. Se añadieron únicamente siete casos PostgreSQL necesarios: cuatro reintentos de creación con versiones incompatibles (estado, reglas, tablero, configuración), uno que reutiliza las comprobaciones de recuperación/copia guardada, y dos de avance/consumo de penalización con orden distinto de las plazas (local y online). Los demás casos reutilizan las pruebas existentes de creación/recuperación, idempotencia, atomicidad y concurrencia.

En el escenario de tres participantes, el orden guardado es 1–3–2. Tres llegadas sucesivas a Virus producen las plazas de turno **1,3,2,1,3,2,1**, con estados **ENDED,ENDED,ENDED,SKIPPED,SKIPPED,SKIPPED,OPEN**. Quedan tres recibos y versión 4, todas las fichas en 5 y todas las penalizaciones consumidas. Cada comando se reintenta después de cambiar el turno, sin otra tirada, recibo ni consumo. En online cada actor es la cuenta de su plaza; en local el anfitrión actúa por las tres plazas sin crear GameSession ni AnswerLog.

Las carreras reales verifican tanto dos operaciones distintas con una misma versión (solo una se ejecuta, la otra recibe STALE_VERSION) como el mismo UUID simultáneo (una tirada y un recibo compartido). La creación simultánea con el mismo UUID crea un agregado. Los fallos inyectados en recibo/commit revierten estado y turnos. Los reintentos de creación rechazan versiones incompatibles explícitamente, sin cargar la definición actual o sustituir copias.

Selección reproducible, dentro del entorno exclusivo de pruebas y con sus variables guardadas: `python -m pytest --noconftest -p no:cacheprovider tests/test_trivial_persistence_postgres.py -k 'closed_roster or setup_race or real_simultaneous or atomic_rollback or saved_board or local_guest or single_local or review_' -q`.

Aislamiento comprobado antes de escribir: PostgreSQL 15 en contenedor nuevo, base biogamed_trivial_test y usuario trivial_test, cero tablas públicas, red Docker interna, volumen propios etiquetados y ningún puerto publicado. Cada caso migró su esquema sintético nuevo. No se reutilizaron datos, copias privadas ni servicios de habitual, demo o instalación limpia. No hubo fallos de esta ejecución ni cambios adicionales en el servicio.

Esta evidencia PostgreSQL es **posterior** a las dos correcciones y distinta de las 37 comprobaciones SQLite de la revisión anterior. Las 28 pruebas PostgreSQL iniciales y las regresiones anteriores quedan como evidencia histórica; no se suman las ejecuciones repetidas como casos nuevos ni se presenta SQLite como prueba de bloqueos PostgreSQL.

Se conserva el contrato de seguridad: la futura API deberá autenticar **cada petición con get_current_user y obtener de ahí el actor**, nunca de un ID del cliente. El servicio interno comprueba vigencia y autorización, pero no autentica tokens por sí mismo. El alcance sigue siendo persistencia de un motor parcial: sin partida jugable, preguntas reales, respuestas, resultados, salas o integración con GameSession. Bazo, Cerebro, continuidad tras acertar, agotamiento y abandono permanecen pendientes/bloqueados. La migración f75e841962a7 solo se ha ensayado en pruebas; sigue sin aplicar en habitual, demo e instalación limpia.
