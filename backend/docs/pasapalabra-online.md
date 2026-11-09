# Pasapalabra en línea: salas privadas

Ampliación backend del 6 de noviembre de 2026: [selección académica por categoría](academic-selection.md), sin Topic único. Los contratos por temática se conservan.

Implementación sobre el motor de [Pasapalabra local](pasapalabra-local.md), sin
otro motor, WebSockets, colas ni servicio de presencia. Dos cuentas distintas,
20 preguntas y 600 000 ms individuales; sorteado el primer turno. Acierto
conserva turno; fallo o paso lo ceden. Las pasadas vuelven circularmente.
Preguntas resueltas y vencimientos terminan al participante; el otro continúa.
El reloj de servidor nunca se pausa por recarga, desconexión o cierre de pestaña.
Vencimiento prevalece sobre respuesta. Gana quien acumula más aciertos; admite
empate. Abandono explícito concede victoria al rival y excluye ambas sesiones
de mejores marcas. Pendientes no son fallos.

## Persistencia y consistencia

Migración aditiva `a21b30c41d52`, posterior a `f17a20b30c41`:

- `pasapalabra_rooms`: creador, segunda cuenta nullable, configuración inmutable,
  selección, código único, preparación de ambos, versión, fechas y partida única.
  CHECK impide la misma cuenta en ambas plazas.
- `pasapalabra_room_operations`: recibos duraderos por usuario y UUID, con carga
  normalizada. Mismo UUID/carga devuelve el recurso actual; otra carga produce
  `IDEMPOTENCY_CONFLICT`. Un reintento antiguo no vuelve a ocupar una plaza liberada.
- `pasapalabra_join_limits`: ventana y contador por cuenta, compartidos por procesos.

Código de doce símbolos aleatorios sin caracteres ambiguos (60 bits). Unión:
máximo diez intentos por cuenta por diez minutos, incluidos códigos incorrectos;
429 con `Retry-After`. Un reintento ya aceptado no consume otro intento. Esto
protege la búsqueda de códigos; no sustituye controles generales de registro
o abuso de cuentas de un despliegue público.

Transiciones: `WAITING → STARTED | CANCELLED | EXPIRED`. Caducidad fija a los
treinta minutos desde creación, sin ampliación. Se materializa al consultar u
operar, sin tarea programada. Antes de iniciar ambos deben estar preparados.
Solo creador inicia/cancela; solo segundo participante sale. Salir libera plaza
y borra ambas confirmaciones; una nueva unión obliga a confirmar otra vez.

Orden de bloqueo: cuenta (`FOR NO KEY UPDATE`), sala (`FOR UPDATE`) y selección
de preguntas ordenada. El bloqueo de cuenta conserva la exclusión entre sus
operaciones sin bloquear las referencias FK del rival. La versión rechaza
operaciones obsoletas. Iniciar crea partida, cuarenta copias y dos sesiones en
la misma transacción; clave interna estable derivada de sala. Revalida filtros,
retiradas y cuarenta IDs distintos sin reemplazo. Insuficiencia devuelve cantidad
y filtros, sin partida parcial ni relajación. Comprueba de nuevo caducidad tras
la selección bloqueada. Vencimiento detectado se guarda incluso si se rechaza.

`start_shared` y los comandos existentes son comunes a LOCAL/ONLINE. En línea,
la carga idempotente incluye actor; solo puede actuar por su participación.
El bloqueo de partida, las fechas PostgreSQL, la reconstrucción de ambos
vencimientos y la conservación del vencimiento ante rechazo siguen siendo comunes.

## Contratos autenticados

Todos requieren Bearer. Docente/administrador no evita pertenencia. El código
permite solicitar unión mientras espera; no autoriza acceso a partidas iniciadas.

| Método y ruta | Entrada / comportamiento |
| --- | --- |
| POST `/pasapalabra/preparations` | Selección existente: `topic_id`, `category_id?`, `difficulty?`, `difficulty_unknown?`; disponibilidad 40. |
| POST `/pasapalabra/rooms` | Selección + `operation_id` UUID; 201 `RoomState`, sin nombre de invitado. |
| POST `/pasapalabra/rooms/join` | `code`, `operation_id`; normaliza espacios exteriores y mayúsculas. |
| GET `/pasapalabra/rooms/{id}` | Solo creador/segundo participante actual. Recupera sala o enlace a partida. |
| POST `/pasapalabra/rooms/{id}/{ready,start,cancel,leave}` | `expected_version`, `operation_id`; devuelve sala actual o `{id,status:"LEFT"}`. |
| GET `/pasapalabra/matches/{id}` | Estado común, personalizado para la cuenta. |
| POST `/pasapalabra/matches/{id}/{answer,pass,abandon}` | Contratos existentes: UUID, versión, participante propio; número para responder/pasar y `text_answer` para responder. |
| GET `/pasapalabra/matches/{id}/result` | Estado final personalizado; 409 si sigue en curso. |

