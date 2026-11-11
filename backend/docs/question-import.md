# Importación docente de preguntas

Entrega revisable del 11 de noviembre de 2026. Sin commit ni push.

## Flujo y formato

Desde la gestión de una categoría, abrir **Importar preguntas**. La jerarquía es
la de la ruta; elegir juego y una temática existente por nombre. Descargar la
plantilla vacía, seleccionar archivo, validar, revisar resumen/errores/vista
previa (10 registros por página) y confirmar explícitamente el lote completo.
Cambiar archivo, juego o temática elimina la validación. No hay importación de
TXT/HTML ni creación de jerarquías, actualización o sustitución del banco.

CSV UTF-8 (BOM admitido), separador `;`, comillas `"` y escape `""`, saltos de
línea dentro de celdas entrecomilladas. Cabeceras exactas y únicas, sin columnas
ajenas. No se adivinan codificaciones o separadores. Se rechazan caracteres
nulos, UTF-8 inválido, estructuras incorrectas, archivos vacíos, más de 500
registros o más de 2 MiB; no hay truncamiento. Registro 1 es la cabecera: los
números de errores son registros CSV, no líneas físicas cuando hay celdas multilínea.

- Trivial: `enunciado;opcion_a;opcion_b;opcion_c;opcion_d;correcta;dificultad`.
  Obligatorios todos excepto dificultad. Correcta A–D, convertida a índice 0–3.
- Pasapalabra: `enunciado;letra;solucion;alternativas;dificultad`.
  Alternativas y dificultad opcionales. Alternativas: una por línea dentro de
  una celda; vacío significa ninguna. Se mantienen los máximos de 30 alternativas
  y 255 caracteres por respuesta, opciones/solución y demás reglas de los esquemas.
- Dificultad vacía = desconocida; solo se admiten 1–4 cuando está asignada.
  No se infiere clasificación ni dificultad. Pasapalabra conserva la validación
  de empieza/contiene: para contener, el enunciado comienza por «Contiene la letra…».
  Se reutiliza la normalización actual de respuestas, con ñ distinta de n.

## API, consistencia y permisos

Prefijo: `/subjects/{subject_id}/blocks/{block_id}/categories/{category_id}/imports`.
Todos los endpoints exigen rol vigente `teacher` o `admin`; no hay alcance por
matrículas/grupos. Se valida la jerarquía completa y la temática existente.

- `GET /template?mode=TRIVIAL|PASAPALABRA`: descarga autenticada de cabeceras con
  BOM, nombre fijo seguro, sin preguntas de ejemplo ni tokens en URL.
- `POST /validate`: multipart `file`, `mode`, `topic_id`. Sin inserciones.
  Devuelve total, número de registros con campos válidos, errores por registro
  y campo, vista previa y `proof` solo si no hay errores. Las filas con campos
  válidos pero duplicadas siguen siendo errores y bloquean el lote.
- `POST /confirm`: mismos campos y archivo, `proof` y `operation_id` UUID.
  Devuelve `count` y `question_ids`. 401 sin sesión, 403 sin rol, 404 para destinos
  inexistentes/fuera de jerarquía, 413 por límites, 422 por CSV/comprobante
  inválido y 409 por caducidad, duplicados nuevos o reutilización incompatible.

El comprobante HS256 tiene propósito específico, usuario, SHA-256 de los bytes
originales, IDs de todos los destinos, juego y caducidad de 15 minutos. No puede
usarse como token de acceso. Confirmar vuelve a verificar firma, correspondencia,
rol, destinos, parser, esquemas y duplicados; no confía en la vista previa enviada
por el navegador. No se persisten archivos ni validaciones.

Huella de duplicado: categoría y temática de destino, juego, enunciado, dificultad,
opciones ordenadas e índice correcto, letra, solución y alternativas. Unicode NFC
y finales de línea se normalizan; no hay comparación aproximada ni eliminación
de tildes del enunciado. Alternativas usan previamente el validador existente;
null y lista vacía equivalen a ausencia. Cambiar opciones, solución o dificultad
crea una versión diferente. Incluye registros retirados, sin omitirlos ni
reactivarlos. Se identifican registros del archivo y IDs existentes afectados.

