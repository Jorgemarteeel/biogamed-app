# Entornos Docker de BioGaMed

## Versión reproducible de reunión — actualización del 16 de noviembre de 2026

La demo actual utiliza **meeting-290c675-058f4833540d**, construida a partir de main `290c6759a883bd26ad150651c65531c9ba588524` más las modificaciones pendientes de navegación. Esta sección sustituye las instrucciones anteriores de arranque de la demo.

- Imágenes: `biogamed-meeting-frontend:meeting-290c675-058f4833540d` y `biogamed-meeting-backend:meeting-290c675-058f4833540d`.
- Proyecto de aplicación: `biogamed_meeting_demo`. La base sigue siendo `biogamed_docente_demo-db-1`, con su volumen original `biogamed_docente_demo_demo_data` y red externa `biogamed_docente_demo_default`. No se publica PostgreSQL ni se comparte su volumen con la habitual.
- Frontend compilado, ejecutado mediante `next start`; backend Uvicorn sin reload y con `--no-proxy-headers`. Un proceso mantiene los límites de autenticación: no es una protección distribuida y los contadores se reinician al reiniciar el proceso. Un futuro proxy necesita configuración explícita; no se confía ahora en cabeceras reenviadas.
- Las fuentes están dentro de las imágenes. No hay montajes de código ni copias manuales posteriores. Se conserva el mismo secreto JWT privado y la misma conexión de demo, solo como variables de ejecución. No están en los contextos de construcción ni en la configuración de las imágenes.
- Incluye las funciones integradas: Trivial individual, Pasapalabra local/online, catálogo académico, gestión, importación y recuperación, seguimiento/CSV, administración y Mi cuenta. Incluye las correcciones pendientes de Volver (origen de navegación e historial) y la consulta docente del tablero.
- Perfil integrado: se excluyen el motor parcial, los modelos/servicios de persistencia y las presentaciones internas del Trivial de tablero, así como sus dos registros de modelos. No se altera el repositorio para excluirlos: la transformación se aplica únicamente a la copia de construcción, de forma explícita en `tools/prepare_meeting_demo.py`. No hay partidas jugables de tablero ni nuevas migraciones en esta imagen.

### Fuentes y reconstrucción exacta

La carpeta privada de versión es:
`C:/Users/Jorge/Documents/BioGaMed-private/demo-releases/meeting-290c675-058f4833540d`.

Contiene las fuentes congeladas, Dockerfiles, Compose, manifiesto de hashes, identificación de imágenes y evidencias técnicas sin tokens. `runtime/backend.env` contiene secretos: es privado, queda fuera de ambos contextos y nunca debe incorporarse a Git ni enviarse a otra persona. Compose necesita soportar `env_file.format: raw` (comprobado con Compose 5.3.1; disponible desde 2.30). Las bases de las imágenes están fijadas por digest; npm utiliza su lockfile y Python sus restricciones fijadas. Reconstruir requiere acceso a los registros de imágenes y paquetes.

El manifiesto registra los 165 archivos utilizados y el estado de Git al congelarlos, incluidos archivos nuevos. Se incluyen las modificaciones de aplicación en layout, pantallas y componentes con Volver, `academic.ts`, `ReturnLink.tsx` y `navigation-return.ts`. Documentación y pruebas pendientes no forman parte del ejecutable. El manifiesto registra también el perfil, exclusiones y hash del preparador.

PowerShell para **reconstruir la misma versión guardada**, sin copiar archivos a contenedores:

```powershell
$release = 'C:\Users\Jorge\Documents\BioGaMed-private\demo-releases\meeting-290c675-058f4833540d'
docker compose -p biogamed_meeting_demo -f "$release/compose.json" build
# Comprobar éxito antes de sustituir los dos servicios; no ejecutar migraciones.
docker compose -p biogamed_meeting_demo -f "$release/compose.json" up -d --no-build
```

Para congelar una **versión futura** desde el árbol de trabajo, con los secretos actuales de la demo:

```powershell
Set-Location C:\Users\Jorge\biogamed-app
python tools/prepare_meeting_demo.py --output-root C:\Users\Jorge\Documents\BioGaMed-private\demo-releases
```

