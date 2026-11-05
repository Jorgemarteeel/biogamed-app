# Interfaz local de Pasapalabra

## Presentación aprobada por el usuario (5 de noviembre de 2026)

La última respuesta resuelta se presenta en una tarjeta con jugador, casilla,
respuesta, acierto/fallo y solución. El resto se conserva íntegramente en un
plegable nativo, inicialmente cerrado, con contador. El orden global procede
de `resolution_order` de la API; no se deduce de los números de pregunta ni de
la posición de los jugadores. Los polls no limpian el borrador ni mueven el foco.
La leyenda describe los cinco estados con indicadores y texto, además del color.

El resultado final es el contenido principal: ganador del servidor en grande,
trofeo, desglose de ambos participantes y acciones separadas «Ver mi historial»
y «Preparar otra partida». Los roscos finales pasan a un plegable secundario;
las correcciones siguen disponibles. En empate se destacan ambos jugadores.
En abandono se usa una presentación sobria sin celebración y se explica el motivo.
El historial enlazado sigue siendo exclusivamente el del anfitrión.

La entrada animada y 28 piezas de confeti solo aparecen al observar una
transición de `RUNNING` a `FINISHED` normal. Su duración CSS es finita; el
indicador se apaga a los tres segundos. Un estado final repetido no la inicia,
y abrir o recargar un resultado antiguo tampoco. El confeti no intercepta
controles. `prefers-reduced-motion: reduce` elimina ambas animaciones y oculta
el confeti, conservando toda la información estática.

### Comprobaciones de esta mejora

- Automatizadas: 92 tests frontend aprobados (incluidos cinco nuevos de
  presentación); tipos, lint y compilación de producción correctos.
  Las 17 pruebas backend relacionadas aprobaron en SQLite en memoria: el caso
  nuevo demuestra que una pregunta 1 resuelta tras recorrer el rosco sigue siendo
  la última, incluso con timestamps iguales, y conserva el orden al recargar.
  No se repitió la batería completa del motor ni se cambiaron sus reglas.
- Navegador integrado real: sesión con la cuenta docente ficticia, escritorio
  1280×900 y móvil 390×844; leyenda, última corrección, plegable con Enter,
  conservación del borrador y foco, y ausencia de desbordamiento. Se verificaron
  anfitrión ganador (partida 5), invitada ganadora (7), empate (6) y abandono (2).
  Se observó confeti real durante la transición, su desaparición y una recarga de
  resultado antiguo sin repetición. La repetición del mismo estado final también
  está cubierta por tests. Las consultas periódicas cesan al finalizar.
- Movimiento reducido: el navegador integrado no expone emulación de preferencias
  CSS. Se revisó visualmente la misma variante estática forzando temporalmente
  su regla CSS a `@media all` **solo en la demo** (partida 8). Durante una transición
  real se comprobaron `animation-name: none` y `display: none` del confeti.
  Se restauró después el archivo original con `prefers-reduced-motion` y se
  comprobó esa regla en tests. No se afirma haber emulado la preferencia del SO.
- Aislamiento verificado antes de escribir: `biogamed_demo`, volumen
  `biogamed_docente_demo_demo_data`, puertos 13004/18004. Se reutilizaron las
  credenciales locales sin exponerlas. Solo se crearon partidas ficticias allí;
  no hubo escrituras en la base habitual ni migraciones. Demo actualizada y
  disponible. Pendiente auditoría con lector de pantalla y móvil físico.

El 5 de noviembre de 2026, el **usuario revisó personalmente y aprobó los ajustes visuales y la celebración**, y autorizó el commit de esta tarea. Se registra como revisión visual del usuario, distinta de las comprobaciones automatizadas y de la revisión del agente descritas arriba. No se modificó código tras esta aprobación: se reutilizan las 92 pruebas frontend, 17 backend relacionadas, tipos, lint y compilación aprobadas. Se conservan las limitaciones documentadas sobre movimiento reducido y la ausencia de emulación nativa de la preferencia del SO.

Para inspeccionar resultados estáticos: `/pasapalabra/5`, `/6`, `/7`
y `/2` en la demo. Al abrirlos no se reproduce la celebración, por diseño.

## Entrega de la interfaz jugable original

