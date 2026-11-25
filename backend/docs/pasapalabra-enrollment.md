# Pasapalabra por matrícula y nombre Trivial

## Recorrido disponible

El panel ofrece Pasapalabra y reserva Trivial (tablero), todavía sin inicio jugable. Pasapalabra sigue juego → asignatura → temática → dificultad 1–4 → modalidad. El servidor obtiene el año de la matrícula habilitada; no admite una edición elegida por el cliente. El catálogo devuelve exclusivamente las asignaturas habilitadas de la cuenta y las temáticas de esa edición, con recuentos por nivel sin soluciones. Se mantienen 40 preguntas distintas, veinte por participante, y diez minutos individuales; un nivel escaso no se amplía automáticamente.

En local el acompañante confirma con su propio DNI y contraseña. Se verifica la cuenta existente y activa sin emitir otro JWT ni sustituir la sesión del anfitrión. Las credenciales solo viajan en la petición de inicio; no se incorporan al recibo, URL, contexto, almacenamiento del navegador ni registros. La contraseña se limpia al terminar cada intento. Un error del acompañante devuelve 400 para no cerrar la sesión del anfitrión. Se reutiliza el límite de login por IP real antes del hash; conserva su limitación por proceso. Los errores de validación de esa ruta no reflejan datos de entrada.

En línea cada cuenta mantiene su propia sesión y se reutilizan sala, código, preparación e inicio existentes. Ambas cuentas deben tener habilitada la misma edición: se comprueba al unirse y de nuevo al iniciar. Un cambio entre preparación e inicio rechaza la selección anterior; no sustituye el contenido silenciosamente.

## Conservación y concurrencia

Se conservan el motor, reloj, respuestas, límites y copias privadas existentes. Cada participante registrado, también el acompañante local, recibe su GameSession, respuestas y resultado personal. El anfitrión controla las acciones del dispositivo; el acompañante puede consultar su resultado desde su cuenta, pero no controlar la partida local por peticiones propias. Las sesiones antiguas con invitado continúan interpretándose como tales.

El contexto de cada sesión guarda asignatura, edición y año, temática y nivel, además del icono de la temática. El rosco utiliza ese icono guardado; móvil mantiene la representación compacta y muestra el mismo icono. No vuelve a consultar el icono actual para reconstruir una partida. Cambiar matrícula, nombre o icono afecta a partidas nuevas y no reescribe estos contextos. Las copias de preguntas siguen conteniendo las soluciones exclusivamente en servidor.

La creación por edición comparte el bloqueo transaccional de matrículas. Se verifica la matrícula vigente bajo ese bloqueo, se bloquean las preguntas elegibles hasta copiarlas y se guardan partida, participantes y sesiones en la transacción existente. Un inicio idéntico conserva la misma partida, sin repartir otras cartas. La identidad del acompañante, no sus credenciales, forma parte del contenido idempotente. No se ha añadido migración: edición, temática, nivel e icono caben en los contextos JSON existentes.

Las rutas y selecciones de catálogo antiguas se conservan para compatibilidad; no son entradas del panel definitivo y no pueden seleccionar preguntas de edición. No se migra ni reclasifica el contenido antiguo. El progreso y las mejores marcas anteriores no se reinterpretan para inventar categorías en las partidas nuevas.

## Nombre Trivial y CSV

Trivial es el nombre visible del tablero; Trivial individual distingue el cuestionario anterior y sus historiales. Permanecen INMUNOQUEST, las clases y tablas internas y las rutas /inmunoquest y /gestion/inmunoquest para no invalidar datos e integraciones. Las versiones del motor no se renombran ni reinterpretan. Las fuentes docentes originales conservan su procedencia.

En el importador mixto por edición, juego=Trivial significa pregunta abierta, nunca pregunta de opciones. Se conserva INMUNOQUEST como alias de CSV anteriores. Los ejemplos de edition-content usan Trivial. En las API antiguas, mode=TRIVIAL sigue identificando el cuestionario individual; mode=INMUNOQUEST sigue identificando el tablero. La plantilla de cabeceras mixtas no cambia: la ayuda indica los dos nombres que se escriben en juego. No se altera la configuración de cinco tipos de casilla ni sus vinculaciones e iconos.

