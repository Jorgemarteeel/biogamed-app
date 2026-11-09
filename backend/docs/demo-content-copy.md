# Copia de contenido real a la demo y preparación compacta

8 de noviembre de 2026. Cambios sin commit ni push, pendientes de aprobación del usuario. Solo la demo se ha modificado. No se han ejecutado migraciones, seeds ni reconstruido copias históricas.

## Aislamiento comprobado

- Origen habitual: contenedor `biogamed_backend` → `biogamed_db`, base `biogamed`, identificador de clúster `7675366743089238050`, rol existente `admin`. Todas las conexiones del procedimiento al origen se abrieron con `default_transaction_read_only=on` y transacción REPEATABLE READ. Revisión `a21b30c41d52`.
- Destino: proyecto `biogamed_docente_demo`, backend/DB propios, base `biogamed_demo`, rol de demo existente, identificador `7703905352215838755`, volumen `biogamed_docente_demo_demo_data`. Frontend loopback 13004, backend 18004. Revisión `b31c40d52e63`, sin cambios.
- El importador no conoce una conexión de origen: solo lee su exportación offline. Rechaza el clúster habitual incluso si se le indica otra base en él, exige nombre e identificador de destino y solo acepta las cinco tablas de contenido. No se modificó la configuración de conexiones de ningún servicio.
- Verificación final del origen: contenido y huellas de usuarios/partidas/respuestas idénticos antes/después; 5 usuarios, 371 preguntas, 19 partidas y 111 respuestas. Fuente sin asignaturas ni bloques; 4 categorías sin bloque; 211 preguntas sin categoría, incluidas las 2 retiradas iniciales. No se interpretan errores de consulta como datos ausentes.

## Copia completa y restauración real previa

Copia duradera fuera del contenedor y repositorio:
`C:\Users\Jorge\Documents\BioGaMed-backups\20261108-demo-real-content-200212\demo-before-real-content.dump`

SHA-256: `C4EFF580CBAB3AB1EA9945B8D3984111F9CF7AACBA35C004EA4815912F44205E`. El archivo externo coincide por SHA-256 con el volcado restaurado. `pg_dump -Fc`, salida del comando, tamaño, `pg_restore --list` y `pg_restore --exit-on-error` correctos. Backend demo detenido para bloquear escrituras mientras se hacía la copia y la importación; después reanudado.

Restauración realizada en una base nueva, sin sobrescribir ninguna: `demo_review_archive_20261108_200214`. Conservada como archivo de escenarios técnicos, dentro del clúster aislado demo y sin conexión de las aplicaciones a ella. Se comprobaron 3 cuentas ficticias, 302 preguntas, 49 partidas y 288 respuestas; igualdad completa de preguntas y huellas de todas las tablas de actividad con la demo previa. Se conserva también `demo_content_test_20261108_201021`, segundo clon nuevo usado para probar el importador. No se han borrado bases ni volúmenes.

La copia completa es de la demo y contiene sus cuentas ficticias. Desde la habitual se exportaron exclusivamente `subjects`, `content_blocks`, `categories`, `topics` y `questions`; las verificaciones de actividad solo guardan recuentos y huellas agregadas. No se copiaron sus usuarios, hashes de contraseña, tokens, partidas, respuestas ni progreso al destino. Las cuentas y credenciales demo existentes no se han alterado.

## Herramienta y repetibilidad

Se revisaron `seed.py`, `tools/assign_trivial_metadata.py` y `tools/diagnose_trivial_sources.py`. No resuelven una copia entre bases: los dos primeros importarían/asignarían desde raw data, por lo que no se ejecutaron. Se reutilizaron sus parsers y comparación de contenido para cotejar la procedencia.

Nueva utilidad `tools/copy_demo_content.py`: recibe snapshot JSON y plan explícito fuera de Git, conexión de destino por entorno, `--expected-database`, `--expected-system` y reporte externo; `--apply` es obligatorio para confirmar la transacción. Por defecto revierte la transacción de ensayo. PostgreSQL puede reservar secuencias durante un ensayo con inserciones aunque se reviertan las filas: nunca se presuponen IDs consecutivos.

Solo inserta contenido nuevo con IDs de destino y remapea sus FK. No combina por nombres ni sobrescribe registros ajenos. Guarda correspondencias y huellas en `demo_import.state`, un registro auxiliar exclusivo de la demo, sin cambios en modelos o migraciones de aplicación. Serializa importaciones con un bloqueo transaccional. Repetir el mismo origen/plan valida sus filas y no duplica nada; un origen o registro ya importado que haya cambiado provoca rechazo y rollback para revisión explícita. Las relaciones provisionales autorizadas se registran separadamente y solo admiten categorías antes sin bloque y preguntas activas antes sin categoría.

