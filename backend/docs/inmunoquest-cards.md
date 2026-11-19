# Cartas, lector y evaluación humana: servicio interno del manual

Esta ampliación continúa sobre la [preparación automática de mazos](inmunoquest-decks.md), guardada por separado. Es otra entrega interna, sin endpoints, interfaz jugable, salas o integración con GameSession. No inicia partidas públicas ni carga los documentos docentes.

## Qué reutiliza y qué añade

- Reutiliza el motor puro `inmunoquest-manual-20261116-basic-v1` sin modificarlo: determina banco/nivel, Cerebro, acierto y cambio de turno por fallo.
- Reutiliza la creación, cuenta vigente, pertenencia, modalidades, bloqueo de partida, versión, recibos y reloj de servidor de la persistencia del manual. El futuro router **debe obtener el actor mediante get_current_user**, nunca desde un ID enviado en el cuerpo. Un objeto User por sí solo no demuestra autenticación.
- Reutiliza las copias abiertas v2 y los veinte órdenes iniciales inmutables de la preparación pendiente. No selecciona preguntas reales otra vez.
- Amplía las presentaciones existentes con una versión explícita: v1 conserva las reglas del HTML y su plazo; v2 representa una aparición oral del manual, sin plazo. Añade una evaluación inmutable por aparición y una partición mutable de circulación por mazo.

## Operaciones y permisos

`present_internal` solo extrae cuando el motor está en QUESTION y una operación guardada de avance o elección de Cerebro solicita exactamente ese banco, nivel, participante y turno. No admite ID de carta, orden del mazo, respuesta oral escrita ni tiradas del cliente. Cerebro sigue exigiendo primero `choose_bank`; se conservan por separado la llegada al tablero y la solicitud posterior de pregunta.

Se extrae la primera copia disponible, se crea una presentación inmutable y se reserva hasta evaluar. Quedan vinculados partida, respondiente, turno, casilla, copia/banco/nivel, llegada, solicitud, ciclo, lector y fecha de apertura del servidor. Una solicitud tiene una sola presentación. Un reintento idéntico devuelve su recibo original; otro UUID para la misma solicitud pendiente devuelve la misma presentación y un recibo de reutilización, sin extraer ni incrementar de nuevo la versión. Solo en ese caso se admite la versión guardada de la solicitud o la actual; una extracción nueva exige versión actual exacta.

**Plazas y lector:** las plazas 1…N se dibujan en sentido horario y las personas miran hacia el centro. La izquierda de la plaza p es p+1, y la izquierda de N es 1. Por ejemplo, el lector de la plaza 2 es la 3 aunque el orden de turnos por dados sea 2, 1, 3. La futura interfaz deberá respetar esta orientación. No se reordenan las plazas según las tiradas.

En online pueden solicitar la presentación el respondiente o el lector; solo la cuenta del lector puede consultar la respuesta de referencia mediante `reader_view_internal` y evaluar. Los demás miembros pueden recuperar el enunciado actual, que se comunica oralmente, pero ninguna solución. En local solo opera el anfitrión, identificando explícitamente la plaza del lector en la vista privada y la evaluación. Esta separación evita exposición accidental; **no aísla a personas que comparten la misma cuenta o dispositivo**.

Todos los accesos vuelven a verificar cuenta/versión de credenciales vigente, pertenencia y modalidad. Los recibos también comprueban actor y contenido originales; conocer UUID o presentación ajenos no autoriza su consulta. La autorización del lector se conserva en reintentos después del cambio de turno; no se exige que siga activo el turno original. La consulta privada solo permite la presentación todavía vigente y no crea recibos con soluciones.

## Evaluación y circulación

El lector envía un booleano estricto Correcta/Incorrecta para la presentación vigente, indicando respondiente, lector, turno y versión. No se comparan textos ni se incorporan audio, IA o transcripción. La fecha de evaluación proviene del servidor. La presentación identifica al respondiente, el veredicto al lector y ambos distinguen al actor autenticado. No se crean sesiones personales para invitados ni se atribuye su respuesta al anfitrión.

- Correcta: el motor conserva el turno y la posición; la carta pasa al descarte del mazo.
- Incorrecta: el motor conserva la posición y abre el siguiente turno; la carta vuelve una sola vez al fondo de disponibles. El turno anterior se cierra con motivo INCORRECT, diferente de VIRUS.
- Si una nueva extracción encuentra disponibles vacíos, baraja el descarte en servidor y aumenta el ciclo. Usa el procedimiento versionado Fisher–Yates ya existente, con permutación controlable solo en pruebas. No toca el orden inicial guardado.
- Una carta reservada pertenece exclusivamente a esa presentación y no está en disponibles ni descarte. Nunca se recicla antes de evaluarla.

Cada mazo es compartido por todos los participantes. Con una carta, un fallo permite volver a extraerla cuando corresponda; un acierto permite barajar su descarte al agotarse disponibles. Cada aparición educativa tiene otra presentación. Repetir una petición de red conserva la presentación y no constituye otra observación educativa. No hay prohibición general de repetición.

