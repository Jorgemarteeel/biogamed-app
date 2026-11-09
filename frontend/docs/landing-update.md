# Actualización de la landing pública

6 de noviembre de 2026. Cambio limitado a la landing y a la extracción mínima de su ilustración compartida. Se conservan todos los cambios pendientes del recorrido académico, sin commit ni push.

## Contenido y recursos

La landing presenta «Dos juegos para practicar», la selección por asignatura/bloque/categoría, preparación con juego y dificultad, los dos modos de Pasapalabra y consulta de resultados y evolución comparable. No describe cobertura alfabética ni resultados exclusivos de Trivial. La llamada principal «Elegir qué practicar» enlaza a `/practicar`, cuyo acceso autenticado y retorno desde login ya existen; se conservan enlaces a login, registro y a la sección de juegos.

`GameIllustration.tsx` contiene exactamente la función SVG que antes estaba dentro de `GamePicker.tsx`. El selector la importa con los mismos argumentos, atributos, trazos y clases de tamaño. La landing usa ese mismo componente, con contenedores de anchura limitada para equilibrar las tarjetas. No se han redibujado variantes ni generado imágenes ni añadido dependencias.

Las tarjetas retiran las etiquetas «Disponible» y los símbolos genéricos ✓/Aa. Trivial muestra una pregunta ilustrativa con tres opciones estáticas; Pasapalabra, una casilla 7 y una pista. Ambos ejemplos se identifican como ilustrativos y no interactivos. No se ha consultado ningún banco de preguntas para construirlos. Se reducen espacios verticales de secciones y se conserva la identidad visual y el marco institucional.

## Comprobaciones

- TypeScript (`npx tsc --noEmit`) y lint aprobados en el frontend de la demo.
- Tres pruebas específicas de landing aprobadas: textos y destinos, identidad del SVG en landing/selector y ejemplos sin controles ficticios.
- Comparación de la función extraída con la versión del selector previa al cambio: coincidencia exacta.
- Demo sincronizada y GET `http://localhost:13004/` devuelve 200 con encabezado y ejemplos actualizados. Es una comprobación HTTP de contenido, no revisión visual.
- `git diff --check` correcto. No se repitieron baterías de motores, juegos ni bases de datos. No se modificaron backend, reglas, gestión docente ni datos de ningún entorno.

## Revisión visual pendiente

No se dispone en esta sesión de herramientas específicas para inspeccionar o accionar el navegador integrado y sus viewports. La herramienta que abre una URL no permite revisar la página. Se respeta la instrucción del usuario: no se usaron control de escritorio, control de ChatGPT, Opera GX ni automatizaciones alternativas.

Queda pendiente la revisión del usuario en escritorio y móvil: proporciones de las ilustraciones y tarjetas, legibilidad de ejemplos, altura de secciones, reflujo y foco de enlaces. No se presenta el render HTML de pruebas como revisión visual.

Para revisar, abrir `http://localhost:13004/`, recorrer las secciones de juegos y pasos y comprobar «Elegir qué practicar», «Iniciar sesión» y «Crear cuenta». No es necesario iniciar partidas ni repetir los recorridos de juego ya aprobados.