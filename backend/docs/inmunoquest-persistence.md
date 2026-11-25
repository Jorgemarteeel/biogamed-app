# Persistencia interna del manual de Trivial de tablero

Base: main, `541cfcba08fdd17a366891b644b6fab85cdb0841`. Entrega interna con cierre autorizado en un commit local; sin push. No habilita partidas públicas.

> Actualización: la [preparación automática de mazos](inmunoquest-decks.md) se integra en la creación interna, con copias privadas v2. No añade partidas públicas.

> Ampliación siguiente: el servicio interno [inmunoquest_cards](inmunoquest-cards.md) extrae, reserva, autoriza al lector y registra evaluaciones. Conserva este coordinador para movimientos y recuperación; no añade API o interfaz.

## Qué se puede ejecutar

`app.services.inmunoquest_persistence` crea un agregado interno cerrado para 2–6 participantes, recupera su estado y ejecuta cuatro comandos de movimiento: `order`, `advance`, `virus` y `choose_bank`. El motor puro existente calcula las reglas; el servicio no vuelve a calcular efectos, ganador, nivel ni banco. Al llegar a `QUESTION` el comando de movimiento conserva el requisito y se detiene. La extracción y evaluación pertenecen al servicio interno de cartas, que exige una presentación real. `FINISHED` conserva la victoria aprobada en 140, sin pregunta final.

Local: anfitrión registrado en plaza 1 y uno a cinco invitados. Online: dos a seis cuentas distintas, con el anfitrión en plaza 1. El orden inicial se obtiene por tiradas, no por plazas; no se cambian las identidades al ordenar. Las creaciones nuevas requieren asignatura explícita y preparan sus veinte mazos; el mínimo técnico y su recuperación se documentan en la entrega de contenido. Los estados/recibos anteriores con subject_id=None siguen siendo interpretables, sin añadirles contenido automáticamente.

## Datos y versiones

Se reutilizan `trivial_board_matches`, `trivial_board_participants`, `trivial_board_turns` y `trivial_board_operations`, sin tablas paralelas ni relación con GameSession. La migración aditiva `d19c285da6eb`, posterior a `c08b174c95da`:

- Añade `manual_state` y `subject_id` opcionales a la partida. Se conserva el nombre de la asignatura elegida en la configuración, sin reescribirlo al renombrarla después.
- Amplía las plazas a seis y permite dejar vacíos los tres campos de estado exclusivos del HTML en las nuevas filas de participante. Una restricción exige que esos campos estén todos presentes o todos ausentes.
- No convierte, copia, reclasifica ni actualiza filas existentes. Las copias y presentaciones históricas no cambian.

Para el manual, `manual_state` es la única representación operativa de posiciones, grupos de orden/desempate, fase, índice activo y banco elegido. Incluye los dados ya recibidos de la ronda de orden incompleta y su número. Los participantes conservan únicamente identidad, plaza y nombre; sus campos HTML `position`, `phase` y `skip_next_own_turn` quedan SQL NULL. No se persiste una penalización futura de Virus para el manual. Ganador, requisito de pregunta y orden final se derivan del estado, evitando duplicarlos en columnas que pudieran contradecirse.

La partida conserva reglas `inmunoquest-manual-20261116-basic-v1`, tablero `inmunoquest-manual-board-v1`, esquema de estado 2 y un manifiesto del recorrido con salida 1 y meta 140. Se valida ese manifiesto y se usa exclusivamente la implementación de la versión guardada. No se sustituye el estado por una definición más reciente ni se convierte el del HTML: una versión incompatible produce `UNSUPPORTED_SAVED_VERSION`. El servicio histórico sigue interpretando su versión y rechaza la del manual.

Los turnos son registros de hechos: apertura, participante y cierre. Durante ORDERING aún no hay fila de turno; el contador interno 1 está reservado y la proyección devuelve `turn_number=None`. El evento `TURN_STARTED` abre el primer turno; `TURN_ENDED` de Virus cierra uno y abre el siguiente; `VICTORY` cierra el actual. La recuperación comprueba la coherencia entre el turno referenciado y el estado canónico.

