# Ediciones académicas y matrículas

Una cuenta identifica al alumno. Una matrícula vincula esa cuenta con una edición de una asignatura. Se conservan cuenta, credenciales, matrículas anteriores e historial al cambiar el curso habilitado.

## Recorrido docente

En [13020](http://localhost:13020/login), entra con la cuenta docente ficticia. Las credenciales están en el archivo privado local de revisión, fuera de Git.

1. Abre el menú de cuenta y **Gestión docente → Ediciones y matrículas**. Consulta código y curso de destino. Para crear una edición, elige una asignatura existente y un curso de años consecutivos como 2026-2027. La primera edición asigna un código único a la asignatura con letras, números, guion o guion bajo.
2. Abre **Gestión docente → Importar alumnado**. Descarga la plantilla, selecciona el CSV y pulsa **Validar sin guardar**. El enlace contextual a ediciones se abre en otra pestaña.
3. Revisa nombre del archivo, totales y filas. Una persona en varias asignaturas genera una cuenta y varias matrículas. La tabla identifica filas que comparten cuenta y cambios de curso.
4. Pulsa **Confirmar importación** al final de la revisión. El resultado muestra recuentos e invitaciones aceptadas por el correo. **Ver matrículas por edición** abre cada listado, incluyendo la edición anterior si cambia el curso.

La importación siempre matricula y habilita el curso indicado. El CSV requiere las cabeceras dni;nombre;correo;codigo_asignatura;anio_academico, UTF-8 con BOM admitido y separador de punto y coma. Máximo 100 filas y 256 KiB. Una edición inexistente bloquea el lote y nunca se crea por una errata. Los campos técnicos de la plantilla se presentan con etiquetas docentes en los errores.

Si todas las matrículas ya existen y los cursos de destino están habilitados, se muestra **Este lote no requiere cambios** y **Ver matrículas existentes**. Una matrícula existente sin curso habilitado necesita confirmación para habilitarlo. Cambiar el archivo invalida la revisión anterior. Cancelar el selector conserva el archivo ya elegido.

## Archivos de prueba

En 13020 existen Inmunología (INMUNO-DEMO) 2025–2026 y 2026–2027, y Fisiología (FISIO-DEMO) 2026–2027.

| Orden y archivo | Primera ejecución sobre identidades nuevas | Revisión posterior |
| --- | --- | --- |
| [alta-inicial.csv](examples/altas/alta-inicial.csv) | 3 filas, 2 cuentas nuevas y 3 matrículas. Ada comparte cuenta entre las filas 2 y 3, en dos asignaturas. | Reutiliza cuentas y matrículas existentes. Si Ada tiene habilitado un curso posterior, importar este archivo cambiaría de nuevo su curso de Inmunología. Revisa el cambio antes de confirmar. |
| [cambio-de-curso.csv](examples/altas/cambio-de-curso.csv) | Después del inicial, 1 fila para Ada en Inmunología. 0 cuentas nuevas, 1 matrícula nueva y cambio 2025–2026 → 2026–2027. | Si ya se confirmó, muestra que no requiere cambios. La matrícula anterior se conserva. |
| [conflicto-dos-anios.csv](examples/altas/conflicto-dos-anios.csv) | Las filas 2 y 3 piden habilitar dos cursos de la misma asignatura para Ada. Ambas aparecen como error en Curso académico. | Bloqueado en ambos órdenes. Deja una sola fila con el curso que deba quedar habilitado. |

La [plantilla](examples/altas/alumnado-plantilla.csv) está vacía. El archivo anterior alumnado-repetidor.csv contiene dos cursos y ahora constituye un caso de conflicto. Las identidades de los ejemplos ya pueden existir tras una revisión manual. Los recuentos de la vista previa corresponden al estado actual.

## Permisos e integridad

El profesorado tiene alcance global y puede importar alumnado. El administrador importa profesorado con su flujo de tres columnas. Se comprueban DNI, correo, rol y edición al validar y confirmar. La importación conserva los datos y credenciales de una cuenta existente. Una cuenta nueva recibe una única invitación, aunque tenga varias filas.

Estado, matrículas y recibo se confirman en una transacción bajo el bloqueo de escritura existente. El comprobante firmado vincula archivo, actor y curso habilitado revisado. Una confirmación repetida devuelve el recibo y no envía nuevas invitaciones. Un cambio de curso entre revisión y confirmación obliga a validar otra vez. Las peticiones que todavía envíen mode se rechazan para evitar ejecutar otra operación con una interfaz obsoleta.

La base impide repetir matrículas y habilitar dos cursos del mismo alumno y asignatura. La migración aditiva pendiente 15df6c9be207 añade códigos, ediciones, matrículas y recuentos del recibo. Esta revisión de presentación no añade migraciones.

## Evidencia

Se reutilizan las pruebas anteriores de conservación de cuenta, contraseña e historial, activación y reintentos. Se adaptaron al flujo único las pruebas de matrículas y concurrencia. Se añadió cobertura del lote sin efectos, de la matrícula existente aún sin habilitar y de la invalidación de la vista previa al cambiar el archivo.

La revisión actual emplea únicamente 13020 y pruebas sintéticas desechables. La selección automática del curso al iniciar juegos y el traslado de preguntas a ediciones pertenecen a entregas posteriores.
### Comprobación del flujo único

Pasaron 15 pruebas backend de altas y matrículas en SQLite en memoria, y 3 en PostgreSQL desechable que cubren concurrencia real y restricciones de la migración. Tras el último ajuste de las referencias entre filas se repitieron las 9 de matrículas. Pasaron también 26 pruebas frontend del importador, menú y panel, tipos, compilación y lint.

En el navegador integrado con sesión docente se comprobó el acceso desde el menú, Escape con retorno del foco, apertura del selector con ratón y Enter, nombre del archivo, habilitación de Validar, retirada de la vista previa al cambiar de archivo, singular, conflicto con ambas filas y lote sin efectos. Con los ejemplos ficticios existentes se confirmaron cambios de curso en ambos sentidos y se abrieron los listados anterior y nuevo. Ada quedó finalmente habilitada en Inmunología 2026–2027, conservando la matrícula 2025–2026. Las cuentas de los ejemplos ya existían y durante estos cambios no se crearon cuentas ni se enviaron invitaciones nuevas. La conservación de contraseña e historial se cubrió con pruebas automatizadas.

La ventana estrecha y la vista de escritorio se revisaron con el navegador integrado. No se ha probado lector de pantalla ni zoom real al 200 %. El aviso de deprecación de httpx en TestClient sigue presente y no impide estas pruebas.
