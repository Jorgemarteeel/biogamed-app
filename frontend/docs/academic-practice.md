# Recorrido académico del alumno

Estado actualizado a 8 de noviembre de 2026. Se conserva abajo el registro de las entregas anteriores. Cambios pendientes de revisión visual del usuario, sin commit ni push. Se conserva el backend de la primera entrega y su migración. Contratos de los motores: [selección académica backend](../../backend/docs/academic-selection.md).

## Comportamiento implementado

El panel muestra directamente las asignaturas con el encabezado «¿Qué quieres practicar hoy?» y saludo secundario. «Unirme con código» abre un diálogo nativo que reutiliza el formulario y los reintentos existentes. «Explorar otros contenidos» despliega el selector heredado por juego/temática, incluido contenido sin clasificación académica. No se eliminan ni reclasifican datos heredados.

`/practicar?subject=…` reúne bloques desplegables, categorías y preparación en una misma página de asignatura. Al seleccionar categoría el contenido pasa a una franja compacta. Las tarjetas grandes de juego se muestran solo al elegir o cambiar; después quedan resumidas. Pasapalabra aplica el mismo patrón a su modo. Dificultad, invitado y disponibilidad tienen prioridad en la preparación final. No se requiere otra pantalla por cada nivel. No incluye selector de Topic: la categoría puede tener preguntas de distintas temáticas. Las tarjetas usan nombres y descripciones reales y muestran categorías vacías. El retorno actual usa un único «Volver» con destino explícito calculado desde la URL, sin depender de historial del navegador ni reconstruir relaciones por nombres.

La URL conserva `subject`, `block`, `category`, `subjectsPage`, `blocksPage`, `categoriesPage`, `mode`, `difficulty`, `play` y `step` (`game`, `mode` o `prepare`). Se validan IDs positivos y combinaciones jerárquicas completas; una ruta incorrecta produce error, sin ampliar selección. Cada listado muestra doce elementos y solicita uno adicional para decidir si existe página siguiente. Paginación estable por ID, enlaces de acceso directo, atrás y recarga. Seleccionar otra asignatura/bloque reinicia las páginas de sus descendientes. Cambiar juego conserva la dificultad. Si no existe en el nuevo banco, se mantiene seleccionada, se explica la incompatibilidad y se bloquea el inicio hasta que el alumno elija otra; nunca se amplían filtros automáticamente. Los enlaces antiguos con juego explícito siguen abriendo su preparación; Pasapalabra sin modalidad muestra sus tarjetas y no permite iniciar hasta elegirla. Al seleccionar otra categoría se conserva el juego/modo elegido y se revalida la dificultad. `step` permanece aceptado para compatibilidad, sin mantener una segunda preparación. Las elecciones usan navegación sin reiniciar el desplazamiento de la página; las cargas técnicas no añaden entradas a la URL.

La elección usa el componente compartido `GameChoiceCards`, con las mismas ilustraciones y presentación del selector heredado. Pasapalabra usa `PasapalabraModePicker`, extraído del selector existente sin redibujar sus SVG: «En este dispositivo · Tú y un invitado» o «En línea · Con un amigo · Dos cuentas». No hay desplegable de juego ni se vuelve a pedir Topic. Elegir una tarjeta solo navega; nunca inicia una partida. La preparación posterior ofrece solo los niveles disponibles en esa categoría/modalidad, además de «Sin filtrar dificultad» y «Sin clasificar». Si un enlace conserva una dificultad sin resultados, sigue visible como selección sin preguntas; no se sustituye. Pasapalabra conserva local con nombre de invitado y creación online con dos cuentas. Se distinguen ausencia de preguntas jugables, dificultad sin resultados e insuficiencia de las cuarenta necesarias. Trivial anuncia hasta diez preguntas; Pasapalabra anuncia cuarenta distintas, veinte por persona y diez minutos individuales.

Iniciar es siempre una acción explícita. Se usa `/game/academic/start` para Trivial y los contratos existentes de inicio local/sala para Pasapalabra. Los reintentos inciertos de Pasapalabra conservan UUID y cuerpo y bloquean cambios de configuración. El contrato de creación de Trivial no es idempotente: si se pierde su respuesta, la interfaz no repite automáticamente ni permite reintentar a ciegas; ofrece revisar historial antes de preparar otra partida. No se ha cambiado ese motor.

