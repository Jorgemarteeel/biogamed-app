# Preparación automática y copias privadas de los veinte mazos

Entrega sobre main/19b0093501e4a0dd4980d41bac15f5f899aa9f29, inicialmente limpio. No habilita partidas públicas.

> Ampliación interna posterior, separada de esta preparación: [extracción, lector, evaluación y circulación](inmunoquest-cards.md). El orden inicial descrito aquí permanece inmutable; la circulación tiene su propio estado y migración f3be4a7fc80d.

## Creación y contenido seleccionado

`inmunoquest_persistence.create_internal` conserva autenticación vigente, participantes cerrados, modalidad, motor y estado. Ahora exige una asignatura existente para toda creación nueva y prepara automáticamente su contenido en la misma transacción que partida, participantes y recibo. El único dato de selección es subject_id: no admite categorías aisladas, dificultad global, listas de preguntas, orden de cartas ni actividades preparadas.

Se incluyen todas las preguntas abiertas INMUNOQUEST activas y válidas con subject_id explícito igual al elegido. Se reutilizan las comprobaciones de QuestionCreate y los filtros de contenido activo de la cobertura existente; no entran preguntas de otros formatos, retiradas, sin asignatura o de otras asignaturas. No se interpreta Topic como banco ni se cambia ninguna clasificación. Se agrupa por Bank del motor y nivel 1–4, independientemente del bloque/categoría donde esté distribuida cada pregunta.

Se respetan las relaciones académicas reales. Un bloque o una categoría ligados no pueden contradecir la asignatura elegida ni entre sí. La cadena categoría→bloque puede proporcionar contexto disponible cuando el campo directo de bloque está vacío, sin escribirlo en la pregunta. No se deduce una asignatura para incluir preguntas cuyo subject_id siga NULL, aunque una categoría pueda sugerirla: permanecen excluidas hasta una clasificación explícita.

El mínimo técnico aprobado es **una pregunta válida por combinación banco/nivel**. Se devuelve EMPTY_INMUNOQUEST_DECKS con minimum_per_deck=1 y la lista exacta de missing_decks (bank/difficulty). No se reducen mazos, amplían filtros ni sustituyen bancos. No se exige treinta; esa cantidad describe la edición docente recibida. Este mínimo no certifica suficiencia pedagógica, variedad ni capacidad de completar una partida.

## Consistencia ante cambios concurrentes

El conjunto seleccionado y sus etiquetas académicas se leen en una sola sentencia SQL, con joins por claves reales. Su snapshot MVCC de PostgreSQL es el instante de selección: una edición o retirada posterior puede cambiar el catálogo, pero no esa preparación. Una inserción posterior pertenece a los siguientes inicios. No se hacen cargas diferidas de relaciones o relecturas de las preguntas después de seleccionar. No se bloquea todo el catálogo ni se cambia la configuración de sus editores/importadores.

Las preguntas que no superen las validaciones no cuentan para el mínimo. Los errores de validación no se registran ni se serializan con su entrada, que podría incluir una respuesta. Las excepciones SQL de creación se convierten en MATCH_PERSISTENCE_FAILED sin parámetros ni cadena de excepción visible. La proyección pública continúa usando su lista explícita de campos, sin enunciados futuros, respuestas, copias ni órdenes de cartas.

## Copia y mazo: responsabilidades diferentes

Se reutiliza trivial_board_content_copies con snapshot_version=2. El cuerpo privado guarda ID de origen, formato INMUNOQUEST, enunciado exacto, respuesta de referencia y referencia opcional a apuntes. Banco/nivel son metadatos inmutables de la copia; clasificación y destino guardan IDs y nombres académicos disponibles al seleccionar. No se fuerzan opciones ni un plazo de sesenta segundos. El trigger existente impide actualizar o borrar copias; editar/retirar/reclasificar el origen no las modifica.

La tabla nueva inmunoquest_decks tiene una fila por partida/banco/nivel: veinte mazos compartidos por todos los participantes. Cada fila guarda exclusivamente la permutación inicial de IDs de copia, fecha y versión del barajado. No contiene cursor, cartas reservadas, descartes o respuestas. Una pregunta con el mismo texto que otra conserva su identidad y su banco; no se fusiona por texto ni respuesta.