El preparador no modifica contenedores ni bases, no instala ni arranca nada. Rechaza salida dentro del repositorio, destinos de base inesperados, clave inválida y sobrescritura de una versión existente. Es un perfil específico de esta reunión: si cambian las dependencias del Trivial o el esquema requerido, debe revisarse antes de usarlo. Antes de desplegar una nueva versión, repetir copia/restauración y compatibilidad sobre aislamiento; no sustituir la fuente congelada existente.

### Arrancar y detener la demo actual

```powershell
$release = 'C:\Users\Jorge\Documents\BioGaMed-private\demo-releases\meeting-290c675-058f4833540d'
docker start biogamed_docente_demo-db-1
docker exec biogamed_docente_demo-db-1 pg_isready -U demo_admin -d biogamed_demo
# Si aún no está lista, repetir pg_isready antes de arrancar la aplicación.
docker compose -p biogamed_meeting_demo -f "$release/compose.json" start
# Abrir http://localhost:13004

# Parada sin borrar contenedores ni datos:
docker compose -p biogamed_meeting_demo -f "$release/compose.json" stop
docker stop biogamed_docente_demo-db-1
```

No usar `up` sobre el Compose antiguo de `biogamed_docente_demo`: sus servicios de aplicación se mantienen únicamente como respaldo y podrían competir por los puertos.

### Copia, compatibilidad y comprobaciones de esta actualización

- Copia privada: `Documents/BioGaMed-backups/meeting-demo-20261116-191133/demo.dump`; formato pg_dump -Fc, listado comprobado y restauración real en una base aislada nueva. Coincidencia del contenido de las 18 tablas mediante recuentos y huellas completas; el contenedor auxiliar se retiró después de verificar.
- Nuevo backend probado contra esa restauración: todas las columnas de los modelos registrados existen, login, identidad, historial y disponibilidad académica correctos. No requiere migrar: la demo permanece en `e64f73085196`.
- Ambas imágenes construidas correctamente, incluida compilación de producción frontend. Hashes de fuentes y exclusión de secretos comprobados. No se repitieron las baterías de juegos: no hubo cambios en sus fuentes. No son pruebas de carga ni una nueva certificación de seguridad.
- Después de sustituir la aplicación, antes de crear actividad: las 18 tablas seguían exactamente iguales a la copia. Se conservan 5 cuentas y 718 preguntas.
- Verificación autenticada por HTTP: login, identidad, catálogo, preparación académica, inicio, envío, resultado e historial. Única actividad nueva de esta actualización: sesión ficticia **67**, dos respuestas, un acierto, completada. Totales finales: 67 sesiones y 365 respuestas. Se conservan la configuración privada, las cuentas y los datos anteriores.
- HTTP 200 en frontend y API. La comprobación del resultado se hizo con el contrato `is_completed`. No se realizó revisión visual/teclado: no hay herramienta específica de navegador integrado disponible en esta sesión. El usuario puede revisar el recorrido en localhost:13004 con las cuentas de demo existentes.
- La instalación habitual no fue arrancada ni modificada. Sus tres contenedores continúan detenidos.

### Vuelta a la versión anterior sin restaurar la base

Se conservan detenidos `biogamed_docente_demo-frontend-rollback-20261116` y `biogamed_docente_demo-backend-rollback-20261116`, con sus capas anteriores e imágenes originales. No eliminarlos antes de aprobar esta versión. Como no hubo migración, la vuelta no necesita restaurar datos:

```powershell
$release = 'C:\Users\Jorge\Documents\BioGaMed-private\demo-releases\meeting-290c675-058f4833540d'
docker compose -p biogamed_meeting_demo -f "$release/compose.json" stop
docker start biogamed_docente_demo-db-1
docker start biogamed_docente_demo-backend-rollback-20261116 biogamed_docente_demo-frontend-rollback-20261116
```

Para volver a la nueva versión, detener ambos rollback y arrancar los servicios de `biogamed_meeting_demo`. No deben ejecutarse simultáneamente: usan los mismos puertos. No restaurar la copia encima de la base automáticamente ni borrar su volumen. Los datos históricos nuevos, incluida la sesión 67, se conservan también al volver a la aplicación anterior.