El login conserva una URL académica interna validada, incluidos filtros y páginas. La invitación de Pasapalabra conserva su mecanismo de recuperación y exige confirmar de nuevo la unión. La carga, errores recuperables, caducidad y vacíos son explícitos; se enfoca el encabezado tras cargar el nuevo nivel. Tarjetas y controles conservan etiquetas, foco de teclado y estilos existentes. Se usan SVG sencillos de carpeta y no hay dependencias nuevas.

## Catálogo de lectura

Router `/practice`, independiente de `/subjects` y sus permisos docentes. Todas las rutas requieren autenticación; también pueden consultarlas estudiantes. Solo proyecta metadatos, relaciones académicas validadas y recuentos de preguntas elegibles: nunca preguntas o soluciones.

| GET | Respuesta |
| --- | --- |
| `/practice/subjects?skip=0&limit=12` | `context:{}`, `items:[{id,name,description}]`. |
| `/practice/subjects/{subject_id}/blocks` | Contexto de asignatura e items de bloques. |
| `/practice/subjects/{subject_id}/blocks/{block_id}/categories` | Contexto de asignatura/bloque e items con `availability:{TRIVIAL,PASAPALABRA}`. Incluye cero. |
| `/practice/subjects/{subject_id}/blocks/{block_id}/categories/{category_id}` | `academic` con los seis campos de identidad/nombre y disponibilidad por juego. |

Las listas admiten `skip>=0`, `1<=limit<=100` y orden estable por ID. Las rutas cruzadas o inexistentes devuelven 404, los parámetros inválidos 422 y la falta de autenticación 401. El catálogo usa el filtro compartido de elegibilidad y exclusión de retiradas. Los recuentos de cada dificultad se consultan con `/game/academic/preparations?mode=...`; el motor revalida la selección al iniciar.

## Contexto guardado y compatibilidad

La ruta académica guardada se muestra en sala, partida, resultado, historial, tarjetas y progreso cuando existe. En escritorio Pasapalabra sitúa ese contexto en la fila de título, con lectura interna mediante foco si es largo, para conservar el espacio de pregunta, roscos y controles. En ventanas estrechas aparece debajo del título y se permite desplazamiento natural. No se modifica el CSS de distribución aprobado de los juegos ni su celebración/movimiento reducido.

Trivial usa el contexto devuelto al iniciar y corregir. Historial y marcas prefieren los nombres guardados, admiten `topic_id:null` y no inventan una temática única. Los resultados antiguos sin contexto académico mantienen sus etiquetas y advertencias anteriores; no se reconstruye su clasificación consultando relaciones actuales. Las claves de grupos de progreso incluyen el ámbito académico para distinguir los grupos que devuelve el backend.

## Demo y migraciones por entorno

Demo: `http://localhost:13004/dashboard` y `http://localhost:13004/practicar`, API `http://localhost:18004`. Antes de escribir se verificaron la conexión efectiva `biogamed_demo/demo_admin`, host interno `db`, puertos loopback y volumen `biogamed_docente_demo_demo_data`.

Copia externa previa a la migración:
`C:\Users\Jorge\Documents\BioGaMed-backups\20261106-172531-demo-academic\biogamed_demo-before-b31.dump`.
Se comprobó éxito de `pg_dump -Fc`, archivo externo, catálogo `pg_restore --list` y coincidencia SHA-256 con el archivo original. SHA-256: `F265C3FDC204C75B9BFAEDF2FACADA3869555EAA2E33B0FCA94C964FCDB3E34E`.

Se aplicó exclusivamente en la demo `a21b30c41d52 → b31c40d52e63`, sin repetir el ensayo aislado aprobado. Conservación durante esa migración: 3 usuarios, 143 preguntas, 43 sesiones y 277 respuestas. Después se añadió contenido ficticio propio de revisión, sin modificar las clasificaciones existentes ni crear cuentas:

- Asignatura 3: «Demo · Recorrido académico».
- Bloque 4: «Sistema cardiovascular».
- Categoría 7: «Corazón y vasos (demo)», 41 preguntas Trivial (40 de nivel 2 y una sin clasificar) y 40 de Pasapalabra nivel 2, procedentes de dos Topic nuevos de prueba.
- Categoría 8: «Banco insuficiente (demo)», 39 preguntas por juego.
- Categoría 9: «Sin preguntas (demo)»; otras once categorías vacías para verificar paginación.

No se aplicaron migraciones ni se realizaron escrituras en la base habitual durante estas entregas académicas. Su revisión comunicada sigue siendo `a21b30c41d52`; la nueva interfaz académica necesita `b31c40d52e63` antes de habilitar su uso allí. Esta actualización de la habitual requiere autorización y procedimiento de copia propio. El ensayo PostgreSQL de la primera entrega se conserva y no se repitió.