## Revisión sintética en 13020

Asignatura Fisiología · ensayo de matrícula (ID 4, código PPR-20261124), ediciones 8/9 para 2026–2027 y 2027–2028. Ambas tienen Vocabulario de fisiología, temáticas 4/5, con iconos diferentes y cuarenta preguntas activas de Pasapalabra de nivel 1 por curso, más una pregunta abierta Trivial por curso. Nivel 2 queda vacío para demostrar el bloqueo. Son preguntas artificiales de integración, no un banco académico validado.

Cuentas: Estudiante de revisión y Alumno acompañante · Pasapalabra están habilitados en 2026–2027. Alumna segundo curso · Pasapalabra está en 2027–2028. Sus accesos se consultan exclusivamente en el archivo privado del entorno, nunca en esta documentación. Para dos sesiones se pueden usar localhost:13020 y 127.0.0.1:13020 (almacenamiento por origen separado) en el mismo equipo; esto no hace accesible localhost desde otro equipo.

1. Entra como Estudiante de revisión. Panel → Pasapalabra → Fisiología · ensayo de matrícula → Vocabulario de fisiología → nivel 1 → Continuar a modalidad. Nivel 2 muestra cero y bloquea continuar.
2. Local: usa los accesos del acompañante para confirmar. Los de la alumna del segundo curso se rechazan por edición diferente.
3. En línea: crea una sala y entra como acompañante en el otro origen. Confirma preparación en ambas sesiones e inicia con el anfitrión.
4. Consulta el historial propio de ambas cuentas. Las partidas de ensayo 1 (local) y 2 (online) terminaron normalmente con veinte aciertos por cuenta. La partida 3 pertenece a 2027–2028 y finalizó por abandono durante la comprobación del cambio de matrícula.
5. Entra como la alumna del segundo curso: la misma asignatura muestra automáticamente 2027–2028 y otro icono. No elijas un año.
6. Como docente, Contenidos muestra Trivial en preguntas y tablero. Los CSV mixtos de ejemplo siguen en docs/examples/edition-content y usan el nuevo nombre; no se convierte el banco individual.

## Evidencia y límites

- Navegador integrado real: panel, preparación, selector de nivel por teclado y falta de contenido; rechazo de acompañante con otro curso; partida local completa conservando la sesión del anfitrión; sala y partida online completas con dos orígenes y cuentas distintas. Resultado normal y revisión de respuestas propias en línea. Nombre Trivial en gestión docente y conservación de Tipo de casilla 3/Tejidos linfoides.
- Navegador: el segundo curso y su icono se contrastaron con el primero. Preparación revisada a 390 píxeles CSS efectivos, sin desbordamiento horizontal; roscos de escritorio comprobados a 1366 × 900. En la preparación móvil se probó abrir el selector con teclado, Escape y retorno del foco. Se revisó el formulario del acompañante sin enviar otro inicio. El historial del anfitrión mostró los dos años con su contexto guardado. No se ha probado lector de pantalla ni zoom real al 200 %.
- API de 13020: comprobación de los dos historiales personales, cambio de matrícula por importación, rechazo de la temática anterior, conservación exacta de contexto/icono previos y comienzo con contenido del nuevo año. Se restauró únicamente la matrícula habilitada de la cuenta ficticia al primer año, conservando ambas matrículas y las partidas. Se importaron 82 preguntas sintéticas mediante CSV, incluidas dos con juego=Trivial.
- Pruebas aisladas: selección de edición, aislamiento de formatos y cursos, identidad del acompañante, límites antes del hash, errores sin credenciales, resultados de las dos cuentas, idempotencia, contexto histórico y revalidación de sala. Dos pruebas PostgreSQL reales verificaron un solo reparto/partida ante dos inicios concurrentes y el bloqueo frente a un cambio de matrícula simultáneo. El PostgreSQL temporal, sin puertos y con datos en memoria, y su red se retiraron.
- Frontend: 128 pruebas focalizadas aprobadas de preparación, icono, historial, compatibilidad, CSV y navegación. Backend: 47 pruebas del primer grupo y 17 del grupo final, con solapamiento (se añadió un caso específico de protección de credenciales). PostgreSQL: dos pruebas nuevas aprobadas. Tipos, lint y compilación aprobados. Se actualizaron las expectativas del panel y los nombres antiguos, conservando las pruebas de compatibilidad del recorrido anterior.
- Solo se actualizó 13020 y sus datos sintéticos. No se modificaron habitual ni 13004, ni se añadieron dependencias o migraciones. El tablero jugable, lector y nuevas pantallas de Trivial siguen fuera de esta entrega. No hay pruebas de carga ni evaluación pedagógica.

