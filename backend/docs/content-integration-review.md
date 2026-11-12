# Revisión integrada de gestión y práctica — 11 de noviembre de 2026

Revisión funcional en demo aislada, sin cambios de código ni migraciones. Git inicial
main limpio, HEAD a6b414090a3856fd3ced38bae08ca12893ecd7f1 y ocho commits locales.
Conexión comprobada: db/biogamed_demo, clúster 7703905352215838755, revisión
d53e62f74085. Sin acceso de escritura a la habitual.

| Recorrido | Resultado | Evidencia de integración |
|---|---|---|
| Crear jerarquía y editar los tres nombres/descripciones | Correcto en navegador con administrador ficticio | Asignatura 5, bloque 8, categoría 27; formularios y confirmaciones de guardado |
| Guardar con cuenta docente | Correcto en navegador | Docente Demo BioGaMed edita descripción de categoría 27; sin cambiar roles |
| Crear preguntas manualmente | Correcto en navegador | Trivial 676 y Pasapalabra 677, temática existente 1, dificultad 2 |
| Importar ambos CSV | Correcto en navegador | Trivial 678; Pasapalabra 679–718 (40 registros), misma categoría y temática |
| Validación inválida | Rechazo sin inserciones | Nueva validación del CSV de Pasapalabra: 40 duplicados, sin comprobante; total final 718 preguntas |
| Descubrir contenido como estudiante | Correcto en navegador | Panel → asignatura → bloque → categoría: 2 Trivial y 41 Pasapalabra; selección explícita antes de iniciar |
| Trivial completo | Correcto en navegador | Sesión 57, 2/2 aciertos; resultado e historial personal |
| Pasapalabra local completo | Correcto en navegador | Enfrentamiento 30, sesión registrada 58; 40 respuestas por controles del juego, empate normal 20–20; invitado sin sesión personal |
| Estudiante sin gestión | Correcto en navegador y API | Pantalla Acceso no permitido; GET /subjects y PATCH a recurso inexistente devuelven 403 con token estudiante |
| Editar/retirar utilizada | Correcto en navegador | 676 cambia enunciado y solución de Alfa a Beta; retirada confirmada |
| Partida nueva sin retirada | Correcto en navegador y consulta posterior | Disponibilidad 1; sesión 59 completada con [678], 1/1 aciertos |
| Reactivar | Correcto en navegador y API | 676 activa; disponibilidad Trivial vuelve a 2 |
| Historial tras editar y renombrar | Correcto en navegador y contraste de datos | Sesión 57 conserva enunciado original y Alfa; sesiones 57/58 y las 40 copias del enfrentamiento 30 idénticas a referencia anterior |

La jerarquía fue renombrada una segunda vez después de finalizar las partidas
mediante la API autorizada de demo; después se compararon íntegramente las
respuestas JSON del historial y las copias/contextos persistidos (sin reconstruirlos).
Relaciones y estados conservados. Nombres actuales: DEMO INTEGRADA 20261111 final,
DEMO Integración bloque final, DEMO Integración categoría final. El docente añadió
posteriormente la descripción final de categoría; el historial guarda los nombres
anteriores terminados en revisada/revisado.

## Actividad ficticia retenida

- Asignatura 5, bloque 8, categoría 27. No se creó otra temática: se utilizó la
  temática 1 de demostración ya existente, sin deducir clasificación por nombre.
- Preguntas nuevas 676–718: 43 en total, 2 Trivial y 41 Pasapalabra. La 676 queda
  editada y reactivada. Todas identificables por DEMO INTEGRADA.
- Sesiones 57 y 59 Trivial, 58 Pasapalabra; enfrentamiento local 30.
- CSV, credenciales, capturas y copias de contraste se mantuvieron fuera del repo.
  No se crearon cuentas ni se cambiaron roles. No se borró actividad histórica.

## Comprobaciones y límites

Recorrido principal funcional en navegador integrado a 1366×768; práctica Trivial,
historial y resultado de Pasapalabra revisados a 390×844. Teclado: Enter para inicio
y finalización de Trivial; foco en las preguntas y formularios, controles nativos
y mensajes observados. Sin desbordamiento horizontal en las vistas móviles
medidas (scrollWidth 375 frente a viewport 390). No se auditó cada pantalla a todos
los tamaños ni se midió de nuevo el juego activo de Pasapalabra en escritorio;
se conservan sus verificaciones de distribución anteriores. Sin auditoría con
lector de pantalla físico ni pruebas de carga.

La selección de archivos del navegador introdujo una espera de unos nueve minutos
en un lote. Se completó con el mecanismo filechooser documentado; no fue un fallo
de importación ni se repitieron confirmaciones. Los desajustes entre nombres AX
y localizadores de summaries se resolvieron usando el texto visible; no se
atribuyen a un fallo de la aplicación sin evidencia adicional.

Pruebas de integración ejecutadas: formularios y partidas reales ficticias de
demo; aserciones HTTP autenticadas de permisos/disponibilidad/conservación del
historial y comparación exacta de copias persistidas. El contraste final por API
no se presenta como revisión visual. Se reutilizan las suites aisladas vigentes;
sin cambios de código no se repiten tipos, lint o compilación.

No se hallaron errores reproducibles de producto que requieran corrección. Puede
darse por cerrada funcionalmente la gestión en el alcance revisado. Esto no
acredita accesibilidad completa, carga, una nueva revisión de salas online ni
clasificación académica de contenido real. La organización usada es enteramente
ficticia. La base habitual mantiene sus migraciones pendientes, sin modificarlas.
Demo disponible en http://localhost:13004/gestion/asignaturas/5/bloques/8/categorias/27;
para estudiante, entrar desde su panel y elegir la asignatura DEMO INTEGRADA.
Sin staging, commit ni push.