## Comprobaciones aprobadas reutilizadas

- Primera entrega backend: suite general 262 aprobadas; 15 pruebas PostgreSQL aisladas; última selección relacionada de 38 aprobadas. No se repitieron motores ni carreras porque la segunda entrega solo añade catálogo y presentación.
- Segunda entrega: 23 pruebas backend de catálogo, permisos docentes y jerarquía/paginación aprobadas, ejecutadas con SQLite en contenedor sin red.
- Suite frontend de 131 pruebas aprobada; tipos y lint correctos. Compilación de producción final correcta, realizada en un contenedor independiente para mantener la demo disponible.
- Al reanudar, sin modificar código de producción, se añadieron dos regresiones de contexto académico en sala y progreso: las 21 pruebas de esos dos archivos aprobaron. Son adicionales a la suite de 131; no se afirma haber repetido una suite completa de 133.
- Se cubren URL, paginación, filtros, cero/39/40, jerarquías, contratos sin Topic, doble clic, UUID conservado, incertidumbre de inicio Trivial, retorno tras login, errores de red y presentación antigua/nueva.

## Revisión visual realizada y pendiente

Antes de la interrupción por límite de uso se revisaron en el navegador integrado: catálogo y ruta académica, categorías vacías/insuficientes visibles, foco y navegación Tab/Enter, elección «Sin clasificar», Trivial completo con respuesta y resultado, inicio local de Pasapalabra, un acierto con Enter y conservación de turno. La sesión Trivial 44 quedó completada; la sesión personal 45 corresponde al enfrentamiento local 25. Se revisó también la creación de sala académica 15, su contexto acordado y plaza 1/2. La sala 15 ya ha vencido según el reloj del servidor: no se presenta como lista para continuar.

También se observó en una segunda sesión por origen (127.0.0.1) la unión sin autenticación, su aviso real y la conservación del código antes de volver al login. La acción de introducir la contraseña de la cuenta rival no se ejecutó: la revisión automática se interrumpió por límite de uso, sin determinar que la acción fuera insegura. No se modificaron cuentas ni contraseñas.

Tras reanudar, el usuario restringió la revisión a herramientas específicas del navegador integrado. En esta sesión solo se descubrieron `open_in_codex` (abre una URL, pero no inspecciona ni acciona la página) y mecanismos genéricos/de escritorio; no se dispone de herramienta específica de DOM, interacción ni viewport separada de ese control. Se respetó la restricción: no se continuó mediante control de escritorio/ChatGPT, Opera GX, otras aplicaciones ni mecanismos alternativos de automatización.

**Pendiente de revisión del usuario:** adaptación móvil completa del recorrido y partida, ambos roscos y corrección en los tamaños de escritorio aprobados, completar login del rival, unión, confirmaciones e inicio de sala académica y revisar sus dos clientes. Quedan también la comprobación visual final del historial/progreso académico y regresión visual de accesos heredados tras todos los ajustes. Las observaciones anteriores en panel estrecho y vista amplia no se presentan como emulación móvil exacta ni como medición DOM de desbordamiento. Los tests de componentes y las respuestas HTTP no sustituyen esa revisión visual.

Se conservan las limitaciones anteriores: sin teclado virtual móvil físico, zoom nativo al 200 %, lector de pantalla físico ni ajuste nativo de movimiento reducido verificados. No hay nueva aprobación visual del usuario para estas entregas.

## Pasos para la revisión del usuario

1. Entrar en `http://localhost:13004/dashboard` con la cuenta docente demo existente y elegir directamente una tarjeta de asignatura.
2. Elegir «Demo · Recorrido académico», abrir «Sistema cardiovascular» y elegir «Corazón y vasos (demo)»; en la misma página, elegir juego mediante sus tarjetas y, para Pasapalabra, elegir modalidad mediante sus tarjetas. Cambiar dificultad en preparación y comprobar URL, atrás, controles de cambio y recarga antes de iniciar; una dificultad incompatible debe mantenerse con aviso y sin inicio disponible. La página de categorías tiene dos páginas y conserva las categorías vacías.
3. Para Trivial, «Sin clasificar» ofrece una pregunta y Nivel 2 ofrece diez por partida. La ruta y el resultado deben conservar nombres académicos.
4. Para Pasapalabra, Nivel 2 permite local con invitado o crear sala online. «Banco insuficiente» debe impedir empezar con 39 y «Sin preguntas» debe explicar su vacío, sin cambiar filtros.
5. Crear una **sala nueva**, copiar su código y abrir `http://127.0.0.1:13004/pasapalabra?join=1` con la cuenta existente «Rival demo en línea». Los orígenes mantienen autenticaciones independientes. Verificar qué cuenta aparece en cada cliente, unir explícitamente, revisar la misma ruta académica, confirmar ambos e iniciar como creador.
6. Revisar ambos turnos, relojes, corrección, móvil y escritorio; abrir el historial propio y el progreso. Probar también «Explorar otros contenidos» y el diálogo «Unirme con código» del panel.