El barajado de servidor está identificado como systemrandom-fisher-yates-v1: Fisher–Yates sobre las copias inicialmente ordenadas por ID de origen, usando SystemRandom.randrange. Las pruebas pueden inyectar una función interna que reordene la lista; se comprueba que siga siendo una permutación completa sin duplicados ni valores ajenos. Ese control no pertenece al esquema de petición ni se expone por HTTP. No se guarda una semilla: se conserva el orden efectivo. El trigger de mazos impide cambiarlo o borrarlo.

## Recuperación, permisos y atomicidad

La configuración interna marca content_preparation_version=inmunoquest-decks-v1, sin actividades docentes con nombre o cantidades objetivo. El esquema de estado del motor sigue siendo 2; el marcador de contenido versiona esta ampliación sin reinterpretar estados anteriores. La recuperación comprueba veinte mazos, versiones conocidas, pertenencia banco/nivel, orden no vacío y correspondencia exacta con los IDs de copia de esa partida.

`recover_private_decks` es un helper de servidor para un agregado ya autenticado y bloqueado; su resultado contiene respuestas y **nunca debe ser una respuesta HTTP**. Lee únicamente copias, contexto y órdenes guardados. La lectura pública y las acciones solo validan metadatos/órdenes; no cargan las respuestas privadas ni consultan Question. Versiones desconocidas de preparación o barajado se rechazan explícitamente. No se reconstruyen preguntas desde el catálogo.

La creación usa un bloqueo compartido de cuenta, que mantiene vigente su versión de credenciales sin impedir las comprobaciones de FK de otras cuentas del roster. En PostgreSQL, un advisory lock transaccional por UUID serializa nuevas creaciones con la misma clave, también entre propietarios distintos. Se conserva el recibo propio ya existente y se comprueba actor/payload antes de devolverlo. Si no existe recibo propio y otra cuenta utilizó la clave, se rechaza con IDEMPOTENCY_CONFLICT sin mostrar datos de esa partida. Posibles colisiones del hash solo serializan operaciones distintas; la comparación posterior siempre usa el UUID completo.

Los UUID antiguos podían estar separados por propietario: sus recibos propios siguen recuperándose aunque otro propietario histórico utilizase el mismo UUID. No se modifica esa historia. Los routers futuros deberán autenticar mediante get_current_user; un User construido no prueba autenticación. No se añade otro sistema de login. Se mantienen autorización local/online y ausencia de historial personal para invitados.

Todo se confirma una vez: partida, participantes, copias, mazos y recibo; cualquier error revierte el conjunto. Un reintento idéntico retorna la respuesta original y no vuelve a seleccionar, validar disponibilidad actual ni barajar. read_state devuelve el estado actual por separado. Las partidas internas anteriores sin el marcador conservan su recuperación, incluso los recibos históricos con subject_id=None; **no reciben mazos automáticamente**. Para ellas el helper privado devuelve CONTENT_NOT_PREPARED. None solo se admite para esos reintentos anteriores, no para crear partidas nuevas.

## Migración y conservación

La migración aditiva e2ad396eb7fc, posterior a d19c285da6eb, amplía las restricciones de copia con dos formatos explícitos: v1 conserva bancos del HTML (incluida Jeringuilla y dificultad desconocida); v2 admite los cinco bancos del manual y exige nivel 1–4. Crea inmunoquest_decks y su trigger. No actualiza filas ni copias, no altera presentaciones ni sus tiempos históricos, no reescribe migraciones y no hace backfill. Su downgrade rechaza eliminar preparaciones existentes.

Al desplegar, todas las preguntas y partidas existentes permanecerán como están; únicamente las creaciones internas nuevas insertarán sus copias y veinte mazos. No se cargan ni convierten los DOCX y no se importan las 600 preguntas reales. No se crean GameSession ni respuestas educativas en esta entrega.

## Comprobaciones

El 19 de noviembre de 2026 se verificó el árbol exacto de esta entrega en PostgreSQL 15 temporal, con dependencias fijadas y datos sintéticos. Pasaron **72 pruebas en 90,33 s**, 26 de preparación y 46 de persistencia. La única cabeza Alembic era e2ad396eb7fc, sucesora de d19c285da6eb. Los modelos, el servicio y la migración de cartas estuvieron ausentes en esta ejecución.