## Presentación del panel: revisión del 25 de noviembre

El panel utiliza dos tarjetas protagonistas con ilustraciones originales minimalistas, títulos, una frase de mecánica y estados de acceso distintos. Pasapalabra incluye una pista de ejemplo en HTML y el enlace Preparar Pasapalabra. Trivial muestra Próximamente sin ofrecer un control de inicio. Las imágenes y sus prompts finales están en frontend/public/games/dashboard/README.md. Son ilustraciones, no una reproducción exacta del rosco o del tablero operativo.

Se revisó con la cuenta de alumno ficticia en el navegador integrado de 13020: escritorio de 1366 × 900 y móvil de 390 × 844 píxeles CSS. Las imágenes cargaron, las tarjetas se mostraron en dos columnas o apiladas respectivamente y no hubo desbordamiento horizontal. La acción principal conservó 48 píxeles de altura en móvil. Se activó con Enter y abrió Preparar Pasapalabra con Selecciona una asignatura. Se guardaron capturas locales de escritorio y móvil fuera del repositorio. Pasaron 22 pruebas frontend relacionadas, tipos, lint y compilación. Se sustituyó únicamente el frontend de 13020; no se crearon partidas, no hubo escrituras de contenido ni cambios en 13004.

## Tarjetas de partidas recientes e historial

La tarjeta compartida GameSummaryCard prioriza el nombre del juego y un icono decorativo, seguido de los aciertos, fallos y pendientes registrados del usuario. Distingue Completada, Finalizada por abandono, En curso y Sin finalizar. Asignatura, año, temática, nivel y fecha quedan como información secundaria tomada del contexto guardado; el catálogo actual solo se usa como alternativa expresamente identificada cuando falta el nombre histórico. No se rellenan contadores ausentes con ceros. Se conservan los enlaces de revisión y enfrentamiento o reanudación. El identificador histórico TRIVIAL sigue mostrándose como Trivial individual; INMUNOQUEST conserva el nombre público Trivial. Esto no integra partidas de tablero en el historial.

Verificación nueva del 25 de noviembre: 31 pruebas frontend focalizadas aprobadas (incluidas dos nuevas de jerarquía, nombres, estados y datos ausentes), tipos, lint y compilación. Navegador integrado autenticado como alumno: recientes e historial a 1366 × 900 y 390 × 844, con partidas existentes completadas y abandonadas, contexto de ambos años y acciones visibles; sin desbordamiento horizontal. Capturas fuera del repositorio. Solo se reconstruyó y recreó el frontend de 13020; no se crearon partidas ni se modificaron datos, backend o demo 13004. No se probó lector de pantalla ni zoom real al 200 % en esta revisión.

Cierre de revisión: se corrigieron tres etiquetas del gestor compatible que confundían INMUNOQUEST con Trivial individual; los selectores de preguntas abiertas muestran Trivial y conservan sus valores internos. Ambos CSV mixtos de ejemplo usan el nombre nuevo. Una prueba comprueba las etiquetas en filtros, edición e importación. Tras esta corrección pasaron 40 pruebas frontend focalizadas, tipos y lint; se reutilizan la compilación previa, las regresiones backend/PostgreSQL y la revisión visual descritas arriba. No se reiniciaron servicios ni se repitieron escrituras durante este cierre.