Las credenciales permanecen en sus archivos locales de demostración fuera del repositorio; no se incluyen en esta documentación ni en el diff. La demo sigue funcionando; partidas y salas consumen tiempo/caducan según el servidor, sin pausas nuevas.

## Ajuste previo de elección y preparación visual (ver versión unificada posterior)

Se reutilizan los mismos componentes de tarjetas en los accesos heredados y en el recorrido académico, manteniendo sus recursos compartidos y el flujo directo de unión. En aquella iteración, la ruta académica permanecía visible en los tres pasos; la versión unificada posterior los reúne en una página. El nombre de invitado solo se solicita en la preparación local; la disponibilidad y las acciones conservan los contratos académicos y límites existentes. No se han modificado backend, reglas, migraciones ni bases de datos para este ajuste.

Comprobaciones específicas: 28 pruebas frontend aprobadas de recorrido académico, salas y landing; tipos (`tsc --noEmit`) y lint completos correctos. Incluyen tarjetas y navegación con contexto/paginación, dificultad compatible e incompatible, enlaces directos antiguos, acciones explícitas sin Topic, creación local/online, y regresión de las tarjetas heredadas y las ilustraciones compartidas de la landing. No se repitieron las baterías de motores ni las migraciones aprobadas. Fuentes frontend de la demo aislada sincronizadas; no se ha escrito en ninguna base.

Revisión visual de este ajuste pendiente: escritorio, móvil y teclado en elección de juego → modalidad → preparación, con atrás/recarga y aviso de dificultad incompatible. Solo se dispone del abridor de URL del navegador integrado, sin interacción, DOM o viewport específicos; no se ha usado control de escritorio ni de la aplicación completa. Las verificaciones automatizadas no se presentan como revisión visual y se mantienen todas las limitaciones anteriores.


## Panel y preparación unificada: primera versión revisable

Esta versión sustituye la tarjeta intermedia de práctica por asignaturas reales en el panel. Incluye carga, vacío, error recuperable y páginas de doce asignaturas con un elemento adicional para detectar la página siguiente. El menú, permisos docentes y cierre de sesión permanecen. Se muestran hasta tres partidas recientes con `GameSummaryCard` y enlace al historial completo, manteniendo el desglose personal y sin contar pendientes como fallos. «Volver a practicar» solo aparece si entre las cinco partidas recientes devueltas por el contrato existente hay un contexto académico guardado válido; usa sus IDs y selección, sin inferir relaciones por Topic y sin iniciar automáticamente.

La preparación comparte una única implementación para enlaces anteriores y nuevos. El árbol de contenido usa los endpoints autenticados existentes y páginas acotadas de bloques y categorías. Solo carga categorías del bloque abierto/seleccionado; reutiliza la página que ya haya cargado el contenedor. Un bloque guardado fuera de la página visible permanece accesible con su identidad comprobada. Cambiar de asignatura limpia dependencias; cambiar de bloque limpia categoría y su página. Juego, modalidad, dificultad y páginas permanecen en URL; el nombre del invitado se conserva como borrador de esta pestaña mediante sessionStorage cuando está disponible. Las respuestas de consultas desmontadas se descartan.

En escritorio el árbol se presenta junto a la preparación. En móvil el contenido ya elegido se resume en una sección desplegable modificable; no se fuerza una altura de viewport ni se recorta el formulario. Las selecciones usan fondo, borde, marca y estado accesible. El resumen incluye contenido, juego, modalidad, dificultad y disponibilidad. Los recursos científicos específicos existentes pertenecen a Topic y no hay metadatos gráficos académicos fiables: se ofrece un SVG neutro de libro y laboratorio, sin carpetas repetidas, IDs, nombres fijados ni clasificación deducida. Las ilustraciones de juego/modalidad son las mismas compartidas, sin variantes nuevas.

