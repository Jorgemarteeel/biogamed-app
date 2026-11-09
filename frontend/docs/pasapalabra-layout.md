# Distribución adaptable de Pasapalabra — 5 de noviembre de 2026

Revisión de presentación local y en línea, sobre los cambios pendientes. No se
modifican motor, API, selección, tiempos, turnos, permisos ni dependencias.
Revisión visual del usuario aprobada el 6 de noviembre de 2026: confirmó personalmente la demo y autorizó el conjunto pendiente de Pasapalabra en línea y la distribución adaptable local/en línea. Esta aprobación no amplía las comprobaciones técnicas ni elimina los límites documentados.
Se conserva la aprobación anterior del pulido local y su atribución original.

## Diagnóstico medido

Antes del cambio, a 1366×768 la página local medía 901 px de alto sin respuesta
y 997 px con corrección. Cabecera: 89 px. El bloque de navegación/título situaba
el comienzo del juego en y=213. El panel central ocupaba 511 px; correcciones
se añadían fuera de esa fila y crecían al responder o desplegar anteriores.
Los roscos dependían del ancho, sin presupuesto de altura. En móvil se apilaban
dos SVG grandes. La sala acumulaba márgenes de 24 px y tarjetas en una columna.

También se detectó desbordamiento horizontal al abrir el menú del usuario en
390 px: página de 405 px y menú hasta x=405,5. Se corrigió su anclaje únicamente
dentro de la cabecera de Pasapalabra; el menú abierto termina en x=363 y la
página mide 375 px, sin desbordamiento horizontal.
El indicador de desarrollo de Next tapaba parte de la respuesta en la barra
inferior; se desactiva con `devIndicators:false`, sin afectar reglas del juego.

## Distribución

`PasapalabraLayout.module.css` aplica estilos solo a los componentes de este
juego. `Frame` conserva marca y menú, compacta cabecera y coloca título y retorno
en una fila adaptable. En escritorio, desde 1100 px de ancho y 650 px de alto,
la partida usa `100dvh`; cabecera y título toman su altura natural y el juego
ocupa el resto mediante flex/grid con `min-height:0`. No hay zoom ni transform
para encajar, y ni página, body ni shell usan `overflow:hidden`.

La fila principal contiene ambos roscos y el panel central. Los SVG ocupan el
espacio restante de sus tarjetas conservando proporción; nombres, turno,
relojes y contadores mantienen sus filas. Nombres extraordinariamente largos
siguen completos y accesibles en un área enfocada y desplazable de dos líneas.
No se sustituyen por texto recortado ni por puntos suspensivos.

El enunciado íntegro tiene región con nombre, foco de teclado, barra de
desplazamiento y ayuda visible. El formulario está fuera de esa región: leer
una pregunta extensa no desplaza entrada y botones. Al cambiar de pregunta
la región vuelve al principio, sin mover foco. Actualizar el mismo estado
conserva borrador y posición de lectura.

La última corrección tiene 116 px reservados en escritorio, incluso antes de
responder, para evitar desplazamientos al actualizar. Respuestas y soluciones
extensas permanecen completas en zonas desplazables. El historial anterior se
abre en panel secundario con altura máxima y scroll propio; no aumenta el alto
principal. Puede cerrarse con botón o Escape y mantiene texto introducido,
turno y reloj. La leyenda también es desplegable. Abandono usa diálogo nativo
con foco inicial en Cancelar; Escape devuelve el foco a Abandonar y no envía
comandos. Se comprobó y corrigió ese retorno durante la revisión.

Preparación coloca categoría y dificultad juntas, compacta acciones y mueve
explicaciones a ayuda plegable. Sala separa código/configuración y jugadores
en dos columnas, con confirmación/inicio debajo y ayuda secundaria plegable.
Resultado prioriza ganador, ambos resúmenes y acciones; roscos y respuestas
quedan en detalles cerrados con áreas desplazables. Celebración y CSS de
movimiento reducido se conservan, sin cambiar duración ni cuándo se activa.

En móvil y ventanas reducidas se vuelve al flujo natural: pregunta, relojes y
contadores de ambos, formulario, última corrección y roscos compactos en rejillas
numeradas legibles. No se exige ausencia de scroll vertical. No se impide scroll
de página si faltan espacio o tamaño de texto. En resultado, ambas tarjetas
permanecen juntas con sus contadores en filas para conservar acciones visibles.

## Mediciones en navegador integrado

