# Gestión común de preguntas e InmunoQuest

> Estado posterior: el [motor del manual](inmunoquest-rules.md), su persistencia interna y la [preparación automática de mazos](inmunoquest-decks.md) están implementados internamente. No hay partida pública ni esta gestión habilita el inicio.

> La ampliación interna de [cartas y evaluación del lector](inmunoquest-cards.md) conserva esta gestión y sus contratos; todavía no incorpora una pantalla jugable.

Entrega desarrollada sobre main/a2119a1, conservando los seis commits anteriores. No hay partidas del manual ni retirada del cuestionario individual.

## Organización y acceso

Entrada docente principal: **Gestión de preguntas**, `/gestion/preguntas`. Un listado paginado (20 por página) reúne preguntas abiertas de InmunoQuest y Pasapalabra. También permite consultar el formato anterior de opciones. Asignaturas, bloques y categorías se mantienen y se administran desde un enlace secundario; ya no es obligatorio recorrerlos para gestionar preguntas. `/gestion/inmunoquest` y las rutas de categoría utilizan el mismo componente de gestión, no catálogos independientes.

Filtros opcionales: formato, asignatura, bloque, categoría, dificultad, estado y clasificación (cualquiera/sin asignatura/sin categoría). Banco solo se admite con InmunoQuest. Consultar aplica filtros, conservados en URL junto a la página. El servidor valida combinaciones: una categoría o bloque identificables resuelven sus ascendientes; un padre contradictorio se rechaza. Nunca se infieren relaciones por nombres.

Cada pregunta puede asociarse directamente a una asignatura, a un bloque sin categoría o a una categoría. Una categoría vinculada determina bloque/asignatura; una categoría sin bloque no permite inventar esa relación. Elegir solo asignatura no requiere crear bloques o categorías ficticios. El contenido sin asignatura sigue localizable. Las vinculaciones explícitas de categorías existentes actualizan las asociaciones demostrables de sus preguntas; se rechazan si contradicen una asignatura ya elegida.

Crear/editar e importar son paneles exclusivos; alternarlos conserva los borradores montados. Cambiar juego/destino del CSV requiere confirmar la pérdida del archivo/validación. Los destinos académicos muestran nombres y se consultan con paginación, incluyendo el valor seleccionado aunque no esté en la primera página. El formulario de opciones anterior se reutiliza dentro del gestor cuando existe su categoría, sin ampliar sus reglas.

## Campos y CSV

InmunoQuest conserva enunciado, respuesta de referencia (hasta 10000 caracteres), banco, nivel obligatorio 1–4 y referencia opcional a apuntes (hasta 120). No usa Topic, distractores o corrección automática. T1–T16 sigue siendo una referencia. Pasapalabra conserva letra, solución, alternativas y dificultad opcional; su temática continúa siendo necesaria para los bancos jugables actuales y no equivale a un banco de InmunoQuest.

Se reutilizan QuestionImportForm, el parser, validadores, comprobantes, bloqueo transaccional y recibos existentes. Solo CSV UTF-8 (BOM admitido), separador `;`, máximo 500 preguntas y 2 MiB. Plantillas sin ejemplos importables. Para abiertas:

```text
enunciado;respuesta_referencia;banco;dificultad;referencia_apuntes
```

Primeras cuatro columnas obligatorias. Banco por fila: Linfocito, Macrófago, Bazo, Matraz o ADN. Banco/nivel no se repiten como destinos de pantalla. Asignatura/bloque/categoría y la temática de Pasapalabra proceden exclusivamente del formulario. No se convierten DOCX ni se cargan las 600 preguntas reales.

Validar no escribe. Se conservan errores por registro/columna, vista previa paginada, confirmación explícita y transacción única de preguntas+recibo. Duplicados exactos bloquean el lote completo, incluso retirados, dentro del mismo formato y destino (asignatura/bloque/categoría/temática cuando corresponda); no se fusionan versiones ni se omiten filas. La creación manual conserva su política previa, pero comparte bloqueo con importación.

Comprobante firmado de 15 minutos: cuenta, huella del archivo, formato y destinos resueltos. Confirmar revalida permisos vigentes, contenido, destinos bajo bloqueo y duplicados. El mismo UUID/contenido devuelve el recibo anterior; otro contenido se rechaza. Categorías usan bloqueo de fila; sin categoría se conserva un advisory lock PostgreSQL compartido, intencionadamente más amplio que una asignatura. No es un límite distribuido ni una prueba de rendimiento.