`RoomState`: `id`, `version`, `status`, `self_position`, configuración y selección,
`expires_at`, `server_now`, participantes con posición/nombre/preparación,
`match_id` nullable y `code` únicamente mientras espera. No envía emails ni IDs de
cuentas. Errores estructurados relevantes: `ROOM_UNAVAILABLE`, `ROOM_FULL`,
`DISTINCT_ACCOUNT_REQUIRED`, `JOIN_RATE_LIMIT`, `STALE_VERSION`,
`BOTH_READY_REQUIRED`, `INSUFFICIENT_QUESTIONS`, `ROOM_NOT_WAITING`, `ROOM_EXPIRED`.
Acceso ajeno devuelve 404. Solo acciones propias; 403 `ONLY_OWN_ACTIONS` al
intentar controlar rival. Conflictos comunes del motor conservan sus códigos.

Estado de partida añade `play_mode:"ONLINE"` y `self_position`. Solo entrega
`active_question` durante turno propio; en espera es null. Ambos roscos, relojes,
contadores y resultado son públicos para participantes. `resolved` del rival es
siempre vacío, incluso al cerrar. Solo correcciones propias incluyen pregunta,
respuesta y soluciones autorizadas. Nunca serializa copias ni preguntas futuras.

## Historial y compatibilidad

Una `GameSession` por cuenta enlazada a la misma partida; cada respuesta crea
un solo `AnswerLog` propio. Historial devuelve únicamente sesión y respuestas
del solicitante, más `shared_summary` tipado de nombres, contadores, estado y
ganador. No incluye preguntas ni respuestas del rival. Local conserva una sola
sesión del anfitrión; invitado sin progreso. Trivial y contratos heredados no
cambian. `/game/submit/{id}` sigue rechazando todas las sesiones compartidas.

Formato `pasapalabra-online-v1` distinto de `pasapalabra-local-v1` y legacy;
agrupación y etiquetas de mejores marcas/evolución distinguen ambos. Siguen
exigiendo clasificación homogénea y cierre normal. Abandono se conserva como
FINISHED/ABANDONMENT, excluido de marcas; permanece en el contador histórico
`unfinished`, cuya definición anterior no se modifica. No se cuenta la fila
compartida como otra sesión personal.

Downgrade solo con salas vacías: se bloquea si perdería historial. No reconstruye
ni migra copias antiguas. Despliegues requieren aplicar Alembic sobre su base
autorizada antes de usar salas; en esta tarea se migró exclusivamente la demo.

## Verificación, 5 de noviembre de 2026

- Suite backend general: 252 aprobadas y seis omitidas por requisitos opcionales
  de otras pruebas de migración. Después, nuevo caso de caducidad durante selección:
  ocho funcionales de salas aprobados (total equivalente 253, sin repetir la suite).
- PostgreSQL real: trece casos de salas/motor, incluidos carreras por plaza,
  misma unión, inicio doble con UUID iguales/distintos, creación repetida,
  doble respuesta, respuesta/paso, versiones obsoletas y dos creadores cruzados.
  Alembic completo, `alembic check`, downgrade vacío y protección con datos.
- Frontend: 102 aprobadas; tras el último ajuste de mensajes y refresco, 25 específicas
  comprobadas. TypeScript, lint y compilación de producción aprobados sin dependencias
  nuevas. Incluye regresiones de Trivial/historial, borradores, orden, reintentos,
  autenticación, espera privada y marcas separadas.

Comandos: `python -m pytest -q`, `python -m pytest -q tests/test_pasapalabra_rooms.py`,
`python -m pytest -q tests/test_pasapalabra_rooms_postgres.py tests/test_pasapalabra_postgres.py`;
frontend `node --test tests/*.test.mjs`, `npx tsc --noEmit`, `npm run lint`, `npm run build`.
Las carreras exigen `TEST_POSTGRES_URL`: base exacta `biogamed_pasapalabra_test`,
usuario `codex_test`; verifican conexión efectiva, crean esquemas únicos,
aplican migraciones y eliminan únicamente esos esquemas al terminar. Sin variable
se omiten, sin fallback a la base de aplicación. Nunca guardar credenciales en Git.