El diálogo de unión usa `showModal`, cierre/Escape nativos y restitución del foco al elemento anterior; el formulario conserva código y UUID incierto. Ante autenticación caducada guarda `/dashboard?join=1` antes de enviar, destino interno exacto aceptado por el login. Tras identificarse, vuelve al diálogo con el código conservado y exige pulsar «Unirme»; no hay unión automática.

Comprobaciones de esta versión: 54 pruebas frontend relacionadas de panel/catálogo, preparación académica, salas/formulario compartido, retorno de login y landing aprobadas; tipos, lint sin avisos y compilación de producción correctos. Compilación en `biogamed_academic_build`, separada del servidor demo. Incluyen carga por demanda y reutilización de páginas, vacíos, filtros y 39/40, enlaces anteriores, navegación/contexto, bloqueo de cambios durante inicio incierto, borrador de invitado, tres resultados personales, semántica nativa del diálogo y devolución de foco. Tras alinear cabecera, título y contenido con estilos acotados a preparación (sin tocar el CSS de partidas), se repitieron únicamente las 28 pruebas de panel/preparación, tipos, lint y compilación; correctos. Las pruebas del diálogo no equivalen a comprobar un navegador/lector de pantalla real.

Demo frontend sincronizada y disponible en `http://localhost:13004/dashboard`; no se han cambiado backend, motores, contratos, dependencias, migraciones ni datos en esta tarea. No se ha copiado contenido desde la base habitual ni se ha intervenido en operaciones de datos de otras tareas. Los nombres técnicos/ficticios que continúan en la demo pertenecen al catálogo de revisión anterior, no al nuevo diseño.

**Revisión del usuario pendiente:** panel y preparación en escritorio/móvil, teclado real del diálogo y de los desplegables, acceso directo, recarga y atrás, legibilidad de nombres largos y ausencia de desbordamiento lateral. La búsqueda actual de herramientas solo ofrece un abridor de URL, sin herramientas específicas de interacción, DOM o viewport del navegador integrado. No se ha usado control de escritorio, de toda la aplicación, Opera GX ni automatización alternativa. Las respuestas HTTP y las pruebas de componentes no se presentan como revisión visual. Se mantienen también las limitaciones previas de teclado virtual, zoom 200 %, lector de pantalla y movimiento reducido. No se han repetido partidas completas ni las pruebas de motores.

Para revisar: entrar al panel → elegir «Demo · Recorrido académico» → abrir «Sistema cardiovascular» → elegir «Corazón y vasos (demo)» → elegir juego, dificultad y modalidad si corresponde. Modificar una opción, volver atrás y recargar antes de pulsar el inicio explícito. «Banco insuficiente (demo)» y «Sin preguntas (demo)» mantienen sus avisos. Probar el diálogo de código desde el encabezado; los accesos heredados siguen en «Explorar otros contenidos». Todo sigue pendiente de aprobación visual, sin commit ni push.


## Preparación progresiva y contenido auténtico (8 de noviembre)

La versión compacta sustituye el árbol lateral persistente por una franja con asignatura/bloque/categoría y «Cambiar contenido». No hay desplegable exterior «Bloques y categorías»; solo los nativos de cada bloque mientras se elige contenido. Juego y modo comparten las mismas ilustraciones grandes al elegir; al confirmar pasan a resúmenes con ilustraciones pequeñas y «Cambiar juego/modo». Los campos finales y la acción principal quedan protagonistas. «Sobre el inicio» conserva la ayuda secundaria plegada.

`step=game|mode|prepare` reabre cada elección sin borrar valores. `edit=content` permite volver al árbol manteniendo el contexto; al seleccionar categoría se cierra y se recupera el juego/modo si siguen elegidos. La dificultad incompatible queda seleccionada con aviso, nunca se amplían filtros. El foco vuelve al SELECT al cambiar dificultad, sin desplazar repetidamente la página; la carga de categorías enfoca su contenido. Se mantienen URL, páginas, atrás, recarga, borrador de invitado y ausencia de inicios automáticos.

Se han copiado 371 preguntas auténticas (369 activas) a la demo, conservando sus cuentas y actividad. Acceso principal para esta revisión: `http://localhost:13004/practicar?subject=4` → **Práctica biomédica**. Su jerarquía es expresamente provisional porque la base habitual no tiene asignaturas ni bloques; la nota se muestra desde metadatos, sin clasificaciones por nombre/ID en el frontend. Los detalles de respaldo, restauración, huellas, correspondencias, procedencia y límites están en [copia de contenido demo](../../backend/docs/demo-content-copy.md).