Recuperación: sessionStorage guarda solo cuenta, UUID y IDs de destino. Asignaturas directas tienen claves distintas; no colisionan con el destino global. URL conserva el destino del panel de importación (`action`, `importSubject`, `importBlock`, `importCategory`, `importMode`). No se persisten CSV, preguntas, soluciones, comprobantes o tokens para recuperar. Tras recargar se consulta el recibo; nunca se reenvía el archivo. Ausencia de recibo es incertidumbre, no fracaso. Como antes, una reclasificación posterior de las preguntas puede impedir acreditar ese recibo en el destino original; no provoca inserciones ni atribuye resultados ajenos.

## API y privacidad

Todos los contratos de gestión requieren docente/administrador vigente; ámbito global, sin grupos, matrículas o propiedad docente. Estudiantes no obtienen soluciones ni respuestas de referencia. Catálogo y cobertura usan `Cache-Control: no-store`.

- `GET /questions/catalog`: `skip`/`limit` (máximo 100), `mode`, `subject_id`, `block_id`, `category_id`, `difficulty`/`difficulty_unknown`, `state`, `bank`, `classification`; devuelve `items,total,skip,limit`. Orden estable por ID.
- `GET /questions/destinations`: `kind=subject|block|category`, padres opcionales, `skip`/`limit`, `selected_id`; solo metadatos, con nombres de ascendientes y selección fijada fuera de página.
- `POST /questions/`: creación reutilizada con destino académico opcional.
- `PUT /questions/manage/{id}`: edición validada sin convertir formato; no altera copias históricas.
- `PUT /questions/manage/{id}/state`: retirada/reactivación.
- `/question-imports/template|validate|confirm|receipts/{UUID}`: importador común con destinos opcionales. Validate/confirm reciben archivo/formato/destinos como formulario; recibos reciben los destinos como parámetros de consulta.
- Rutas jerárquicas anteriores de creación, edición, estado e importación conservan sus contratos estrictos: el destino lo determina la ruta, no se admite en el JSON. La consulta abierta anterior es un adaptador al catálogo común.
- `GET /inmunoquest/coverage?subject_id=...`: asignatura explícita, veinte pares banco/nivel y sus cantidades; sin soluciones, IDs de cartas o selección individual.

## Disponibilidad automática

Cuenta únicamente abiertas activas, completas y pertenecientes a la asignatura elegida, incluyendo sus bloques y categorías. Excluye otras asignaturas y preguntas sin asignatura. Devuelve los veinte mazos aunque estén vacíos y el número de mazos sin preguntas. Cantidades mayores de treinta son válidas. No existen objetivos manuales, nombres/versiones de actividades ni selección de cartas. `can_start=false` siempre: disponibilidad no garantiza suficiencia pedagógica ni implementa la partida.

La futura creación de partidas congelará su contenido y preparará los mazos automáticamente. Se mantiene fuera de alcance: motor del manual, extracción/barajado, lector, evaluación, salas e historial de InmunoQuest.

## Migraciones y conservación

`b97a063b84c9` se mantiene sin reescribir: ya estaba aplicada en el entorno aislado. `c08b174c95da`, sucesora, añade a questions los FK opcionales `subject_id`/`block_id` con índices y completa solo cadenas reales pregunta→categoría→bloque→asignatura. No deduce nada desde Topic, texto o apuntes. El resto queda sin asignatura.

La sucesora elimina la tabla de configuraciones manuales, cuyos únicos consumidores eran el gestor pendiente, su API y pruebas. También se retiraron modelo/esquema y endpoints de actividades. No hay relaciones desde partidas o respuestas. La configuración interna y las copias del motor parcial anterior son otra cosa y se conservan. No se ofrece downgrade destructivo para descartar las nuevas asociaciones; ante incidentes se conserva la copia y se prepara una restauración aislada.

No se convierten, retiran ni borran preguntas existentes. Se conservan IDs, relaciones anteriores, cuentas, hashes, roles, preguntas, sesiones, respuestas, copias y contextos. Partidas/salas abiertas no cambian su selección. Pasapalabra y Trivial mantienen preparación y reglas existentes: la asignatura directa de este gestor todavía no sustituye la selección académica de partidas. Las nuevas preguntas de Pasapalabra sin categoría siguen accesibles por su temática; una preparación por asignatura directa será otra entrega.

## Comprobaciones — 17 de noviembre de 2026

