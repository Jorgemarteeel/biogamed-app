# Participación docente: primera entrega

Consulta global de plataforma para teacher/admin, sin matrículas, grupos ni propiedad académica. GET /monitoring/activity exige require_content_staff; estudiantes 403, sin token 401. UI /seguimiento enlazada desde navegación docente y valida rol antes de consultar. No expone nombres, correos, UUID de cuentas, respuestas, soluciones ni snapshots.

## Definiciones

- Iniciadas: una fila PasapalabraMatch (local u online) o una GameSession sin shared_match_id. Las dos sesiones online nunca duplican el enfrentamiento. Salas sin iniciar excluidas.
- Finalizadas normales/abandonadas/abiertas: estado y desenlace persistidos del match. Consulta de lectura no invoca reconciliación ni modifica reloj: abierta puede estar pendiente de materializar vencimiento.
- Sesión individual heredada completada: normal; incompleta: UNKNOWN, nunca abandono inferido ni abierta confirmada. Estados no reconocidos son desconocidos.
- Cuentas únicas: user_id distintos de las sesiones registradas pertenecientes a las partidas del filtro. Invitados no son cuentas. Tabla muestra números registrados/invitados del match, sin identidad personal.
- Resultados por formato: número de sesiones registradas y recuentos de AnswerLog correctas/incorrectas. Pendientes compartidas según pending_count guardado. Invitado local excluido de agregados de respuestas, sin atribuirlas al anfitrión. No deduplicar respuestas entre sesiones diferentes. Sin logs antiguos no se reconstruye score en respuestas; se informa cobertura desconocida. Incompletas individuales tienen pendientes desconocidas; completadas con todos los logs tienen cero. No se promedian puntuaciones ni tiempos.

## Filtros y contrato

start/end fechas YYYY-MM-DD, ambos opcionales; días inclusivos Atlantic/Canary convertidos a [inicio00:00, día posterior00:00) UTC, respetando horario estacional. Filtra por creación/inicio, no por fecha de respuesta o cierre. Inicio posterior al fin, fecha máxima final, juego inválido o paginación inválida:422. game ALL/TRIVIAL/PASAPALABRA; skip>=0, limit1..100. Tabla orden inicio descendente y referencia estable; total y agregados siempre de todo el filtro, no solo página. UI20 filas; fechas/juego/página conservados en URL, recarga y volver; enviar filtros reinicia página.

Respuesta: scope platform, timezone, unique_registered, started/normal/abandoned/open/unknown, groups (format/sessions/correct/wrong/pending/unknown_sessions), total/items (key/started/game/format/status/registered/guests). unknown_sessions señala cobertura de pendientes incompleta; los recuentos de respuestas son registros existentes, no reconstruidos.

Sin migraciones: todas las fuentes ya existen. Sin motores/reconciliación/snapshots nuevos. Esta entrega no cubre dificultades frecuentes, exportación, administración ni seguimiento docente completo.

## Verificación

Tres pruebas nuevas SQLite en memoria: 401/403/docente/admin, fechas y horario verano, online sin duplicado, abandono, incompleta histórica desconocida, local normal/invitado excluido, respuesta registrada, privacidad, juego/fechas/paginación/vacío y validación. Aviso previo Starlette/httpx conservado. Tipos/lint y compilación frontend comprobados. No se ejecutaron suites completas ni se escribió en habitual. Demo usa sus cuentas y actividad existentes, sin semillas ni cuentas nuevas.

Limitación inicial: agregación en memoria de filas públicas necesarias; paginación limita respuesta pero no materialización interna. Adecuado para revisión funcional, no acredita prueba de carga ni escalabilidad masiva. Los datos reflejan estado persistido, no presencia ni resultado recalculado en vivo. La clasificación provisional de demo permanece intacta.

Demo: http://localhost:13004/seguimiento con cuenta docente existente; menú de usuario → Participación y resultados. Credenciales gestionadas en configuración privada externa, no en este documento.


Revisión integrada realizada con Docente Demo BioGaMed: acceso desde menú docente, consulta global, filtro TRIVIAL mediante Enter (13 registros actuales de demo), URL y recarga conservadas. Escritorio 1366x768 y móvil390x844, sin desbordamiento horizontal de página (clientWidth376 móvil); tabla con desplazamiento horizontal accesible si necesario. No se creó actividad: solo lectura de datos existentes y autenticación de cuenta ficticia. Dos pruebas frontend nuevas aprobadas: rechazo de estudiante sin solicitar informe; filtros/página enviados a API y estados vacío/error. No se presenta como validación de accesibilidad completa, rendimiento, exportación ni dificultades frecuentes. Evidencia de captura fuera del repositorio; aprobación visual pendiente del usuario.

## Presentación y verificación de unidades

Los códigos de formato se conservan en API; solo la interfaz los etiqueta. TRIVIAL-legacy significa ausencia de format_key y también lo generan sesiones actuales: no equivale a antigüedad. Se muestra «Trivial · individual». PASAPALABRA-legacy se muestra «Pasapalabra · sesión individual» (sin enfrentamiento compartido); local-v1 y online-v1 se distinguen. La tabla de detalle llama al fallback legacy mediante game, sin inventar una fecha de corte.