## Orden y acciones

Cada participante envía únicamente la intención de tirar para sí mismo; en local el anfitrión puede hacerlo por cualquier plaza. El servicio genera un dado 1–6. Conserva el resultado parcial y resuelve la ronda con el motor cuando todos los pendientes han tirado. Solo los grupos empatados vuelven a tirar, conservando su prioridad previa. Una recarga entre las tiradas no obliga a repetirlas. No hay un límite artificial de rondas de desempate.

Los recibos conservan el dado generado, el número de ronda de orden cuando procede y los eventos del motor. Un evento ORDER_ROLLED en la resolución de una ronda describe las tiradas ya recibidas, no otra generación de azar. El generador por defecto es SystemRandom; las pruebas pueden inyectar una función sin que exista un campo `die` en los comandos ni un endpoint que lo acepte.

Las acciones requieren `operation_id` UUID, versión esperada, plaza y, salvo en orden inicial, número de turno. Solo `choose_bank` admite y exige un banco. No se admiten campos adicionales, evaluaciones ni tiradas proporcionadas por cliente.

## Autenticación, transacciones y reintentos

El futuro router deberá ejecutar `get_current_user` y obtener de ahí el actor. **Un objeto User por sí solo no demuestra autenticación**: no se añade otro login ni se acepta un actor declarado por el cliente. Se reutilizan los helpers existentes de sesión limpia, cuenta vigente/versión de credenciales, autorización de participante y errores del servicio histórico.

Antes de operar o devolver un recibo se comprueban cuenta vigente, pertenencia y modalidad. En local solo el anfitrión opera las plazas; en online cada cuenta actúa exclusivamente por la suya. Para una acción nueva se comprueban además versión, fase, turno y participante activo o pendiente de desempate. No se crea progreso personal del invitado ni del anfitrión por sus acciones.

Cada método posee commit/rollback y requiere una Session dedicada sin escrituras pendientes. El orden de bloqueo es cuenta y después partida: la creación actual mantiene un bloqueo compartido de cuenta y un advisory lock por UUID; las acciones y recuperación mantienen bloqueo de lectura de cuenta y exclusivo de partida. La actualización conserva los recibos históricos por propietario. Estado, turnos y recibo quedan confirmados en la misma transacción.

Un recibo se identifica por partida y operación. El actor, plaza y contenido completo del comando deben coincidir; otro uso produce conflicto. Un reintento confirmado devuelve **exactamente la respuesta original**, aunque posteriormente haya cambiado el estado, sin tirar de nuevo ni exigir que el turno histórico siga activo. Se vuelven a comprobar autorización vigente e integridad de la partida. `read_state` permite obtener el estado actual por separado. La creación también conserva su respuesta original en un recibo de setup. Las operaciones rechazadas o revertidas no tienen recibo confirmado.

La proyección usa una lista explícita de campos: nombres de jugadores, plazas, condición registrado/invitado, posiciones, orden, fase, dados de orden pendientes, turno, banco/nivel requerido y ganador. No devuelve UUID de cuentas, payloads privados, hashes, tokens, copias ni soluciones. No se expone públicamente ninguna función de esta entrega.

El reloj previo se extrae sin cambiar su semántica a `app.utils.server_time`: clock_timestamp de PostgreSQL, truncado a milisegundos, con el mismo fallback UTC para SQLite. Pasapalabra conserva los nombres importables server_now/utc; sus consumidores históricos usan la utilidad. Los tiempos registrados son de hechos; no se añade cronómetro al manual.

## Verificación y límites

Las pruebas `test_inmunoquest_persistence_postgres.py` usan una URL explícita y verifican host `pg`, base `biogamed_iq_persistence_test`, usuario `iq_test` y marcador de recurso propio antes de escribir. Cada caso usa un esquema nuevo y la cadena real Alembic desde vacío. El recurso de esta revisión es PostgreSQL 15 desechable con red interna exclusiva, sin puertos publicados y datos tmpfs: no usa volúmenes existentes, copias privadas ni conexiones de habitual, demo, instalación limpia o revisión 13014.