Demo aislada verificada antes de escribir: conexión efectiva
`biogamed_demo/demo_admin`, volumen `biogamed_docente_demo_demo_data` y puertos
loopback 13004/18004. Se crearon únicamente bancos y partidas ficticios propios;
no se escribieron datos ni migraciones en la base habitual. Dos cuentas demo
autenticadas con almacenamiento separado por origen, en un solo equipo:
docente en localhost y rival en 127.0.0.1.

Se midieron dimensiones del documento y rectángulos de roscos, nombres,
relojes, contadores, pregunta, entrada, botones y corrección; no solo capturas
de la parte superior. En todas las filas siguientes los elementos esenciales
quedaron dentro de la ventana y overflow de html/body siguió siendo `visible`.

| Ventana CSS | Página local | Página online, turno propio | Página online, espera | Borde inferior de corrección |
| --- | --- | --- | --- | --- |
| 1366×768 | 1366×768 | 1366×768 | 1366×768 | 756 px |
| 1440×900 | 1440×900 | 1440×900 | 1440×900 | 888 px |
| 1920×1080 | 1920×1080 | 1920×1080 | 1920×1080 | 1068 px |

Casos: turno de ambos participantes en local; turno propio y rival en línea;
correcciones previas; nombres de más de 120 caracteres; enunciados de más de
3.000 caracteres y solución extensa. Se probaron preguntas completas, sin
modificar las copias de preguntas después de iniciar. Para nombres largos se
usaron participaciones ficticias, sin renombrar las cuentas demo.

A 1366×768 el enunciado largo tenía 2.032 px de contenido en 223 px disponibles.
Ctrl+Fin permitió llegar al final, con scroll de página igual a cero. Responder
reinició únicamente la región para la nueva pregunta; el foco siguió en `word`
y el tablero mantuvo y=118,7 y altura 513,3 px. Abrir historial con borrador
conservó el texto y dejó documento 1920×1080, sin crecimiento.

Las dos preparaciones y la sala se midieron también en las tres ventanas de
escritorio: documento igual a ventana. Botones principales a y=447 en preparación
local, 366 online y 487 en sala. En 390×844 quedaron a y=605, 524 y 723
respectivamente; cancelar sala a y=775, con scroll para ayudas/enlace inferior.
Sala móvil: documento 375×892, permitido y sin desbordamiento horizontal.

Resultados local/en línea, con nombres extensos y ambos resúmenes, permanecieron
dentro de las tres ventanas de escritorio con detalles cerrados; acciones a
y≤614. En móvil, resultado online con acciones hasta y=689 y página 390×844.
Se verificó también finalización normal local con empate y celebración activa,
con acciones móviles hasta y=610.

Móvil local con texto y nombres largos: 390×844, documento 375×1221 por los
roscos e historial secundarios; nombres/relojes entre y=141–230, entrada hasta
y=616 y botones Responder/Pasapalabra hasta y=669. Abandonar hasta y=717.
Móvil online se revisó en ambos estados de turno. Se comprobaron navegación
por Tab, lectura interna, cierre por Escape y conservación de borradores.

## Límites de las comprobaciones

- Zoom nativo al 200 %: el navegador integrado no ofrece API de zoom y sus
  atajos Ctrl+igual no cambiaron viewport ni devicePixelRatio. No se presenta
  esta prueba como zoom nativo aprobado. Se revisó reflujo equivalente con
  viewport 683×384 (mitad de 1366×768): sin scroll horizontal y con Responder,
  Pasapalabra y Abandonar alcanzables y visibles mediante Tab/scroll natural.
  Queda pendiente validar zoom nativo real en un navegador/dispositivo que lo permita.
- Teclado virtual móvil real: no disponible en esta sesión de escritorio.
  Se comprobó altura reducida 390×460 con campo enfocado, borrador conservado
  y Responder visible a y=305. Es una simulación de espacio, no prueba de IME
  de Android/iOS. Queda pendiente esa comprobación física.
- No se usó lector de pantalla físico ni se emuló el ajuste nativo de movimiento
  reducido. Se mantiene la prueba automatizada y el CSS aprobado anterior.
- No se garantiza ausencia de scroll con cualquier longitud, altura, zoom o
  tipografía. En los escritorios medidos sí se verificó sin ocultar contenido.

## Pruebas y demo para revisar

39 pruebas frontend relacionadas aprobadas, incluidos enunciado íntegro en región
de teclado con controles fuera, historial compacto completo, cancelación sin
enviar ni borrar texto, privacidad online, borradores, turnos, errores y
celebración/movimiento reducido. TypeScript, lint y build aprobados. No se
repitieron las baterías del motor o PostgreSQL: no cambian backend ni contratos.