Las importaciones bloquean la categoría y vuelven a consultar duplicados después
de adquirir el bloqueo. La creación manual y edición de preguntas de categoría
usan el mismo bloqueo, manteniendo sus políticas anteriores: no se prohíben sus
duplicados. Si la creación manual equivalente confirma primero, la importación
rechaza; si la importación confirma primero, la creación manual posterior sigue
siendo admisible. No se promete unicidad universal del banco.

Construcción compartida `build_question`, sin commit. Creación manual conserva
su commit individual; el lote inserta todas sus preguntas y el recibo en una
transacción. Un fallo tras flush revierte ambos. No se modifican preguntas,
estados, respuestas, sesiones o copias previas; no hay reconstrucción histórica.

Recibo por cuenta/UUID, huella de archivo/destinos y lista de IDs, con fecha.
El mismo UUID y contenido recuperan el resultado sin insertar de nuevo, también
tras caducar la validación si ya existe recibo, verificando firma/correspondencia
y permisos actuales. Otro contenido con el UUID devuelve 409. El cliente impide
doble envío y conserva el UUID/comprobante al perder la respuesta para reintentar
Confirmar. Una recarga descarta el archivo y estado del formulario: no hay
recuperación automática del lote en interfaz; una nueva validación detectará los
duplicados si la operación anterior había confirmado. No se pierden los recibos
servidor y no se duplican preguntas por esa vía.

## Migración, demo y comprobaciones reales

Migración aditiva `d53e62f74085`, desde `c42d51e63f74`: únicamente tabla
`question_import_receipts`. Downgrade automático bloqueado para conservar recibos.
Ensayada en esquemas nuevos de `biogamed_pasapalabra_test` / `codex_test`.

Demo verificada: `db/biogamed_demo`, clúster `7703905352215838755`. Backend detenido
para copia completa `pg_dump -Fc`, fuera del repositorio, en el directorio privado
`Documents/BioGaMed-backups`. Archivo `demo-before-question-import-20261111-111040.dump`,
verificado con SHA-256 y `pg_restore --list`, restaurado realmente en la base
nueva `biogamed_import_rehearsal_20261111_111040`. Ensayo correcto antes de migrar
la demo, con 5 usuarios, 673 preguntas, 56 sesiones y 328 respuestas conservados.
Revisión final de demo `d53e62f74085`. No se migró ni escribió en la habitual.

Pruebas: nueve casos nuevos SQLite, 82 regresiones de creación/edición vigentes,
y cuatro comprobaciones PostgreSQL real (migración, idempotencia simultánea,
importaciones distintas y creación manual concurrente). Incluyen rollback tras
inserción, ambas modalidades, CSV español/multilínea/comillas, límites 500/501,
2 MiB excedidos, duplicados retirados, versiones diferentes, comprobantes
alterados/caducados, rol vigente, administrador y conservación literal de preguntas,
sesiones y respuestas. No se repitieron las 82 regresiones tras ampliar solo las
pruebas nuevas. Aviso existente de TestClient/httpx, sin dependencias modificadas.
Frontend: 17 pruebas relacionadas; tipos, lint y compilación aprobados. Sin pruebas
de carga. La comparación de duplicados carga el contenido del banco de destino
filtrado por categoría/temática/juego; no se ha medido rendimiento con bancos muy
grandes. El límite de archivo se verifica tras recibir multipart; no es una cuota
ni un límite de tráfico de un proxy.

Navegador integrado: escritorio 1366×768 y móvil 390×844, cuenta administradora
ficticia existente. Plantilla real descargada e inspeccionada (BOM y solo cabeceras).
Validación y confirmación de ambos juegos; revisión de solución/alternativas,
selección por teclado, vista adaptable sin desbordamiento horizontal observado
y rechazo de la segunda validación duplicada. La paginación se verificó con prueba
frontend de once filas; no se importó un lote grande en navegador. No es una
auditoría completa con lectores de pantalla o dispositivos físicos.

Actividad de revisión: solo dos preguntas nuevas, **674 (Trivial)** y **675
(Pasapalabra)**, categoría 5 «DEMO · Validación visual», temática 1 de demostración.
Los enunciados contienen `DEMO CSV 20261111`. No se cambiaron roles, cuentas,
clasificaciones ni registros anteriores. Conservadas para revisión del usuario.

Revisar en <http://localhost:13004/gestion/asignaturas/1/bloques/1/categorias/5>,
con una cuenta docente/administradora de demo, abriendo Importar preguntas.
Pendiente de aprobación visual del usuario. Sin staging, commit ni push.