Antes de confirmar comprueba copias completas, campos de pregunta (opciones, solución, alternativas, letras, dificultad, retirada) y huellas de todas las tablas de actividad demo. La retirada técnica usa IDs y huellas completas del snapshot verificado, no filtros por nombres del frontend. Solo cambia `is_active` de esas preguntas: mantiene IDs, relaciones, cuentas, sesiones, respuestas y snapshots históricos.

## Contenido y correspondencias verificadas

Se copiaron 7 Topic, 4 categorías y 371 preguntas, de las que 369 están activas. Las preguntas de origen 1 y 2 conservan `is_active=false` y su Topic de prueba. Mapas de categorías: 1 → 21, 2 → 22, 3 → 23, 4 → 24. Mapas de Topic: 1 → 11, 2 → 12, 3 → 13, 4 → 14, 5 → 15, 6 → 16, 7 → 17. Ejemplos de preguntas origen → destino: 1 → 303, 2 → 304, 371 → 673. Las 371 correspondencias individuales constan en el reporte, no se deducen de intervalos ni de nombres.

Huellas SHA-256 coincidentes de la exportación y del destino normalizado (IDs remapeados y únicamente las relaciones provisionales documentadas revertidas para comparar):

| Tabla | Filas copiadas | SHA-256 común |
| --- | ---: | --- |
| subjects | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| content_blocks | 0 | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` |
| categories | 4 | `512044c5375feec4ec57c16040df1cde31d3e1ca6fcfab655eb811cd9b65b52f` |
| topics | 7 | `c2c8c548727c6d6969a6ff63aab9ebcafe6d1afa8c7f2c06807ebe6d564469a6` |
| questions | 371 | `886d3752b7281ab172fd3eeb85abf7a5eb8285095b1ab06163c5554f2ce3edbc` |

Archivos externos de auditoría en `C:\Users\Jorge\Documents\BioGaMed-backups\20261108-demo-real-content-200212`: `source-content.json` (contenido protegido, nunca Git), `content-plan.json` (criterio/IDs), `restore-list.txt`, `restore-verification.json`, `import-report.json` (mapas completos y huellas), `recheck-report.json` (ensayo repetido: cero inserciones), `source-after-verification.json` y `demo-after-verification.json`. Credenciales y volcado quedan fuera de Git.

## Clasificación oficial frente a provisional

No existe jerarquía oficial en el origen: cero asignaturas y bloques. Se han conservado nombres de las cuatro categorías reales, pero vincularlas a un bloque en demo es provisional. Las 209 preguntas activas de Pasapalabra estaban sin categoría; las dos preguntas retiradas iniciales continúan sin clasificar.

Únicamente en demo se ha creado la asignatura **Práctica biomédica** (ID 4), con descripción visible «Organización provisional de demostración · pendiente de validación académica». No supone una clasificación curricular aprobada:

| Bloque demo | Categorías | Evidencia y disponibilidad real |
| --- | --- | --- |
| Preguntas del Trivial original (5) | Erlenmeyer (21), Jeringuilla (22), Linfocito (23), Macrófago (24) | Cotejo unívoco de las 160 preguntas con los 16 TXT de `raw_data/Trivial_Pursuit/Juego_tipo_Trivial_Pursuit/Preguntas/`, reutilizando `read_sources` y `compare_content`. Cada categoría: 40 preguntas Trivial, diez por nivel 1–4; cero Pasapalabra. |
| Fisiología (6) | Vocabulario de fisiología (25) | 107 preguntas Pasapalabra cotejadas unívocamente con `raw_data/Fisio-Quiz-III.html`: enunciado, solución y letra; dificultad sin clasificar. Cero Trivial. |
| Inmunología (7) | Vocabulario de inmunología (26) | 102 preguntas Pasapalabra cotejadas unívocamente con `raw_data/Inmuno-Quiz.html`, mismo criterio; dificultad sin clasificar. Cero Trivial. |

Las rutas y hashes de los originales y los IDs cotejados quedan en el plan/reporte. No se crearon preguntas, se duplicaron para alcanzar 40 ni se amplió dificultad/categoría. Los números de disponibilidad son cantidades de preguntas. Queda por decidir con criterio académico la jerarquía oficial, especialmente el vínculo de las categorías heredadas y los bancos de Pasapalabra; la agrupación de demostración no se escribe en la habitual.

## Escenarios técnicos conservados

La base restaurada conserva el conjunto técnico íntegro y activo. En la demo de revisión se retiraron sus 302 preguntas. Estado final: 4 asignaturas, 7 bloques, 26 categorías, 17 Topic, 673 registros de pregunta y 369 preguntas activas; exactamente las mismas 3 cuentas demo, 49 partidas y 288 respuestas, con huellas de actividad idénticas tras la revisión de interfaz.

**Límite del modelo:** asignaturas, bloques y categorías no tienen archivo/retirada. Las tres asignaturas técnicas y sus categorías vacías siguen visibles porque tienen relaciones que hay que preservar; quitarlas requeriría borrar relaciones o ampliar el modelo. No se han ocultado por nombre, ID ni excepciones frontend. El historial previo también conserva sus etiquetas ficticias. Para la revisión principal, acceder directamente a la asignatura de contenido auténtico que se enlaza debajo.

## Revisión y límites

- 8 pruebas de la utilidad: guardas de origen/destino y whitelist, huellas de opciones/alternativas/retirada, ensayo real PostgreSQL en clon, rollback, copia íntegra, repetición sin duplicados, conflictos de edición, rechazo de reclasificación de retiradas y actividad preservada. Aviso de deprecación Starlette/httpx ya existente; no se cambian dependencias.
- 35 pruebas frontend relacionadas (panel/preparación/landing), tipos y lint sin avisos, compilación de producción independiente correctos. Tras sustituir solo el icono decorativo de categorías por el SVG científico existente se repitieron las 13 pruebas de catálogo y tipos/lint; no los motores. Se conservan las mejoras pendientes de Trivial y su componente jugable compartido.
- Navegador integrado aislado, APIs específicas de pestaña/DOM y viewport: 1366×768 escritorio y 390×844 móvil. Cuenta ficticia verificada. Revisados selección por teclado, resúmenes, reapertura de contenido/juego/modo, categorías auténticas, Trivial de 10 por nivel, Pasapalabra con 107, estado vacío de juego incompatible, atrás, acceso directo y recarga, invitado/dificultad conservados, foco SELECT tras cambiar dificultad y Tab hasta el inicio. No se crearon partidas ni salas.
- Escritorio: documento 1351 px de ancho = clientWidth, sin desbordamiento horizontal. Página de 822 px, acción local entre y=626 e y=670 dentro de los 768 px visibles. Se permite el pequeño desplazamiento para enlaces secundarios; no se oculta contenido.
- Móvil: documento/clientWidth 375 px en viewport de 390 px, cero elementos que sobrepasen el borde derecho, alto 1156 px; desplazamiento natural y acción accesible con Tab. No se promete que quepa toda la preparación sin scroll.
- El primer intento sobre la pestaña antigua devolvió conexión rechazada; la pestaña nueva en localhost funcionó al quedar listos los servicios. No se usaron escritorio, aplicación completa ni Opera GX. La captura de página móvil completa no está soportada por esta herramienta: se guardó captura de viewport y mediciones DOM, sin reconstruir imágenes.
- No se han verificado teclado virtual físico, zoom nativo al 200 %, lector de pantalla ni ajuste nativo de movimiento reducido. Celebración y pantallas jugables no se han cambiado ni se han repetido partidas completas. La revisión del agente no sustituye la aprobación visual del usuario.

## Cómo revisar

1. `http://localhost:13004/practicar?subject=4` con una cuenta demo existente; también accesible desde **Práctica biomédica** en el panel.
2. Elegir bloque/categoría y juego. Al elegir, la tarjeta grande pasa a resumen con «Cambiar». Pasapalabra hace lo mismo tras elegir modo.
3. Trivial: bloque 5, cualquiera de sus categorías, nivel 1–4 → diez preguntas; sin filtrar → hasta diez de cuarenta.
4. Pasapalabra: Fisiología o Inmunología, «Sin clasificar» o sin filtrar → 107 o 102, suficientes para ambos modos. Inicio local requiere nombre; online solo crea sala al pulsar explícitamente su botón.
5. «Explorar otros contenidos» mantiene los bancos auténticos sin imponer cobertura alfabética. El Topic de prueba retirado carece de preguntas activas y no aparece como banco jugable.

Capturas y métricas de revisión fuera de Git: `C:/Users/Jorge/Documents/Playground/academic-compact-desktop.png`, `academic-compact-mobile.png` y los dos JSON de métricas correspondientes. La demo queda disponible. No se ha hecho commit, push ni creado rama.

## Integración autorizada — 9 de noviembre de 2026

El usuario autorizó conservar la utilidad, sus pruebas y esta documentación en un commit local específico. Las cifras y comprobaciones anteriores corresponden a la copia del 8 de noviembre; no se ejecutó de nuevo la importación al preparar el commit. Exportaciones, manifiestos privados, credenciales y copias completas permanecen fuera del repositorio. La presentación posterior agrupa las asignaturas técnicas mediante configuración explícita exclusiva de demo (véase frontend/docs/academic-practice.md); no cambia las relaciones preservadas aquí.