Cobertura: recuperación en ORDERING (incluidas rondas parciales/repetidas), READY, ROLL_AGAIN, VIRUS_ROLL, CHOOSE_BANK, QUESTION y FINISHED; plazas frente a orden; 2–6 local/online; acotación y victoria; Cerebro; detención sin cartas; reintentos originales; azar por defecto e inyectado; actor/plaza ajenos, credenciales revocadas, versiones y snapshots inválidos; rollback de estado/turnos/recibo; creación concurrente y acciones concurrentes con el mismo o distintos IDs, también entre cuentas online diferentes. Los casos de victoria usan posiciones sintéticas cercanas a meta, no una partida completa con preguntas simuladas.

El ensayo hacia delante prepara estado HTML, pregunta copiada, presentación y recibo reales mediante los servicios históricos, además de historial de Trivial individual y estado/copias/respuestas de Pasapalabra, todo sintético. Compara todas sus filas antes/después desde c08b174c95da, descontando únicamente las dos columnas nuevas inicialmente NULL; recupera después el estado histórico con su servicio y rechaza su interpretación como manual. No se reconstruye contenido ausente.

Evidencia anterior a la revisión de cierre (18 de noviembre de 2026):

- **40 aprobadas en 34,18 s**: 38 casos de persistencia/migración/concurrencia en PostgreSQL real y 2 pruebas unitarias del reloj. El primer ensayo detectó comparaciones inadecuadas en el test (hora de consulta variable y JSON True/1 que el ORM no marcaba como modificado); se corrigieron los fixtures y se verificó de nuevo el conjunto final.
- **99 regresiones aprobadas y 3 fallidas en 51,50 s** en los archivos de persistencia histórica PostgreSQL, copias/presentaciones, revisión SQLite y Pasapalabra PostgreSQL. Las tres fallidas son test_additive_migration_preserves_existing_rows_and_guards_data, test_migration_keeps_previous_movement_and_no_backfill y test_additive_migration_keeps_old_rows_and_guards_downgrade. Sus fixtures intentan hacer downgrade por debajo de c08b174c95da, cuyo downgrade está prohibido deliberadamente. Se ejecutaron exclusivamente esos mismos tres casos sobre una copia temporal del HEAD anterior 541cfcba: **también fallan allí por la misma causa** (5,82 s). No se debilita ninguna migración aplicada ni se presenta esa batería como totalmente verde; esa adaptación de fixtures se completa en la revisión de cierre descrita abajo. La conservación de la migración nueva se verifica mediante el ensayo hacia delante descrito arriba.
- **33 regresiones HTTP aprobadas en 9,87 s**, con las bases SQLite en memoria existentes: Pasapalabra local, salas y Trivial individual. Aparece el aviso de deprecación de Starlette TestClient/httpx ya presente; no se actualizan dependencias.
 No son pruebas de carga, navegador ni de una integración HTTP. Las 127 pruebas puras del motor aprobadas en la entrega anterior siguen vigentes: el motor no se modifica aquí.

Las ampliaciones de mazos y cartas enlazadas arriba incorporan copias abiertas, presentación sin plazo, lector y evaluación interna autorizada. Siguen fuera salas y acciones públicas, interfaz, resultados personales e integración educativa. No hay política nueva de abandono/desconexión; desconectarse no se transforma en abandono. No se migra ningún entorno existente.

Cierre de recursos: se detuvieron y eliminaron únicamente el contenedor PostgreSQL desechable y su red propia, verificando sus etiquetas. Los procesos de pruebas se retiraron con --rm. No se crearon volúmenes persistentes ni se retiraron imágenes existentes. Se eliminaron la configuración efímera de pruebas y la copia temporal del código de referencia, fuera del repositorio. Comprobadas también sintaxis/espacios de los diez archivos Python afectados, única cabeza Alembic d19c285da6eb y diff sin secretos ni temporales. La primera entrega se dejó sin staging ni commit; el cierre posterior se describe a continuación.
## Revisión de cierre y commit local