- PostgreSQL 15 exclusivo: red interna propia, sin puertos, usuario/base sintéticos y tmpfs; identidad y cero tablas verificadas antes de migrar. Migraciones desde vacío y desde b97, cadenas válidas y categorías huérfanas, sin inferencia por nombres. Conservación de columnas anteriores y JSON históricos comprobada.
- 154 pruebas backend aprobadas en la ejecución principal (PostgreSQL y regresiones SQLite): formatos, filtros, jerarquía, destinos directos, CSV, atomicidad, permisos, recibos, recuperación, cobertura, ediciones y compatibilidad académica anterior. Se mantuvo el contrato estricto de las rutas anteriores.
- 46 casos adicionales aprobados: concurrencia PostgreSQL (incluida creación manual frente a CSV y doble envío con asignatura directa) y regresiones de copias, Pasapalabra, permisos y retirada. Cuatro verificaciones dirigidas posteriores confirmaron el destino resuelto de duplicados al indicar solo bloque, el reintento y la concurrencia por asignatura. Parte de la idempotencia ya tenía evidencia anterior; no son 200 casos nuevos diferentes. Aviso existente TestClient/httpx; no se actualizan dependencias.
- 39 pruebas frontend relacionadas aprobadas: filtros pendientes y URL, entrada de categoría al gestor común, exclusión de paneles y borradores, retirada, recibos por asignatura y recuperación tras recarga, navegación y menú. Tipos/lint/compilación de producción verificados; la compilación se repite solo tras cambios de código que la invaliden.

Entorno actualizado exclusivamente: `biogamed_iq_review_20261117`, http://localhost:13014/gestion/preguntas y API en localhost:18014. Base/revisión comprobadas antes de actuar; PostgreSQL conserva su volumen privado y no publica puertos. Copia completa privada fuera del repositorio, índice pg_restore y restauración real verificados en recursos propios; ensayo de la sucesora sobre esa restauración antes de aplicarla al entorno de revisión.

Comparación antes/después: 2 cuentas, 49 preguntas, 1 asignatura, 1 bloque, 1 categoría, 1 recibo y 0 partidas/0 respuestas. Campos anteriores y registros comparados mediante huellas sin publicar datos privados. Se asociaron 45 preguntas por relaciones existentes; 4 quedaron sin asignatura. Se retiró la única configuración manual sintética. No se crean preguntas durante esta actualización. HTTP autenticado docente/estudiante comprueba catálogo, cobertura, metadatos, CORS y rechazo de estudiantes: la cobertura de asignatura 1 reúne 3 abiertas y muestra 19 mazos vacíos, no las abiertas sin asignatura.

La demo de reunión, instalación habitual e instalación limpia no se migran ni se modifican. Sus servicios permanecen intactos. Fuentes e imágenes de revisión están separadas, con configuración privada y copia anterior conservadas fuera de Git.

## Cierre y revisión autenticada — 17 de noviembre de 2026

**Revisión aportada por el usuario:** listado, filtros visibles, edición y tabla de disponibilidad en navegador de escritorio. Confirmó 45 preguntas de la asignatura sintética y tres cartas de Matraz/nivel 2, con los otros 19 mazos vacíos. Es una revisión parcial de esos elementos, no una aprobación exhaustiva de todos los recorridos.

**Comprobaciones nuevas del agente en el navegador integrado:** sesión docente existente, escritorio con viewport efectivo de 1366×768 CSS y adaptación a 390 px CSS de ancho (altura observada alrededor de 845 px). Se revisaron:

- Selección por teclado en Radix, filtro pendiente sin consulta automática, aplicación explícita, banco vacío y mensaje recuperable. La disponibilidad de asignatura mantuvo las tres cartas de Matraz aunque el listado se filtrara por otro banco.
- Paginación del listado y conservación al recargar; filtros en URL. Seleccionar categoría completó sus ascendientes y limpiar solo la categoría mantuvo el bloque explícito. Menú compartido dentro del ancho móvil; Escape cierra y devuelve el foco.
- Formulario abierto de InmunoQuest: foco inicial, Tab/Shift+Tab entre campos, Guardar deshabilitado si falta contenido, borrador conservado al alternar con CSV. Formulario de Pasapalabra en móvil y edición/cancelación de la pregunta ficticia ID 7 sin guardar, con devolución del foco a Editar. No se enviaron formularios de creación o edición durante el cierre.
- Descarga real de plantilla InmunoQuest: solo cabeceras, sin ejemplos importables. Selección de archivos ficticios (incluida activación por teclado), error de cabecera ausente con recomendación de plantilla, error de registro 2/columna banco y vista previa válida de 12 filas en dos páginas, sin confirmar. El resumen usa role=status y el error de estructura role=alert; no equivale a probar un lector de pantalla.
- CSV de Pasapalabra: temática sintética elegida explícitamente y vista previa válida de dos filas, sin confirmar. Tras recargar se conservaron formato y destino en URL; no persistieron archivo ni comprobante y no se reenvió la importación.
- Sin desbordamiento horizontal de página en los estados medidos: escritorio innerWidth=1366/scrollWidth=1353; móvil innerWidth=390/scrollWidth=376. Se permite desplazamiento vertical de formularios y listado. Son tamaños y estados concretos, no una garantía para todos los textos, dispositivos o zoom.

