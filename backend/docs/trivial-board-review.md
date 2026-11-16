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