Pruebas PostgreSQL exclusivamente en un recurso desechable propio, con red interna, sin puertos publicados y almacenamiento tmpfs. Los fixtures comprueban base, usuario, host pg y marcador de recurso; cada caso migra un esquema sintético nuevo desde vacío. La conservación se ensaya además desde d19c285da6eb con copias/presentaciones v1 de Jeringuilla, dificultad desconocida y estados/recibos del manual previos a esta entrega. Se comparan todas sus filas antes y después y se recuperan con su versión correspondiente, sin backfill.

Resultados nuevos (18 de noviembre de 2026): **71 casos aprobados en 55,57 s** (25 nuevos de mazos/copias y 46 regresiones de persistencia adaptadas al contenido mínimo), más **28 aprobados en 32,31 s** de copias/presentaciones HTML y migraciones históricas relacionadas. Todos utilizan PostgreSQL real; se incluyen carreras entre creaciones de la misma y de distintas cuentas, edición concurrente del catálogo, rollback, conservación de v1 y ausencia de reconstrucción histórica. Las comprobaciones de formatos, texto español multilínea, referencias opcionales, actores/UUID históricos y procedimientos desconocidos están incluidas. La primera pasada de los 23 casos iniciales ya fue satisfactoria; el resultado de 71 corresponde al conjunto final ampliado y no se suma a ella.

En la revisión final se reprodujo un nombre de asignatura obsoleto en la caché ORM del llamante: las copias leían el nombre nuevo en el snapshot SQL, pero la cabecera podía conservar el anterior. Se corrige con populate_existing en la lectura bloqueada de Subject, sin refrescar ni reescribir partidas anteriores. Tras ese cambio se ejecutan de nuevo **26 casos de mazos aprobados en 20,18 s**, incluido ese nuevo caso y el aislamiento de categorías sin bloque y preguntas sin asignatura explícita. Los 46 casos de persistencia del lote anterior y los 28 históricos siguen vigentes; en total se cubren 100 casos distintos, no se suman las pasadas repetidas.

Se reutilizan las 127 pruebas puras del motor y la evidencia HTTP/frontend anterior que no cubre código modificado; no se presentan como ejecutadas ahora. El motor, los endpoints existentes, la importación y el frontend no se han cambiado. No hay interfaz nueva que revisar. No son pruebas de carga ni de navegador. La validación de integridad de la preparación examina los IDs/metadatos de una partida, no el banco de toda la plataforma; su coste depende del contenido de esa partida y no se ha medido bajo carga. La recuperación privada completa carga las copias de esa partida en servidor, nunca en un cliente.

Al terminar esta preparación faltaban extracción, presentación/reserva/descarte, lector, evaluación y reinicio del descarte; su implementación posterior está documentada en la entrega de cartas enlazada arriba. Siguen fuera salas/API, interfaz y resultados personales. El motor puro no cambia y se rechaza cualquier evaluación sin presentación real.

Comando del conjunto principal, desde backend con las variables de prueba aisladas: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -p no:cacheprovider tests/test_inmunoquest_decks_postgres.py tests/test_inmunoquest_persistence_postgres.py -q. La regresión adicional ejecuta test_trivial_content_postgres.py y los casos históricos de f75 y f17. INMUNOQUEST_TEST_DATABASE_URL debe apuntar a pg/biogamed_iq_persistence_test con usuario iq_test y un INMUNOQUEST_TEST_RESOURCE que empiece por iq-persistence-; las credenciales se proporcionan privadamente en el recurso desechable, nunca desde la configuración habitual.

Cierre: retirados únicamente el contenedor PostgreSQL, su red y la configuración efímera privada de estas pruebas, después de verificar etiquetas e identidad. No se crearon volúmenes persistentes ni se eliminaron imágenes existentes. Verificadas sintaxis/espacios de los once archivos Python afectados, única cabeza Alembic e2ad396eb7fc y creación de metadatos SQLite en memoria (solo compatibilidad de DDL, no evidencia de concurrencia). Diff revisado sin secretos, originales docentes ni temporales. No se ha aplicado esta migración ni escrito datos en habitual, reunión, instalación limpia o revisión 13014.