**Defectos corregidos en este cierre:** formato anterior guardado en la URL al abrir CSV desde el filtro Pasapalabra; borradores y destinos compartidos entre editor e importador; controles externos utilizables mientras el CSV estaba ocupado; opciones académicas del contexto anterior durante una recarga de metadatos; selector interior de juego que podía contradecir el formato fijado por el gestor; pérdida del bloque al limpiar solo la categoría; anuncio prematuro de fallo de disponibilidad y foco al cerrar tras guardar. En servidor, el bloqueo de categoría refresca expresamente el objeto ORM antes de revalidar: una relación establecida por otra conexión no puede ocultarse detrás de una copia en memoria obsoleta.

**Automáticas nuevas:** 47 pruebas frontend relacionadas aprobadas, con ocho regresiones añadidas al conjunto anterior de 39. 70 casos backend dirigidos aprobados en PostgreSQL aislado y regresiones relacionadas, incluida categoría previamente cacheada modificada por otra conexión y reintentos/concurrencia de importación. No son 70 funciones nuevas. Tipos, lint sin avisos y compilación de producción aprobados después de los ajustes. Se reutilizaron las verificaciones previas de migraciones, conservación histórica, atomicidad, permisos y formatos; no se repitieron las suites completas de motores.

**Límites manuales:** no se pudo verificar zoom real al 200 %. Los atajos del navegador integrado no alteraron devicePixelRatio ni dimensiones observadas; CSS zoom permaneció en 1. No se sustituyó esta comprobación por cambiar el viewport. No se utilizó un lector de pantalla real ni un teléfono físico/teclado virtual. El diálogo nativo de descarte no pudo inspeccionarse en todas sus ramas mediante la herramienta (una llamada quedó bloqueada hasta resolver el diálogo); se comprobó el cierre y retorno del foco y se conserva la cobertura automática de cancelar sin descartar. No se afirma conformidad completa de accesibilidad ni capacidad bajo carga.

Durante este cierre solo se actualizaron las imágenes de frontend/backend del entorno aislado. No se aplicaron migraciones adicionales ni se confirmaron importaciones. El cotejo final de recuentos y huellas coincidió con el estado al comenzar el cierre: todas las filas previas permanecieron iguales (49 preguntas, 2 cuentas, 1 recibo y 0 partidas/respuestas), en c08b174c95da. Los CSV, capturas, credenciales y evidencias privadas permanecen fuera del repositorio. Los recursos PostgreSQL nuevos de prueba son sintéticos, propios y sin puertos; se retiran al finalizar, sin borrar registros del entorno de revisión.

Para jugar a InmunoQuest desde la aplicación faltan el acceso público a las partidas y la interfaz de juego local y online. La preparación de mazos, presentación de cartas y evaluación del lector ya funcionan internamente. Esta entrega solo permite gestionar contenido y consultar disponibilidad. El Trivial individual permanece compatible y no se amplía.

## Revisión manual breve

1. Abrir http://localhost:13014/login con la cuenta docente ficticia existente (credenciales solo en su archivo privado).
2. Menú → Gestión de preguntas. Consultar todos los formatos y después InmunoQuest/asignatura; probar Sin asignatura y Sin categoría.
3. Abrir Crear pregunta y alternar con Importar CSV; comprobar asignatura directa y clasificación opcional. No se inicia ninguna partida.
4. Consultar la tabla de los veinte mazos: incluye toda la asignatura, sin objetivos ni actividades.
5. Usar el enlace secundario para administrar la jerarquía. La cuenta estudiante debe ser rechazada en gestión.