Las preguntas técnicas anteriores se retiraron, conservando sus referencias e historial; sus asignaturas vacías permanecen por falta de archivo en el modelo. No se añadieron filtros por nombre para ocultarlas. El original completo está conservado en una base de prueba restaurada; no se copiaron usuarios ni actividad de la habitual. La habitual mantiene `a21b30c41d52`, la demo `b31c40d52e63`; sin migraciones nuevas.

Comprobaciones actuales: 35 pruebas frontend relacionadas aprobadas, tipos, lint y compilación; 8 de importación, incluido PostgreSQL aislado. Revisión real mediante las herramientas de pestaña del navegador integrado en escritorio 1366×768 y móvil 390×844, teclado, cambios, atrás y recarga, sin crear partidas. Acción principal visible en escritorio; móvil con scroll accesible y sin desbordamiento lateral. Se conserva el resto de limitaciones de accesibilidad física y de movimiento reducido documentadas. Los registros anteriores que indicaban falta de herramientas reflejan aquellas sesiones, no esta última revisión. Todo continúa pendiente de aprobación visual del usuario, sin commit ni push.


## Pulido visual del recorrido (8 de noviembre, posterior a la copia)

Esta entrega solo modifica presentación y navegación. No ejecuta importadores, retiradas, semillas, migraciones ni conexiones a la base habitual. Se conserva el contenido auténtico y la jerarquía provisional ya importados. Backend, motores, autorización, historial, progreso y copias no se modifican.

**Navegación:** se eliminan las migas visibles; un único «Volver», con foco visible y flecha SVG compartida, aparece sobre el título. No existe una dependencia/biblioteca de iconos instalada: se ha seguido la convención SVG local existente, sin instalar otra. El contexto aparece una sola vez en su franja. Los resúmenes conservan «Cambiar contenido», «Cambiar juego» y «Cambiar modalidad». La descripción de la organización sigue accesible en «Sobre este contenido», plegada. Se mantienen los nombres reales, incluido «Preguntas del Trivial original».

`practiceBackHref` calcula el paso anterior con la selección, filtros y páginas relevantes conservados: preparación Trivial → juego; preparación Pasapalabra → modalidad → juego → contenido; edición de contenido con categoría → paso guardado; bloque sin categoría → bloques de la asignatura; asignatura → panel. Funciona con entrada directa y recarga. Si una categoría directa devuelve 404, permite subir al contenido padre en vez de alternar pasos inválidos. El control se deshabilita durante una operación de inicio pendiente/incierta. `Frame.backControl` es opcional: las pantallas de partida conservan el enlace/salida predeterminados, sus títulos, confirmaciones y espaciado. No se rediseñan partidas.

**Disponibilidad:** al elegir juego se consultan en paralelo los dos contratos existentes de preparación académica, sin soluciones ni preguntas. Las tarjetas usan los recuentos filtrados por dificultad; el selector permite cambiarla explícitamente antes de continuar. Cero: «Sin preguntas disponibles». Pasapalabra 1–39: cantidad y requisito de 40 distintas. Ambos casos bloquean la tarjeta y su acción; Trivial admite desde una, hasta diez por partida. Si la dificultad no tiene preguntas, se conserva con aviso. Al cambiar categoría, si el juego anterior ya no alcanza su mínimo, se reabre la elección manteniendo las preferencias en URL. El servidor sigue revalidando al iniciar; no hay mezclas de categorías ni ampliaciones automáticas. Los accesos heredados sin disponibilidad proporcionada conservan su comportamiento.

**Recursos:** cuatro SVG locales en `public/categories/` para Erlenmeyer, Jeringuilla, Linfocito y Macrófago. La correspondencia exacta solicitada está en `category-presentation.ts`, limitada a presentación decorativa y normalización Unicode NFC; no asigna contenidos ni modifica relaciones. Otros nombres usan el recurso genérico anterior. Colores, fondos y trazos siguen las tarjetas compartidas. Se mantienen las ilustraciones de juegos y modos.

**Comprobaciones:** 39 pruebas actuales de panel/selección y navegación, incluidos volver con entrada directa/recarga, contexto único, error 404, filtros, 0/39/40, bloqueo de tarjetas, reapertura y correspondencias gráficas. Se reutilizan las 3 pruebas de landing y 16 de Pasapalabra aprobadas durante esta entrega antes de los ajustes acotados a catálogo/retorno; 58 comprobaciones relacionadas vigentes en total. Tipos y lint sin avisos; compilación de producción independiente correcta. No se repiten suites backend ni pruebas de los motores.