Lectura explícita de la demo: 18 sesiones sin match +20 enfrentamientos locales +9 online =47 partidas; sesiones registradas:18+20+18=56. No hay pares duplicados shared_match_id/user_id. La diferencia de nueve es la segunda cuenta de cada online, no duplicación; invitados locales no son sesiones. La interfaz explica las unidades sin forzar coincidencia.

Resultados por formato en tabla semántica con caption, th scope col/row y región de desplazamiento accesible. Columnas: formato, sesiones registradas, aciertos, fallos, pendientes conocidos y sesiones sin información de pendientes. Fecha de inicio/Hora de Canarias; Finalizada y Estado sin determinar; se mantienen los límites de persistencia/relojes sin reconciliar. Estilos de bordes slate-200, esquinas y sombras reutilizados de ProgressContent.

Verificación proporcional: cuatro pruebas backend y tres frontend aprobadas, reutilizando permisos docente/admin/estudiante, local/invitado, online, abandono y abierta. Casos nuevos: una partida online con dos sesiones y otra individual produce dos partidas/tres sesiones; límites inclusivos de día canario en UTC; completadas sin registros no inventan respuestas y señalan desconocidos; etiquetas, columnas y unidades. Tipos/lint correctos. Revisión integrada con docente demo, escritorio1366x768 y móvil390x844; dos tablas, sin desbordamiento horizontal de página (376px útiles en móvil). Solo lectura de demo, sin escrituras de actividad ni consultas a habitual. No se modificaron motores, contratos internos ni migraciones. Conservados límites anteriores de accesibilidad y rendimiento.

## Filtros de fecha con calendario accesible

No existía un calendario reutilizable en src ni dependencias. Se incorpora react-day-picker 9.12.0 fijado y su lockfile (cuatro paquetes nuevos), siguiendo la documentación oficial https://daypicker.dev/v9/api/interfaces/PropsBase . DayPicker proporciona navegación y selección, locale es, lunes inicial y dropdown de mes/año; no se implementa navegación de calendario propia. Dialog nativo gestiona confinamiento de foco/Escape y devuelve foco al disparador; selección con ✓ y hoy subrayado, además de colores.

MonitoringFilters separa borrador de filtros aplicados. Desde/Hasta manuales dd/mm/aaaa o calendario; borrado explícito; fechas inexistentes y rango invertido presentan error adyacente y bloquean Consultar. Accesos Hoy/7/30 días incluyen el actual en Atlantic/Canary; Todo el periodo limpia ambas. Solo Consultar cambia URL y consulta; cambios pendientes se indican mientras siguen visibles los resultados aplicados. Al enviar se serializa YYYY-MM-DD y se reinicia página. Recarga recupera filtros de URL. No se convierten fechas sin hora a instantes UTC: calendario/aritmética civil local con mediodía, fecha actual calculada mediante Intl en Canarias. Backend mantiene su validación y días inclusivos sin cambios.

Verificaciones proporcionales: seis pruebas relacionadas frontend (tres utilidades fechas y tres seguimiento) aprobadas; entrada estricta, bisiestos, inexistentes, rango, limpieza, intervalos inclusivos, año/mes y horario estacional. Tipos/lint aprobados. Navegador integrado docente demo: quick7 conserva URL/resultados y muestra pendiente; inválida31/02 bloquea; inversión10/11 frente9/11 bloquea; Todo limpia sin consulta; Hoy solo consulta al pulsar; URL y recarga conservadas. Calendario español lunes, teclado flecha/Escape/foco, dropdown mes/año y selección29/02/2024 comprobados. Móvil390x844 diálogo dentro de ancho útil sin scroll horizontal interior; hoy seleccionado blanco/azul con ✓ y subrayado visible. Sin pruebas de lector físico ni teclado virtual real.

La demo instaló lockfile con npm ci y reinició solo Next tras cambiar dependencias. Para desplegar en otros entornos hace falta instalar el lockfile/reconstruir frontend; esta tarea no modificó servicios ni bases habituales. npm audit reportó16 avisos en otras dependencias (incluido Next); no señaló DayPicker y no se aplicó audit fix ni actualizaciones ajenas. Esos avisos requieren revisión separada; no se afirma seguridad de producción. Dependencias y métricas/tabla/permisos permanecen sin otros cambios.

## Aprobación visual del usuario

El usuario revisó y aprobó visualmente seguimiento y calendario y autorizó el commit local de esta entrega. Se reutilizan cuatro pruebas backend del seguimiento, seis frontend relacionadas con fechas/seguimiento, tipos, lint y compilación vigentes, junto a las revisiones integradas de escritorio y móvil documentadas. No se modificó implementación al preparar el commit; se conserva la distinción entre aprobación visual y límites técnicos, incluida la falta de evaluación con lector físico y teclado virtual real. Sin escrituras en bases ni push. La revisión de npm audit es posterior e independiente y no autoriza actualizar dependencias.