Una evaluación ya confirmada solo se recupera mediante su operación original idéntica, incluso después del cambio de turno. Otra operación no vuelve a evaluar y cambiar el veredicto bajo la misma clave es conflicto de idempotencia. La vista general y **todos los recibos públicos** excluyen siempre respuestas de referencia, también después de resolver. Solo la operación privada autorizada devuelve la solución vigente; las listas completas de copias siguen siendo helpers internos de servidor.

## Recuperación y atomicidad

El orden inicial y las copias son inmutables. `inmunoquest_deck_states` contiene una única partición canónica: disponibles ordenados, descarte ordenado y presentación reservada; la carta reservada se deriva de esa presentación, sin duplicar su ID en otro estado. Cada copia pertenece exactamente a uno de esos conjuntos. Se validan versiones, veinte mazos, particiones, reserva y coherencia con el requisito del motor antes de devolver estado o recibos.

La recuperación lee únicamente esas copias/órdenes/estados y registros guardados. Editar, retirar o reclasificar un origen no cambia lo ocurrido. La proyección carga solo el contenido de la presentación actual para devolver una lista explícita de campos públicos, nunca futuros enunciados, soluciones u órdenes de mazo. La consulta privada carga esa misma copia, no el catálogo. No existe cronómetro ni fallo automático: una recarga, varios días transcurridos o una consulta no liberan ni evalúan la reserva.

El bloqueo FOR UPDATE de partida serializa extracciones y evaluaciones. Versión e idempotencia protegen operaciones obsoletas o repetidas. Motor, turno, circulación, veredicto, eventos y recibo se confirman en una transacción; cualquier fallo revierte todo. Las excepciones SQL de cartas devuelven CARD_PERSISTENCE_FAILED sin parámetros privados ni cadena visible. No se registran soluciones.

La validación de integridad recorre metadatos/IDs de los mazos de esa partida. La búsqueda de la solicitud usa los recibos de esa partida. No se han realizado pruebas de carga ni se garantiza capacidad de un hosting; antes de escalar deberá medirse ese coste. El navegador no recibe el banco completo.

## Esquema y separación de entregas pendientes

La migración **f3be4a7fc80d**, posterior a **e2ad396eb7fc** de la preparación, es aditiva:

1. Amplía `trivial_board_presentations` con versión, lector, solicitud y ciclo; permite deadline NULL exclusivamente en v2. V1 mantiene deadline obligatorio y posterior a apertura. Se conservan sus filas y fechas.
2. Crea `inmunoquest_deck_states`. Para mazos que nunca pudieron extraerse con e2 inicializa disponibles desde su orden inicial congelado, ciclo 1 y ningún descarte/reserva. No vuelve a consultar ni barajar el catálogo. Si hubiera presentaciones de copias v2 insertadas por una vía no soportada, rechaza inferir su consumo.
3. Crea `inmunoquest_evaluations`, un veredicto por presentación, con actor, lector y fecha; trigger impide editar o borrar. Las presentaciones siguen siendo inmutables.

No convierte estados del HTML o del manual sin contenido preparado. El downgrade solo permite retirar esta ampliación sin presentaciones/veredictos v2 ni circulación consumida; se mantiene el rechazo de pérdida histórica. No se modifica ninguna migración aplicada.

La preparación previa incluye el servicio y esquema `inmunoquest_content`, la migración e2 y sus pruebas y documentación. Esta ampliación añade el servicio y esquema `inmunoquest_cards`, la migración f3, pruebas de cartas y este documento. Los cambios compartidos son los nuevos modelos de circulación/evaluación, extensión de Presentation, registro de modelos, inicialización/lectura/coherencia de turnos en persistencia y las comprobaciones de columnas nuevas en dos tests históricos. La primera entrega se probó por separado antes de integrar estos fragmentos.

## Comprobaciones y límites

El 19 de noviembre de 2026 pasaron **42 pruebas en 73,16 s** en una instancia temporal de PostgreSQL 15 con datos sintéticos. Se ejecutaron los 40 casos de cartas y dos regresiones de conservación de presentaciones y estados anteriores. Incluyen acceso privado del lector local y online, recibos públicos sin soluciones, reserva única y evaluación única ante concurrencia. La única cabeza Alembic era f3be4a7fc80d, sucesora directa de e2ad396eb7fc. La evidencia siguiente corresponde a la implementación del 18 de noviembre y no se vuelve a sumar.

Evidencia nueva (18 de noviembre de 2026), siempre en PostgreSQL real desechable con datos sintéticos:

- **40 pruebas nuevas de cartas aprobadas** en el conjunto final (40 de los 41 casos aprobados en 46,67 s; el otro era una regresión histórica). Incluyen los cinco bancos en Cerebro y los límites de nivel, orientación por plazas distinta del orden de dados, permisos local/online y credenciales revocadas, privacidad en lecturas/recibos/errores, reserva recuperable sin plazo, reintentos originales después del cambio de turno, alias de presentación, veredicto único y actor/contenido originales, retorno al fondo, descarte, barajado, una sola carta y nuevas apariciones educativas.
- Carreras reales con conexiones PostgreSQL distintas: dos presentaciones concurrentes consumen una carta; dos veredictos opuestos producen una evaluación; dos peticiones idénticas con la misma clave ejecutan el motor una sola vez y recuperan el mismo recibo. Se comprueba rollback después de reservar y guardar recibo, y después de insertar el veredicto/cambiar turno, así como una permutación de reciclaje inválida.
- Revisión final del lector: **2 casos aprobados en 3,15 s**, local y online, con orden 2 → 1 → 3. El lector de la plaza 2 sigue siendo la 3, y un fallo pasa al jugador 1, demostrando que lector y siguiente turno no se confunden. Son dos de los 40 casos anteriores reforzados y repetidos, no dos observaciones adicionales que sumar.
- **100 regresiones relacionadas aprobadas**, en ejecuciones separadas: 26 de preparación, 46 de persistencia y 26 de contenido/presentaciones HTML, más los guards históricos de migración de Trivial y Pasapalabra. El primer lote dio 97/98: la comparación de una migración necesitaba comprobar las cuatro columnas añadidas; tras exigir sus valores iniciales v1/NULL y comparar todos los campos anteriores, pasó ese caso. La segunda prueba de conservación de presentación v1 se adapta igual, sin omitir ninguna comprobación antigua.
- Se ensaya f3 desde vacío en cada fixture y hacia delante desde e2 con mazos nunca extraídos: conserva catálogo, copias, órdenes iniciales, participantes, turnos, estado y recibos. Los tests comprueban que las presentaciones HTML conservan tiempos, contenido y recuperación, y que el downgrade rechaza pérdida de presentaciones/veredictos/circulación reales.

Durante varias pasadas el WAL llenó el tmpfs de 384 MiB del PostgreSQL desechable y bloqueó el último guard histórico de Pasapalabra. Se verificó el recurso propio, se repuso exclusivamente ese contenedor sintético con WAL acotado y se repitió solo el caso bloqueado: **1 aprobado en 4,34 s**. No fue un fallo de datos de la aplicación; no se modificó ningún servicio existente. Las primeras pasadas de cartas (28 y después 38/39) son evidencia de desarrollo y no se suman al total final; la diferencia del último caso era únicamente la expectativa del código de error ante una reserva sintética corrupta, que ya se rechazaba.

Evidencia anterior reutilizada: las **127 pruebas puras del motor**, las dos unitarias del reloj compartido y las comprobaciones HTTP/frontend de los formatos integrados que no han cambiado. No se presentan como ejecutadas ahora. No hay cambios frontend que requieran tipos, lint o compilación, ni una nueva interfaz que revisar. Estas pruebas no equivalen a una prueba de carga, una revisión visual ni una API autenticada ya integrada.

Comandos desde backend, con las variables privadas del recurso de pruebas (nunca las de una instalación):

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -p no:cacheprovider tests/test_inmunoquest_cards_postgres.py -q
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -p no:cacheprovider tests/test_inmunoquest_decks_postgres.py tests/test_inmunoquest_persistence_postgres.py tests/test_trivial_content_postgres.py -q
```

Los guards adicionales son `test_trivial_persistence_postgres.py::test_additive_migration_preserves_existing_rows_and_guards_data` y `test_pasapalabra_postgres.py::test_additive_migration_keeps_old_rows_and_guards_downgrade`. Los fixtures requieren host pg, base/usuario sintéticos y marcador iq-persistence- (o sus pares históricos específicos); cada caso crea y retira un esquema propio. El contenedor temporal usa red interna, sin puertos, sin volúmenes persistentes y almacenamiento tmpfs. No recibe copias o credenciales de entornos de la aplicación.

Comprobaciones estáticas: 15 archivos Python analizados y compilados sin escribir bytecode, espacios revisados en los 20 archivos pendientes, metadatos SQLite creados en memoria (solo DDL), única cabeza Alembic f3be4a7fc80d y diff sin secretos/temporales. La migración e2, el servicio/esquema de preparación y sus fixtures conservan exactamente el contenido previo. Se retiran únicamente el PostgreSQL desechable y su red verificados por etiquetas, y los temporales privados de esta tarea; no se eliminan imágenes ni recursos ajenos.

Quedan fuera: endpoints y autenticación en router, transferencia de dispositivo/vistas del lector, interfaz jugable, salas, comunicación oral externa, resultados personales e integración educativa con GameSession, abandono/desconexión y exportaciones. No se importa el contenido real ni se modifica habitual, reunión, instalación limpia o revisión 13014. No hay revisión visual que realizar en esta entrega sin pantallas.