**Revisión real:** herramientas específicas de pestaña, DOM y viewport del navegador integrado aislado; cuenta ficticia confirmada. 1366×768: documento/clientWidth 1366, alto 768, acción local hasta y≈533, un único control Volver, sin scroll de página ni desbordamiento horizontal en la preparación comprobada. 390×844: documento/clientWidth 375, alto 1030, cero elementos fuera del borde derecho; desplazamiento natural. Verificados teclado, restauración de sesión, entrada directa desde otra categoría, volver por los pasos correctos, recarga, invitado conservado, foco SELECT y desplegable informativo. Comprobados Trivial con diez preguntas del nivel 2, Pasapalabra con 107 y tarjeta del juego sin preguntas bloqueada; cuatro ilustraciones inspeccionadas en el catálogo. No se inició partida ni sala.

El caso de 39 preguntas se comprueba automáticamente: el banco auténtico de revisión no contiene ese escenario activo y no se han alterado datos para simularlo. Se mantienen los límites pendientes de teclado virtual físico, zoom nativo 200 %, lector de pantalla y movimiento reducido. La revisión del agente no es aprobación visual del usuario. Las medidas no prometen ausencia universal de scroll para cualquier texto, zoom o ventana.

Demo sincronizada en `http://localhost:13004/practicar?subject=4`. Revisar: abrir bloque/categoría; elegir juego y dificultad; usar «Volver» tras recargar y «Cambiar» para comprobar conservación; en Fisiología, Trivial queda sin preguntas y Pasapalabra dispone de 107; en categorías del Trivial original, elegir un nivel muestra diez. Capturas externas: `C:/Users/Jorge/Documents/Playground/academic-polish-desktop.png` y `academic-polish-mobile.png`. Todo sigue en main, sin staging, commit ni push; cambios anteriores conservados.

## Revisión coherente del recorrido (9 de noviembre de 2026)

Esta revisión sustituye la presentación anterior de dificultad en las tarjetas: contenido → juego → modalidad de Pasapalabra → dificultad/datos → inicio explícito. La disponibilidad de las tarjetas usa el total de la categoría, antes de filtrar dificultad. Una dificultad guardada permanece en URL y se comprueba al preparar; si es incompatible se avisa y no se amplía. Trivial mantiene hasta 10; Pasapalabra exige 40 distintas. «No disponible» no tiene flecha, subrayado ni acción.

Panel y preparación comparten un ancho máximo de 68rem y el mismo eje para cabecera, título y contenido. Se conservan las ilustraciones, con variante compacta opcional de las tarjetas académicas; no se rediseñan partidas. El acceso conserva las dos columnas y actualiza su texto. La paginación solo aparece cuando hay más páginas o se está en una posterior. Las descripciones de bloques y categorías consultadas se reúnen en «Sobre este contenido», junto a la nota provisional; no se renombran clasificaciones ni se infiere su naturaleza.

### Configuración exclusiva de presentación de la demo

`NEXT_PUBLIC_DEMO_TEST_SUBJECT_IDS` es una lista explícita de IDs separados por comas, sin valor por defecto. En el Compose externo de `biogamed_docente_demo` se ha configurado `1,2,3`, tras comprobar esos registros. Agrupa esas asignaturas en «Contenido de pruebas», cerrado inicialmente, dentro de la página solicitada del catálogo; conserva sus enlaces, permisos y paginación. No filtra por nombres, no oculta datos de la API y no modifica el catálogo habitual. Sin esta variable se muestra el catálogo normal. La variable pública se incorpora al compilar (o al arrancar Next en desarrollo); no contiene secretos. El Compose de demo y sus credenciales permanecen fuera de Git.

«Volver a practicar» consulta la disponibilidad actual de la última selección académica guardada, con su modalidad y dificultad. Si no alcanza el mínimo, ofrece elegir contenido; si no puede comprobarse, informa y permite reintentar. No recomienda otra categoría ni cambia filtros silenciosamente.

### Comprobaciones de esta revisión