## Revisión y limpieza inicial — 16 de noviembre de 2026

Se conserva main y el trabajo pendiente; no se han aplicado migraciones ni cambiado configuración privada. La limpieza se limitó a recursos identificados mediante referencias de contenedores, montajes, configuración Compose y contenido inspeccionado. No se utilizó prune global.

| Entorno | Finalidad y código | Datos y acceso | Estado final |
| --- | --- | --- | --- |
| biogamed-app | Instalación habitual. docker-compose.yml del repositorio. Backend y frontend montan los directorios del repositorio. | biogamed-app_postgres_data; PostgreSQL solo 127.0.0.1:5432; frontend localhost:3000; API localhost:8000. | Arranque comprobado por HTTP y detenido después. |
| biogamed_docente_demo | Demostración inicial; sustituida por las imágenes identificadas de reunión descritas arriba. | biogamed_docente_demo_demo_data; sin puerto PostgreSQL publicado; frontend localhost:13004; API localhost:18004. | Sus tres servicios quedan funcionando. |
| biogamed_clean_20261112 | Ensayo de instalación reproducible; copia independiente del código en Documents/Playground/biogamed-clean-20261112. | Datos sintéticos respaldados y restaurados antes de retirar recursos Docker. | Contenedores, imágenes, red y volumen eliminados. Se conserva la copia de código/configuración en el equipo. |
| Recuperación y loopback restore | Restauraciones históricas aisladas, sin dependencias de habitual o demo. | Copias completas privadas verificadas mediante restauración y comparación del contenido de todas las tablas. | Contenedores, volúmenes y red dedicada eliminados. |
| Online testdb y trabajos académicos | Bases sintéticas y ejecutores de pruebas/construcción. | Bases archivadas; configuraciones, registros y fuentes únicas de las capas archivados fuera del repositorio. | Recursos identificados eliminados. |

La definición Compose determina servicios, imágenes, montajes y puertos. El nombre de proyecto (-p) separa nombres de recursos; por sí solo no garantiza aislamiento si se configuran montajes externos compartidos. En esta revisión se comprobaron montajes y bases diferentes. Ambos entornos conservados están en e64f73085196; no se han aplicado las migraciones internas posteriores de Trivial.

### Evidencia y límites

- Habitual: 5 cuentas, 371 preguntas, 21 sesiones, 141 registros de respuesta y 1 enfrentamiento Pasapalabra. Consultas de lectura y HTTP 200 en frontend y OpenAPI; no se generó actividad en esta base.
- Demo: 5 cuentas, 718 preguntas, 66 sesiones, 363 respuestas y 31 enfrentamientos. Bases habitual y demo tienen identificadores de sistema PostgreSQL diferentes.
- Comprobación autenticada por HTTP en demo: login, catálogo académico, disponibilidad, inicio y finalización de Trivial e historial. Única actividad nueva: sesión ficticia 66, dos preguntas, un acierto. Esto no equivale a una revisión visual ni de teclado mediante navegador integrado, que queda pendiente.
- Cuatro entornos PostgreSQL retirados: ocho bases respaldadas con pg_dump -Fc, listado de archivo comprobado, restauración real en aislamiento y comparación íntegra de tablas satisfactoria. Se guardaron también los roles necesarios para recuperación, en archivos privados.
- Copias y manifiestos privados: Documents/BioGaMed-backups/docker-order-20261116-184616, fuera de Git. No publicar sus archivos: algunos contienen configuración y datos privados.
- Eliminados: 19 contenedores anteriores, 4 volúmenes, 3 redes y 3 imágenes. El contenedor auxiliar de restauración de esta revisión también se retiró al terminar.
- Espacio lógico de Docker: imágenes 6,731 a 5,111 GB; capas de contenedores 1,314 a 1,165 GB; volúmenes 2,475 a 2,243 GB. Reducción aproximada conjunta: 2 GB. Las capas se comparten y el archivo de disco de Docker Desktop puede no reducirse automáticamente. Las copias privadas ocupan espacio adicional fuera de Docker.
- Conservados por falta de procedencia suficiente: dos volúmenes anónimos con node_modules (prefijos 3e42d5f7 y 6bfbbeef) y uno PostgreSQL 15 (7c1611c2). No se arrancó ese PostgreSQL desconocido ni se eliminaron sus datos.
- Caché BuildKit: 104 registros, 25,82 GB. Se conserva porque el historial y las descripciones disponibles no acreditan la pertenencia de cada registro; no se borra por antigüedad o nombre. La cifra marcada como recuperable no es espacio recuperado en esta entrega.