## Ajuste de presentación y diagnóstico de recuperación

La barra compacta Crear pregunta / Importar preguntas mantiene ambos componentes
montados y oculta el inactivo: alternar conserva texto, archivo, destinos y
validación sin guardar automáticamente. La importación carga las temáticas al
abrirse, ofrece estados de carga/vacío/fallo y Reintentar solo ante fallo; utiliza
el selector Radix compartido. Tres secciones en una pantalla separan destino,
archivo e instrucciones del juego, y validación/vista previa/confirmación. Input
nativo transparente sobre el botón Seleccionar CSV, con foco visible, nombre
separado y límites permanentes. No cambian API, modelos, migraciones ni permisos.

Comprobaciones de este ajuste: 19 pruebas frontend relacionadas, tipos y lint.
Revisión real en navegador integrado 1366×768 y 390×844: borrador manual y archivo
conservados al alternar, selección por teclado, Escape, menú de temáticas, CSV
con duplicado 674 y vista previa válida SIN GUARDAR, sin nuevas confirmaciones.
Fallo real de carga provocado deteniendo brevemente SOLO el backend de demo:
mensaje y Reintentar visibles; backend reiniciado y reintento correcto. No se
simuló ese fallo modificando respuestas del servidor. Sin desbordamiento horizontal
observado. No es auditoría completa de lectores de pantalla o dispositivos físicos.
Se reutilizan las comprobaciones del servicio y migración vigentes.

Carencia comprobada de recuperación: TestClient aislado confirma un lote y luego
se ignora esa respuesta; una nueva validación del mismo CSV devuelve duplicado y
ningún comprobante. El comando original sí recupera el recibo sin duplicar.
Prueba frontend adicional: tras una respuesta perdida el formulario actual retiene
la operación; una instancia nueva (recarga) carece de archivo, comprobante e ID y
no consulta ningún recibo. En navegador también se comprobó que recargar borra el
contexto del formulario. Estas evidencias NO son una recuperación completa de
extremo a extremo en navegador: no se confirmó ningún lote nuevo en la demo.

Por tanto, el docente NO puede recuperar el resultado desde la interfaz después
de recargar en ese escenario. Puede consultar el listado, pero volver a validar
no recupera el recibo. No se implementa una solución nueva en este ajuste; queda
por acordar un recorrido explícito de recuperación antes de ampliar el alcance.
Sin nuevas preguntas ni cambios de cuentas/roles, sin escrituras en la habitual,
sin migraciones adicionales, staging, commit ni push.


## Cierre de cabeceras y recuperación tras recarga

Cabeceras estrictas: los errores distinguen obligatorias ausentes, desconocidas y
repetidas, y recomiendan descargar la plantilla del juego seleccionado. Se muestran
como texto React, no HTML. Como máximo se enumeran 12 nombres por tipo, de 80
caracteres cada uno, con indicador de truncamiento; los controles se representan
mediante texto escapado. No se reconoce formato por nombre ni se convierten
exportaciones de estadísticas.

`GET .../imports/receipts/{operation_id}` exige usuario vigente docente/admin,
valida la jerarquía y busca por **propietario autenticado + UUID**. Solo devuelve
`status:confirmed,count` cuando los IDs del recibo existen en esa categoría;
recibo ausente, ajeno o de otro destino devuelve `status:unknown`, indistinguible.
No expone IDs de preguntas, cuentas ni contenido. Cabecera `Cache-Control:no-store`.
La consulta no bloquea la categoría ni crea preguntas; un recibo de una transacción
sin commit todavía no es visible y NO implica fracaso. Si herramientas externas
alterasen la categoría de esas preguntas, no se puede acreditar el destino original
con el esquema existente: se conserva incertidumbre; no se reconstruye contexto.
No hay migración nueva ni modificación de la migración aplicada.

Antes de enviar Confirmar, la interfaz identifica la cuenta y guarda en
sessionStorage de esta pestaña exclusivamente versión, ID de cuenta, asignatura,
bloque, categoría y UUID de operación. Una referencia por cuenta/categoría: conserva
la última confirmación enviada explícitamente, no un historial navegable. No guarda
CSV, preguntas, soluciones, comprobante ni token. Almacenamiento bloqueado impide
ese envío con explicación; datos inválidos al recuperar se señalan sin consultar
recibos. No se borran referencias por fallos transitorios. La referencia no sirve
para autorizar: el servidor verifica propietario, rol y destino otra vez.