- 46 pruebas relacionadas aprobadas (43 de catálogo/preparación y 3 de landing). Tras el ajuste final de ancho de tarjeta y ayuda sin descripción de asignatura, se repitieron únicamente las 43 afectadas: aprobadas. Tipos, lint y compilación final aprobados. No se repitieron motores ni baterías ajenas.
- Revisión previa en navegador integrado: login, panel, bloques, categoría Erlenmeyer (40 Trivial / 0 Pasapalabra; nivel 2: 10), Vocabulario de fisiología (0 / 107), juegos, modalidades y preparación. Se abrió una partida de cada juego solo en la demo. Pasapalabra conserva dos roscos, pregunta central, relojes y controles. No se han creado nuevas cuentas, importado/retirado preguntas ni cambiado clasificaciones; esas dos partidas de revisión sí dejan sus registros normales en la demo.
- Revisión posterior limitada a las pantallas afectadas: login, agrupación del panel y despliegue por teclado, notas de procedencia, tarjetas sin dificultad previa, cero preguntas, resúmenes y cambios, recarga con invitado/dificultad, vuelta a modalidad después de recarga, foco hasta inicio sin pulsarlo. La expiración real de la sesión se recuperó con la cuenta existente y mantuvo el destino.
- Escritorio solicitado 1366×768: títulos/contenido alineados; Trivial inicial midió página 1366×768 y botón a y≈533; en la sesión de navegador recuperada el viewport redondeó la altura a 769 CSS px. Tarjetas completas hasta y≈581, modalidad hasta y≈557 y comienzo local hasta y≈533, sin desbordamiento de página. 1920×1080: tarjetas y contexto alineados, página 1920×1080. CSS zoom=1 y visualViewport.scale=1; no se redujo el zoom para encajar.
- Móvil 390×844: modalidades, tarjetas apiladas y preparación legibles, sin desbordamiento horizontal; preparación con scroll natural (alto 1031) y tarjetas (1099), ancho útil 376 por barra de desplazamiento. Tab alcanza el botón de comienzo, con foco visible. Login móvil mantiene todos los controles.
- La demo se restauró con su Compose existente después de un fallo del motor Docker Desktop; volumen `biogamed_docente_demo_demo_data` conservado. No se conectó ni escribió en la base habitual, no se aplicaron migraciones y no se ejecutaron seeds.

Límites: no se ha simulado un teclado virtual físico, lector de pantalla ni zoom nativo al 200 % en esta revisión. El caso de 39 preguntas y la selección anterior ya no disponible se cubren con pruebas automatizadas; no se alteró el banco real para fabricarlos. Se mantienen las limitaciones previas de movimiento reducido. La agrupación demo opera sobre la página paginada, no cambia el orden global del servidor.

Para revisar: abrir `http://localhost:13004/dashboard`, elegir Práctica biomédica y abrir Preguntas del Trivial original → Erlenmeyer o Fisiología → Vocabulario de fisiología. Elegir juego, modalidad cuando proceda y dificultad. Probar «Cambiar» y «Volver», y recargar antes de comenzar. Ninguna selección inicia una partida. Todo permanece sin staging, commit ni push.

## Aprobación visual del usuario y preparación de commits — 9 de noviembre de 2026

El usuario revisó personalmente el conjunto visual y confirmó que el último acceso duplicado estaba solucionado. Autorizó commits locales del conjunto pendiente, incluidos recorrido académico, landing, panel, resultado de Pasapalabra y herramientas asociadas. Esta aprobación se registra como revisión del usuario; no se atribuyen a ella verificaciones técnicas no realizadas.

Estado final del panel sin asignaturas: un único botón principal «Practicar con los bancos disponibles» controla apertura/cierre con aria-expanded y aria-controls. «Bancos de preguntas disponibles» es un título de sección. El selector permanece montado mientras se oculta para conservar selecciones; cuando existen asignaturas se mantiene el acceso secundario anterior. Esta implementación sustituye el enlace nativo descrito en registros anteriores.

Comprobaciones reutilizadas por alcance: backend académico general/PG y catálogo documentados, importador y clon aislado documentados, frontend de recorrido/landing (46 relacionadas) y resultado/partida activa/panel (45 relacionadas). Son tandas solapadas, no se suman como casos únicos. El último ajuste de acceso tiene 20 pruebas de panel aprobadas. Tipos y lint se comprobaron de nuevo al preparar los commits porque el acceso había cambiado desde su última ejecución; build de la entrega visual final aprobado anteriormente. No se repitieron motores, migraciones ni recorridos visuales aprobados. Se mantienen los límites de lector de pantalla real, teclado virtual físico, zoom nativo al 200 %, movimiento reducido nativo y dispositivos físicos.

La habitual ya está en b31c40d52e63 por operación autorizada separada, preservando sus datos; no se ha trasladado la jerarquía provisional de demo. La configuración externa de demo y credenciales, volcados, capturas, manifiestos con contenido protegido y temporales se excluyen de los commits.