## Arranque y parada de la habitual conservada

PowerShell, sin credenciales ni recreación:

```powershell
# Instalación habitual
 docker start biogamed_db
 docker start biogamed_backend biogamed_frontend
# Detener habitual
 docker stop biogamed_frontend biogamed_backend biogamed_db
```

Esperar a que la base esté disponible y a que el frontend termine de arrancar. Abrir http://localhost:13004 para la reunión o http://localhost:3000 para la habitual. Las sesiones de navegador son independientes de las usadas por herramientas.

start reutiliza los contenedores existentes y su configuración privada. up puede recrearlos: no sustituir estos comandos sin comprobar antes el archivo Compose, proyecto, variables y montajes. Esto afectaba a las imágenes antiguas de la demo; la versión de reunión descrita arriba ya incluye las fuentes en sus imágenes. El Compose de instalación limpia aplica migraciones al arrancar el backend; no usarlo para habitual o demo.

Configuraciones locales identificadas:
- Habitual: C:/Users/Jorge/biogamed-app/docker-compose.yml; variables privadas fuera del repositorio en Documents/BioGaMed-private/habitual.env.
- Demo: C:/Users/Jorge/.codex/visualizations/2026/10/29/01a1875d-353a-7252-b09d-1537fb796b89/biogamed-docente-demo/compose.yml.

## Evitar acumulación en próximos ensayos

- Usar --rm para ejecutores desechables y un bloque try/finally para retirar únicamente sus recursos identificados.
- Etiquetar proyecto, finalidad y propietario; registrar nombres de contenedor, red, volumen y ruta de respaldo antes de escribir.
- Preferir volúmenes con nombre explícito para bases de ensayo. No suponer que un volumen anónimo sin referencias está vacío.
- Reutilizar un entorno de pruebas dedicado cuando proceda, sin reutilizar bases habituales o de demo. No crear una copia completa para cada comando de pruebas.
- Conservar la receta reproducible del ensayo limpio; recrearlo solo cuando se necesite comprobar instalación, con datos sintéticos.
- Para futuros trabajos, separar la caché de construcción de pruebas mediante un constructor identificado si se necesita poder retirarla por proyecto. No se ha creado infraestructura nueva en esta limpieza.

## Cierre de revisión y separación de commits — 17 de noviembre de 2026

La navegación incluida en la imagen de reunión queda registrada en el commit d9bf05d153c5d44bb20dce36a930d36553569006. La imagen conserva su identificador original meeting-290c675-058f4833540d: no se ha reconstruido ni se ha cambiado su manifiesto para aparentar una construcción posterior.

En este cierre se verificó por lectura que los 165 hashes de fuentes de la versión congelada coinciden con las fuentes actuales, aplicando únicamente la exclusión documentada de registros internos del tablero. El hash del preparador también coincide con el registrado al preparar la versión; su sintaxis Python es válida. Se revisaron los archivos candidatos para excluir claves privadas, tokens JWT, conexiones con contraseñas, descargas, copias y temporales. No se ejecutó el preparador, Docker, migraciones ni consultas de base de datos durante este cierre. Se reutilizan la compilación, restauración, compatibilidad y comprobaciones HTTP documentadas arriba; no constituyen una nueva revisión visual. Las pruebas de navegación y sus límites se conservan en frontend/docs/navigation.md.

El preparador y esta documentación se confirman después de la entrega de navegación. Los archivos privados de ejecución, fuentes congeladas y copias permanecen fuera de Git. Esta confirmación no despliega nada y no cambia reglas de Trivial individual, Pasapalabra o del motor de tablero.