Fixtures propias: banco 7 normal y 8 extenso; partidas 15/16 para diagnóstico,
17/18 para nombres/enunciados y resultados extensos, 19 para celebrar empate,
20 local y 21 online para revisión final; sala 13 para revisar preparación e
inicio. Las escrituras ficticias respetaron el aislamiento antes verificado.
La partida 22 revalidó el último ajuste de corrección extensa en las tres
alturas: todos los campos quedaron dentro de su tarjeta; a 1366×768, el campo
de solución terminó en y=753,3, antes del borde y=756, manteniendo página 1366×768.
Las partidas continúan consumiendo tiempo según el motor; no se han pausado.
La demo sigue disponible y permite crear otra desde sus preparaciones habituales.

## Resultado final y panel sin asignaturas — 9 de noviembre de 2026

Resultado con dos tarjetas iguales centradas y próximas, apiladas en móvil. Reutiliza Rosco con variante final; se neutralizan las columnas 1/3 de la partida activa y las alturas máximas de resultado. Las cifras con símbolos/etiquetas diferencian aciertos, fallos y pendientes; remaining_ms se presenta como «Tiempo restante». Encabezado compacto; ganador/empate/abandono y celebración conservan sus reglas.

FinalAnswers usa únicamente resolved autorizado ya cargado. Lista por jugador/número con enunciado histórico, respuesta y solución cuando existen; campos ausentes indicados sin reconstruir banco. Filtros jugador/estado y diez elementos iniciales con Mostrar más. No deduplica registros. Online filtra también por self_position y no ofrece filtro del rival. Pendientes no se convierten en respuestas. Corrections y sus controles de partida activa se mantienen; resultado no los reutiliza ni anida desplegables.

Panel vacío informa «Todavía no hay asignaturas disponibles. Puedes practicar con los bancos de preguntas existentes» y enlaza principalmente a /dashboard?banks=1#legacy-banks. El enlace nativo recarga esa ruta para que el estado inicial abra realmente los bancos. Subtítulo adaptado por catálogo consultado; página posterior vacía no implica catálogo global vacío. Sin cambios de clasificación, permisos ni datos.

Verificación: 45 pruebas relacionadas aprobadas (presentación, partida activa y catálogo), incluidas normal/empate/abandono, celebración, privacidad online, ausencia de datos antiguos, registros repetidos, filtros y límite inicial. Las 19 de catálogo se volvieron a comprobar tras reforzar la prueba de comportamiento del estado vacío; no sumarlas como casos nuevos. Tipos/lint correctos; compilación independiente aprobada. No motores, migraciones ni escrituras de aplicación nuevas. No se crearon partidas de prueba.

Navegador integrado específico: resultado online existente /pasapalabra/24 (normal) y /26 (abandono sin respuestas), cuenta demo existente. Filtro falladas y Mostrar más comprobados sin consultas nuevas al banco. Escritorio solicitado 1366x768 (herramienta reporta 1366x769 CSSpx), CSSzoom1/visualViewport.scale1: anchuras iguales de 410px, roscos iguales; cero contenedores con overflow:auto efectivo en resultado. Móvil390x844: tarjetas apiladas de igual anchura, página/clientWidth376 por scrollbar, sin overflow horizontal. Respuestas extensas usan scroll de página. Diámetro final común 200px. No se presenta como inspección visual de la cuenta habitual ni de su partida1.

Límites: panel vacío verificado con pruebas de componentes; la demo tiene asignaturas y no se alteró para vaciarla. Partida activa cubierta por regresiones existentes, sin crear actividad para una inspección visual adicional. Empate/datos incompletos cubiertos por pruebas. Persisten límites de lector de pantalla, teclado virtual físico y zoom nativo200%. La aprobación visual corresponde al usuario.

Demo: http://localhost:13004/pasapalabra/24 y /26 con la cuenta demo existente. El acceso habitual /dashboard refleja el estado vacío real con código montado; esta tarea no inicia sesión ni añade actividad allí. Todo pendiente en main, sin staging/commit/push.

## Aprobación posterior — 9 de noviembre de 2026

El usuario confirmó visualmente el resultado y el acceso único del panel y autorizó su inclusión en commits locales junto al recorrido académico. Estado final del panel vacío: botón nativo de apertura/cierre con aria-expanded/aria-controls; selector conservado en DOM para no perder selección; título no interactivo y sin enlace duplicado. Sustituye la solución de recarga por enlace descrita arriba. Se conservan los límites técnicos documentados y la distinción entre revisión autónoma y aprobación del usuario.
