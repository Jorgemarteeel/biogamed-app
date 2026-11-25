# Contenidos por edición académica

## Uso docente

Abre [Contenidos en revisión](http://localhost:13020/gestion/contenidos) desde el menú de cuenta, Gestión docente → Contenidos. Selecciona asignatura y curso. Puedes crear ambos desde esa pantalla. Las temáticas se crean previamente en la edición. El contexto de asignatura y año permanece en una banda visible al desplazarse por la edición.

Las preguntas de una temática pueden ser de Pasapalabra o de Trivial de tablero. El único nivel de dificultad es 1–4. Trivial de tablero utiliza enunciado, respuesta de referencia y referencia opcional a apuntes. Su tipo de casilla se asigna en la configuración del tablero a la temática, sin inventar asociaciones por nombres.

Los iconos se suben como PNG, hasta 512 KiB y 1024 × 1024 píxeles. Se conservan en la temática de esa edición y se pueden sustituir. No se aceptan SVG. La vista permite consultar la imagen guardada.

## Dos accesos, un procesamiento CSV

- Sin temática seleccionada, pulsa Importar CSV en esta edición. La plantilla incluye tematica.
- Con temática seleccionada, pulsa Importar CSV en esta temática. La plantilla omite tematica y el servidor fija el destino.
- Ambos usan el mismo servicio, límites y validaciones. Asignatura y curso proceden de la pantalla. Máximo 500 filas y 2 MiB, UTF-8 (BOM admitido), separador de punto y coma.
- Campos comunes de fila: juego, dificultad y enunciado. Trivial de tablero usa respuesta_referencia y referencia_apuntes opcional. Pasapalabra usa letra, solucion y alternativas opcionales separadas por saltos de línea dentro de una celda entrecomillada. Los campos del otro juego quedan vacíos.
- Validar no guarda. La vista previa muestra contexto, grupos por temática y juego, errores por fila y una tabla paginada.
- Confirmar revalida destinos, contenido y duplicados bajo el bloqueo compartido con la creación manual. Se confirma todo el lote junto con su recibo, o no se inserta nada. Los duplicados exactos del formato y temática, incluidas preguntas retiradas, bloquean el lote. No se fusionan preguntas por similitud.
- El comprobante caduca a los 15 minutos y vincula actor, archivo, edición, temática fijada y las temáticas resueltas. La clave de operación reutilizada con otro contenido se rechaza. Un reintento idéntico recupera el recibo.
- Antes de confirmar se guarda en sessionStorage de la pestaña únicamente el identificador de operación y los identificadores de edición y temática, bajo una clave del usuario autenticado. No se guardan CSV, soluciones, comprobantes ni tokens. Tras recargar se consulta el recibo del propietario mediante una petición autenticada. La consulta nunca reenvía la importación. Si el recibo aún no existe, se conserva la incertidumbre y se ofrece Consultar de nuevo. Un fallo transitorio conserva la referencia. Si no puede guardarse la referencia antes del envío, se informa de que la importación no se ha enviado.

## Recorrido preparado en 13020

La revisión creó la asignatura ficticia **Inmunología · revisión por ediciones** (ID 3), las ediciones **2026–2027** (ID 6) y **2027–2028** (ID 7). En la primera están **Tejidos linfoides** (ID 1) e **Inmunidad innata** (ID 2). En la segunda existe otra **Tejidos linfoides** (ID 3). Se verificaron iconos distintos, Linfocito en la primera y Macrófago en la segunda, reutilizando recursos existentes como datos sintéticos de revisión.

1. Selecciona la asignatura y 2026–2027. Elige Toda la edición y abre Importar CSV en esta edición.
2. Descarga su plantilla y selecciona [edicion-mixta.csv](examples/edition-content/edicion-mixta.csv). Tiene cuatro filas, dos temáticas y ambos juegos. Valida, revisa los cuatro grupos y confirma cuando quieras incorporar los ejemplos.
3. Selecciona Tejidos linfoides. Abre Importar CSV en esta temática y selecciona [tematica-mixta.csv](examples/edition-content/tematica-mixta.csv). Contiene dos filas y omite la columna temática. Revisa y confirma.
4. Consulta las preguntas en cada temática. En la configuración del tablero, Tipo de casilla 3 (código SPLEEN) está vinculado expresamente a Tejidos linfoides como ejemplo sintético. Las otras casillas pueden quedar pendientes y guardarse así.
5. Cambia al segundo curso para contrastar la temática homónima. El primer curso conserva su contenido y su icono.

Los archivos entregados llevan textos distintos de los lotes utilizados en el ensayo inicial. Se reservaron para revisión manual; en la comprobación de cierre sus preguntas ya están presentes en 13020. Volver a validarlos muestra duplicados; no se omiten ni sobrescriben.

## Conservación e integración posterior

La migración aditiva 26ea7dac0318 parte de 15df6c9be207. Añade edición e icono a temáticas, edición a preguntas, restricciones de pertenencia y configuración temática del tablero por edición. Adapta la restricción del formato abierto para conservar la variante histórica con banco y aceptar la nueva con temática de edición. No asigna ni convierte preguntas antiguas.

El contenido anterior queda con edición vacía. Se localiza mediante Preguntas sin curso asignado, con identificadores y relaciones conservadas. Su revisión y asignación requieren una decisión explícita, fuera del traslado automático. Historiales, copias de preguntas, respuestas y sesiones no se reescriben.

Pasapalabra ya utiliza la edición de la matrícula habilitada; véase [recorrido y verificación](pasapalabra-enrollment.md). Las consultas de los formatos anteriores siguen excluyendo preguntas de edición. No se habilitan partidas nuevas del Trivial de tablero.

## Evidencia y límites

- PostgreSQL desechable: cadena completa desde vacío, ampliación desde el esquema anterior con registros sintéticos, conservación de preguntas y temáticas antiguas y restricciones de pertenencia. Se repitieron las pruebas de matrículas concurrentes.
- SQLite en memoria: 16 pruebas de contenido, altas y matrículas. Otro grupo de 38 regresiones de importación, permisos, filtros de juego y Pasapalabra. Estos grupos solapan algunos casos.
- Frontend: tipos, compilación, lint y prueba del componente para ambos accesos CSV y el aviso de cambio de destino con borradores.
- Navegador integrado con docente: creación de asignatura, edición y dos temáticas, subida y previsualización de icono, validación y confirmación del lote de edición con cuatro preguntas. Se observaron listados de temáticas y el contexto del segundo curso.
- API autenticada en 13020: importación desde temática (dos preguntas), repetición del recibo, segunda edición con temática homónima, creación, edición, retirada y reactivación de su pregunta, aislamiento del primer curso y de sus iconos, configuración parcial, cobertura y rechazo de estudiante.
- Un diálogo nativo bloqueó la primera revisión y se sustituyó por un aviso integrado. La revisión posterior completó el importador temático y los formularios manuales en navegador. Siguen fuera de la evidencia un lector de pantalla, zoom real al 200 % y una auditoría exhaustiva de teclado de todas las acciones.
- No hay pruebas de carga. El catálogo de asignaturas y ediciones se consulta en páginas de 100 para completar los selectores. La edición carga su lista de temáticas e iconos. Las preguntas tienen paginación de servidor y la vista previa CSV está limitada a 500 filas.
- Solo se actualizó 13020. Se guardó una copia privada de su base antes de aplicar la migración. No se tocaron habitual ni demo 13004. La migración sigue pendiente en esos entornos.
## Cierre de recuperación y revisión del importador temático

Se creó un lote distinto en la carpeta privada de revisión, ensayo-recuperacion-tematica.csv, y otro con un error de nivel. Los CSV finales de esta guía se conservaron sin editar ni confirmar.

En el navegador integrado se realizaron estas comprobaciones con la cuenta docente ficticia.

- Se importaron dos preguntas en Tejidos linfoides de 2026–2027, una por juego. Después de confirmar se recargó la página y se recuperó el recibo original con su cantidad y destino. Consultar de nuevo mantuvo el resultado. Ver preguntas importadas abrió el listado con ambas.
- Se crearon desde el formulario una pregunta abierta y otra de Pasapalabra. Se comprobó el cambio entre respuesta de referencia y referencia a apuntes, frente a letra, solución y alternativas. Se editó y retiró la pregunta abierta del primer curso. La pregunta de 2027–2028 continuó activa y con su texto anterior.
- La tabla del primer curso mostró el icono disponible en Bazo, casillas sin configurar con icono pendiente, y recuentos vacíos de sus niveles sin preguntas. El segundo curso mantuvo su configuración independiente.
- En una ventana estrecha de 355 píxeles CSS efectivos se comprobó el selector por Enter, un nombre de archivo largo legible, errores que bloquean la confirmación y el botón de confirmar visible con foco. Se usó Tab entre los controles. La página no desbordó horizontalmente y las tablas conservaron su desplazamiento propio. El lote de vista previa móvil se dejó sin confirmar.
- Se corrigieron el singular de los mensajes y la etiqueta Nivel de dificultad del error.

Pruebas nuevas y focalizadas aprobaron dos casos backend de gestión y recuperación, y cuatro pruebas frontend del flujo, la recarga y el almacenamiento inválido o no disponible. El caso backend simula una respuesta perdida descartando la respuesta de confirmación y comprueba consulta previa, consultas repetidas, reintento sin inserciones adicionales, autorización y propietario del recibo. El navegador comprobó la recarga y recuperación, sin simular un corte de transporte. Pasaron tipos, lint y compilación. Se reutiliza la evidencia PostgreSQL y de regresiones anteriores.

No se añadieron migraciones para esta recuperación. Se actualizaron únicamente las imágenes de aplicación de 13020. Las cuentas, roles, contraseñas y la demo 13004 permanecieron conservados. La pregunta manual abierta de ensayo quedó retirada y la de Pasapalabra activa, como evidencia de revisión.

## Etiquetas docentes del tablero y contenido anterior

La tabla usa Tipo de casilla 1–5, en el orden de los códigos LYMPHOCYTE, MACROPHAGE, SPLEEN, FLASK y DNA. Solo cambia la presentación: se conservan códigos, asignaciones, iconos y recuentos. Preguntas sin curso asignado identifica el contenido anterior aún sin vinculación a un año académico; su consulta y sus relaciones no cambian.

Comprobación de este ajuste en 13020: navegador docente con los cinco nombres nuevos; Tipo de casilla 3 conserva Tejidos linfoides e icono disponible (niveles 1–4: 2, 3, 0, 0 en el catálogo revisado). Ver preguntas sin curso asignado consulta correctamente y devuelve cero en estos datos sintéticos. Pasaron las cinco pruebas frontend focalizadas, tipos, lint y compilación. Solo se recreó el frontend de revisión; no se guardó configuración ni se modificaron datos.

## Comprobación de cierre del listado sin curso

El único filtro de /edition-content/legacy/pending es questions.edition_id IS NULL. Es global, sin depender de los selectores de asignatura, curso, temática, juego o estado activo. Incluye retiradas y todos los formatos; devuelve el total y páginas de 20 ordenadas por ID. No exporta soluciones. Una copia histórica dentro de una partida no es una pregunta del catálogo y no se incluye.

En 13020, una transacción SQL explícitamente de solo lectura encontró 17 preguntas, todas con edición (16 en la edición 6 y una en la 7), ninguna sin curso y una retirada. La API docente respondió total 0 e items vacío, coincidiendo con SQL. No se borró ni reasignó contenido para obtener este resultado. La prueba de migración conserva el contenido anterior con edición nula.

Se detectó además un defecto de paginación en la interfaz: cambiar de página vaciaba el listado sin consultar la siguiente. Se corrigió para consultar directamente el desplazamiento pedido y mantener la página anterior si falla. Se añade cobertura frontend de avance/retroceso y backend de 25 preguntas anteriores de distintos formatos y estados, excluyendo una con edición.

Verificaciones nuevas del cierre: tres pruebas backend aprobaron en un contenedor desechable sin red con SQLite en memoria; seis pruebas frontend aprobaron, incluidos los desplazamientos 0/20/0 del listado. Tipos y lint pasaron. Se reutilizan las pruebas PostgreSQL y la revisión visual documentadas; no se presenta SQLite como prueba de migración ni se repiten escrituras en 13020.

## Nombre del juego y compatibilidad

El juego de tablero se presenta como Trivial. Trivial individual identifica el cuestionario anterior de opciones. Se conservan question_type=INMUNOQUEST, los identificadores de reglas inmunoquest-*, clases, tablas y rutas /inmunoquest y /gestion/inmunoquest para interpretar registros y clientes existentes. No se convierten datos históricos. En el CSV mixto por edición, juego=Trivial crea exclusivamente una pregunta abierta (internamente INMUNOQUEST); INMUNOQUEST sigue admitido para CSV anteriores. El modo TRIVIAL de las API antiguas sigue significando cuestionario individual. La plantilla mixta usa las mismas cabeceras; los ejemplos nuevos muestran Trivial.