Al volver a la categoría se consulta una vez, aunque el formulario esté cerrado.
Una respuesta confirmada muestra cantidad y acceso al listado; ausencia de recibo,
conexión fallida, sesión caducada y permisos perdidos tienen mensajes distintos.
Consultar de nuevo es explícito, sin polling, reenvío ni nueva operación. Se vuelve
a verificar identidad antes de mostrar el resultado para descartar respuestas de
una cuenta anterior. Una referencia propia conocida sigue siendo consultable tras
caducar el comprobante. Cerrar la pestaña/limpiar su almacenamiento elimina esta
ayuda local; no los recibos de servidor. El archivo y la validación siguen siendo
borradores volátiles y no se restauran.

Pruebas vigentes de este cierre: 14 casos SQLite de importación (incluidos los
nuevos diagnósticos y consultas), 5 PostgreSQL real (incluida consulta mientras la
confirmación original tiene inserciones sin commit), 11 pruebas frontend de
importación/recuperación y 7 regresiones de retirada; tipos, lint y compilación.
El caso API confirma, ignora la respuesta, consulta desde un nuevo contexto y
verifica ausencia de nuevas inserciones; la instancia frontend nueva recupera
solo desde referencia mínima. Se cubren recibo ajeno, rol perdido, cuenta cambiada,
almacenamiento bloqueado/inválido y consultas repetidas. Sin pruebas de carga.

Revisión real integrada en escritorio 1366×768 y móvil 390×844: recibo preexistente
confirmado tras recargar, incertidumbre ante UUID sin recibo y Consultar de nuevo
con Enter. Se utilizó una página temporal de prueba SOLO en el contenedor frontend
de demo para colocar referencias existentes en sessionStorage mediante botones,
sin confirmar importaciones; eliminada al acabar, fuera del repositorio. No se
simuló una nueva pérdida de respuesta de confirmación en navegador ni se crearon
preguntas. El intento visual del CSV de cabeceras quedó bloqueado unos 20 minutos
por el selector integrado y terminó en sesión caducada: esa revisión visual queda
pendiente, aunque cada diagnóstico está comprobado mediante pruebas API. La sesión
se recuperó y la demo quedó operativa. Sin escrituras habituales, migraciones,
staging, commit ni push; siete commits anteriores conservados.


### Revisión visual de cabeceras completada

11 de noviembre de 2026: se cierra el pendiente visual descrito arriba. Sesión
renovada con la cuenta administradora ficticia existente. Tres CSV ficticios de
15, 83 y 81 bytes, fuera del repositorio: obligatorias ausentes, columna desconocida
`estadistica` y cabecera repetida `enunciado`. Solo se pulsó Validar sin guardar.
Cada mensaje identifica lo que debe corregirse y recomienda descargar la plantilla.
Los tres se observaron a 1366×768 y 390×844, sin desbordamiento horizontal; cada
error es un nodo `role=alert`, añadido tras validar. Se verificó la semántica de
anuncio accesible, no audio de un lector de pantalla externo. Validación también
activada con Enter. Sin necesidad de corregir código, se reutilizan las pruebas.

Diagnóstico del selector integrado: se recibe `filechooser` mientras el clic sobre
el input sigue pendiente. Esperar a que termine ese clic antes de asignar el archivo
puede mantener la espera circular. Se separaron recepción del evento y asignación
mediante `setFiles`, esperando el clic al final; las tres selecciones terminaron en
esta sesión sin el bloqueo anterior ni caducidad. No se usó control de escritorio.
Sin confirmaciones, nuevas preguntas, cambios de roles ni migraciones. Demo preparada
con el último error visible para aprobación del usuario. Capturas y archivos de
prueba permanecen fuera del repositorio; siete commits y cambios pendientes intactos.


## Aprobación del usuario

El 11 de noviembre de 2026 el usuario aprueba la entrega y presentación completas,
incluida la revisión visual final de cabeceras, y autoriza su commit local. Se
conservan las limitaciones documentadas. Comprobaciones vigentes reutilizadas, sin
nuevas migraciones ni escrituras en bases de datos para el cierre; sin push.