Demo verificada: volumen `biogamed_docente_demo_demo_data`, identidad efectiva
`biogamed_demo/demo_admin`, puertos limitados a loopback 13004/18004. Base habitual
sin migraciones ni escrituras. No se cambiaron firewall, router o puertos públicos.
Revisión visual real con dos cuentas y dos almacenamientos de autenticación
independientes por origen (`localhost` y `127.0.0.1`), en un solo equipo, dentro
del navegador integrado. Se permiten exclusivamente ambos hosts loopback en
desarrollo Next y CORS cuando el origen configurado ya es loopback.

Se comprobaron crear/copiar/unir, preparación, conflicto obsoleto y recuperación,
inicio, pregunta privada, correcciones propias, Enter, acierto/fallo/paso,
recorrido circular, recarga y borrador entre polls. Se interrumpió y restauró
solo backend de demo: avisos en ambos clientes, reloj continuo, borrador intacto
y recuperación automática. Partida 11 cerrada normalmente mediante 40 respuestas
en interfaz: 19–20; sesiones personales 22/23. Ambos clientes celebraron el
resultado; recargar resultado no repitió celebración. Partida 12 cerrada por
abandono de segunda cuenta, resultado sincronizado, sin celebración, sesiones
24/25. Historial de ambas cuentas revisado. Escritorio 1440×1000 y móvil 390×844
revisados; sin desbordamiento horizontal. Se corrigió el texto de abandono para
que quien abandona no lea que abandonó su rival.

Límites: no se probó en dos dispositivos físicos ni con lector de pantalla real.
La pausa de uso permitió comprobar caducidad natural y retorno tras login en
ambas cuentas, incluidos token ausente por otra pestaña y resultado recuperado. Conserva límites previos de
movimiento reducido: CSS y prueba automatizada, sin emulación nativa del ajuste
del sistema en el navegador integrado. No se atribuye esta revisión autónoma al usuario:
su aprobación anterior correspondía al pulido local; la aprobación posterior del conjunto se registra al final.

## Ajuste posterior de errores de unión y revisión de sala

Se mantiene la seguridad y selección del motor. La unión ahora distingue sala
caducada (`409 ROOM_EXPIRED`) y cancelada (`409 ROOM_CANCELLED`) de código
incorrecto/no disponible (`404 ROOM_UNAVAILABLE`). Una partida iniciada sigue
sin admitir acceso por código. Autenticación conserva sus contratos: 401
`Not authenticated` sin Bearer; 401 `No se pudieron validar las credenciales.`
con token rechazado. Cuenta creadora y sala llena siguen siendo 409, sin pedir login.

Se reprodujo en navegador el mensaje incorrecto «sesión caducada» al faltar
autenticación. Se verificó también un JWT firmado realmente vencido: ambos
casos conservan código y destino, y al volver necesitan confirmar la unión.
No se amplían permisos ni vigencia del token. CORS de ambos orígenes loopback
respondió 200 con origen exacto. La causa de la petición original del usuario
no puede conocerse retrospectivamente; se distinguen los casos comprobados.

Nueve pruebas backend de salas aprobadas, incluida matriz HTTP de cuenta propia,
tercero con sala llena, código incorrecto, cancelación, caducidad y ausencia de
autenticación. Cuarenta y dos frontend relacionadas, tipos, lint y build.
No requiere nuevas migraciones, dependencias ni repetir las carreras anteriores.
Detalles de evidencia visual, instrumentación temporal del JWT y límites en la
[documentación de interfaz](../../frontend/docs/pasapalabra-online.md#revisión-del-selector-sala-y-unión--5-de-noviembre-de-2026).
## Aprobación visual del usuario — 6 de noviembre de 2026

El usuario revisó personalmente la demo y aprobó el modo en línea, el selector
visual, la sala de jugadores, las correcciones de autenticación y la distribución
adaptable local/en línea. Autorizó el commit del conjunto pendiente. Esta revisión
se atribuye al usuario y se añade a la revisión autónoma descrita anteriormente;
se conserva también la atribución de su aprobación previa del pulido local.

Para preparar el commit solo se actualizó documentación: se reutilizaron las
comprobaciones vigentes descritas en este documento y en la revisión de
distribución, sin repetir pruebas ni modificar código o bases de datos. Se
mantienen las limitaciones de dos dispositivos físicos, lector de pantalla,
movimiento reducido nativo, zoom nativo al 200 % y teclado virtual móvil real;
la aprobación visual no se presenta como verificación técnica de esos casos.