Se adaptan los tres tests históricos mediante `tests/migration_fixtures.py`: cada caso crea un esquema adicional en su revisión de origen (e64f73085196, f75e841962a7 o e2b47c91a306), copia exclusivamente fixtures sintéticos y ensaya el upgrade hacia delante. La reflexión evita utilizar modelos actuales contra columnas que aún no existen. Los campos posteriores omitidos deben ser NULL o tener un valor inicial expresamente comprobado (auth_version=0); no se descarta información no vacía. Se conservan IDs, relaciones, copias y recibos de esos fixtures. Esta técnica es únicamente de pruebas, no un procedimiento de traslado de datos de instalaciones reales.

Se mantienen todas las verificaciones de conservación, esquema, ausencia de backfill y recuperación. Los guards de f75 y f17 se invocan con el contexto real de operaciones Alembic en una transacción que siempre se revierte: así se verifica su rechazo exacto sin atravesar revisiones posteriores. Se verifica además que c08 sigue rechazando un downgrade de la cadena. Ninguna migración aplicada se modifica, no se usa stamp y no se omiten tests.

La revisión original descubre y corrige una validación incompleta: se comprobaba la fila actual de turno, pero no los huecos o contradicciones del registro previo. Antes de devolver estado o recibos se comprueban en una agregación SQL la continuidad del registro, el último número, el número de turnos abiertos y los metadatos de cierre. Se rechazan turnos adicionales, omitidos, varios abiertos, cierres sin fecha y turnos abiertos con cierre. Entonces los cierres solo podían deberse a Virus; la ampliación de cartas añade INCORRECT para el fallo evaluado mediante el motor. No se admite SKIPPED del HTML ni se cambia el reloj.

Evidencia nueva de cierre:

- **3 tests históricos de migraciones aprobados en 15,96 s**, con sus verificaciones conservadas y reforzadas. Las preparaciones ya no requieren el downgrade prohibido.
- **48 pruebas aprobadas en 32,02 s**: 46 de persistencia/migración/concurrencia PostgreSQL y dos unitarias del reloj. Incluyen ocho casos adicionales respecto a la primera entrega: cinco corrupciones sintéticas del registro de turnos, reintentos después de finalizar el turno en local y online, y rechazo de estado HTML independiente en participantes del manual. El caso de turno anterior ausente se reprodujo como fallo antes de corregir el servicio; después pasa el conjunto completo.
- Se comprueban otra vez las fases recuperables, versiones, identidad/cuenta vigente, separación plazas/orden, idempotencia con contenido y actor originales, generación única del dado, atomicidad y carreras reales, conservación de copias e historial y detención en QUESTION sin evaluación.

Se reutilizan sin repetir las 99 regresiones anteriores aprobadas de servicios históricos/PostgreSQL/revisión SQLite, las 33 HTTP SQLite de Pasapalabra/salas/Trivial individual y las 127 puras de movimiento. Solo se han modificado los tres casos históricos de aquella batería y han pasado expresamente con sus fixtures nuevos. No se presentan como resultados de una suite completa ejecutada ahora.

La consulta de coherencia se agrega en PostgreSQL por partida, sin cargar el registro completo de turnos en Python; no se han realizado pruebas de carga. No hay API nueva ni revisión visual que realizar en esta entrega interna. La migración d19c285da6eb sigue sin aplicar en habitual, reunión, instalación limpia y revisión 13014. Se retiraron únicamente el PostgreSQL desechable, su red propia y los temporales de esta revisión, tras comprobar sus etiquetas; no se retiraron imágenes ni volúmenes existentes. Se comprobaron sintaxis y espacios de los 14 archivos Python afectados, única cabeza Alembic d19c285da6eb y diff sin secretos ni artefactos privados.