Disponible desde el selector de juegos y `/game?topicId=…&mode=PASAPALABRA`.
La preparación consulta disponibilidad académica de la modalidad y valida la
selección mediante `/pasapalabra/preparations`. No reduce las 40 preguntas ni
relaja filtros. El invitado introduce un nombre; la cuenta autenticada es el
anfitrión. Los 20 números de cada rosco no representan letras.

Inicio y acciones conservan un UUID y el mismo cuerpo mientras un envío quede
sin confirmar (incluidos red, timeout y HTTP 5xx). Un bloqueo inmediato con ref
evita doble clic antes de que React renderice. Tras 409 se vuelve a consultar
estado y no se aplica automáticamente la acción a la nueva pregunta.
La preparación permite repetir la consulta de disponibilidad tras errores.

La ruta persistente `/pasapalabra/{id}` recupera por GET; también hay enlaces
desde el historial. Consultas secuenciales cada segundo, sin solaparse entre sí,
con limpieza al desmontar y protección frente al montaje doble de StrictMode.
El servidor gobierna reloj, turnos y corrección; la representación local deriva
de `server_now`, `turn_deadline_at` y tiempo monotónico (`performance.now`).
Las versiones menores y las fechas anteriores de una misma versión se descartan.
Volver al foco o cambiar visibilidad provoca consulta inmediata. El reloj no
se pausa al perder conexión. No se han modificado motor, API ni migraciones.

El borrador permanece si la pregunta conserva participante y número. Cambiar de
pregunta lo limpia; los polls no enfocan elementos. El campo queda de solo
lectura durante un envío, evitando perder el foco al responder con Enter.
Las correcciones visibles proceden exclusivamente de `resolved`; no se descargan
soluciones futuras. No se añade pausa para mostrar corrección.

Escritorio: dos roscos con controles centrales. Móvil: pregunta, controles y
resumen de ambos relojes antes de los roscos. Los nodos son informativos, sin
navegación arbitraria; usan número, símbolo y nombre de estado. Una lista
equivalente para lectores de pantalla describe todas las posiciones. Los relojes
no son regiones live. No hay animaciones del rosco y el selector respeta movimiento
reducido. Abandono requiere seleccionar explícitamente al participante y confirmar
que el rival ganará; recargar no abandona. El resultado muestra ambos desgloses,
motivo y enlaces al historial propio y a preparar otra partida.

## Verificación del 5 de noviembre de 2026

Tests de interfaz cubren banco insuficiente, inicio con doble clic y reintento,
recuperación, conservación del borrador, orden de estados, reloj, Enter, paso,
permiso denegado, pérdida de red, HTTP 500, conflicto 409, abandono y empate.
Se ejecutan con `node --test tests/pasapalabra.test.mjs`; regresiones frontend
con `node --test tests/*.test.mjs`. Tipos, lint y build se comprueban en un
contenedor separado con las dependencias existentes. El build necesita acceso
a la fuente Geist de Google ya usada por el proyecto; sin red falla por esa
descarga, no por código de Pasapalabra. No se instalaron dependencias.
Resultado: 87 tests de frontend aprobados (nueve nuevos), lint sin errores,
TypeScript y compilación de producción aprobados. Se detectó y corrigió durante
la compilación un guard de montaje del refresco posterior a un conflicto.

Demo: contenedores `biogamed_docente_demo-*`, volumen
`biogamed_docente_demo_demo_data`, conexión efectiva `biogamed_demo`, frontend
13004 y API 18004 verificados antes de escribir. Se reutilizó la credencial
docente local sin exponerla. Se usó el banco ficticio existente de temática 6.
En navegador integrado se verificaron banco insuficiente (temática 1), preparación,
inicio del enfrentamiento 2 / sesión 13, acierto con Enter, foco, borrador entre
polls, paso, fallo, turno, recarga, confirmación y resultado por abandono.
Escritorio y móvil 390×844 revisados visualmente; sin desbordamiento horizontal.
Por HTTP real se repitieron inicio y respuesta con sus mismos UUID: una sola
partida 3 / sesión 14 y una sola respuesta; se cerró por abandono. Las dos
participaciones ficticias quedaron excluidas de mejores marcas.

Límites: salas en línea pendientes. Los borradores y UUID de acciones no
confirmadas viven en la pestaña; recargar recupera el estado de servidor,
pero descarta el texto no enviado. La prueba visual no sustituye una auditoría
con lector de pantalla físico ni una prueba con dispositivo móvil real.
No se repitió la batería del motor; no hubo escrituras en la base habitual.
