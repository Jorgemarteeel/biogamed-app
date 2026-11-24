# Altas y acceso

El docente importa estudiantes desde **Importar alumnado**. El administrador importa docentes desde **Importar profesorado**. El servidor aplica el rol vigente y fija el rol de las cuentas nuevas. El registro público se ha retirado. Para crear el primer administrador se usa el [procedimiento de consola del README](../../README.md).

El CSV de alumnado también crea matrículas. Si el DNI y el correo identifican a un alumno ya registrado, conserva la cuenta y añade la matrícula cuando falte. Consulta [Ediciones académicas y matrículas](academic-editions.md) para su plantilla y ejemplos. Los pasos siguientes describen el alta de profesorado y la activación común.

## Validar y confirmar

1. Entra con el DNI y la contraseña de una cuenta autorizada. Abre la opción de importación de su panel.
2. Descarga la [plantilla de profesorado](examples/altas/plantilla.csv) o usa el [ejemplo válido](examples/altas/profesorado-valido.csv). El [archivo con errores de profesorado](examples/altas/errores.csv) permite ensayar un DNI inválido, nombre vacío, correo inválido y DNI y correo repetidos. Son datos ficticios para el buzón local.
3. Pulsa **Validar sin guardar**. Corrige los registros señalados y vuelve a validar antes de confirmar. El archivo usa UTF-8, separador `;`, cabeceras `dni;nombre;correo` en ese orden, hasta 100 cuentas y 256 KiB. Si usas una hoja de cálculo, configura DNI como texto antes de pegar los datos. El servidor admite espacios y guiones, conserva los ceros iniciales y comprueba la letra del DNI español. El correo se compara sin distinguir mayúsculas.
4. Confirma la vista previa. Las cuentas se crean en una sola transacción. Cualquier coincidencia con un DNI o correo existente bloquea el lote sin editar cuentas. Repetir la confirmación del mismo archivo con el mismo actor y operación recupera el recibo y no vuelve a enviar invitaciones. La lista **Invitaciones pendientes** permite reenviar si el correo no se entregó o el enlace caducó.
5. Abre el enlace desde el correo. El primer acceso pide elegir y confirmar una contraseña. Abrir el formulario no consume el código. Guardar una contraseña válida activa la cuenta y consume el código en la misma operación. Después inicia sesión con DNI y contraseña. En **Mi cuenta → Seguridad** se puede cambiar la contraseña actual y cerrar las sesiones anteriores.

Las cuentas pendientes carecen de contraseña. El enlace lleva el código en el fragmento de la URL y el servidor conserva su huella, con caducidad de 24 horas por defecto. Un reenvío invalida el enlace anterior. El resultado del correo se registra como aceptado por SMTP o pendiente de reintento. Si el proceso se interrumpe después de guardar el lote y antes de enviarlo, la persona autorizada puede reenviarlo desde el listado.

## Revisar en local

En el entorno aislado [abre BioGaMed](http://localhost:13020/login) y el [buzón local](http://localhost:18021/). Las credenciales ficticias del ensayo están en `accesos-privados.json`, dentro de la carpeta local `BioGaMed_Altas_Revision` del espacio de trabajo. Inicia sesión como administrador para importar profesorado. Usa el enlace recibido para comprobar el acceso docente, o la cuenta docente ficticia ya activada, e importa alumnado. Selecciona en el buzón el mensaje del destinatario correspondiente. Reserva estos CSV de ejemplo para confirmar con el buzón aislado.

## Comprobaciones de esta entrega

- API sobre PostgreSQL y SMTP de captura en el entorno aislado. Se importó profesorado y alumnado con sus roles autorizados, se activaron las cuentas desde el correo de prueba y se comprobó el acceso por DNI. La repetición de los lotes no emitió más mensajes y se verificó el cambio de contraseña con revocación de la sesión anterior.
- Con el buzón detenido, el alta quedó pendiente. Tras reanudarlo se reenvió la invitación y se activó la cuenta. También se comprobó que reenviar y activar invalidan el enlace antiguo. Los CSV de ejemplo se validaron sin guardar.
- 28 pruebas backend relacionadas y 274 frontend aprobadas. Pasaron tipos, lint de los archivos afectados y compilación. La migración PostgreSQL se ensayó desde vacío y desde la revisión anterior con una cuenta y una partida sintéticas. Se conservaron el UUID, rol, hash, versión de credenciales e historial y se comprobó la asociación explícita.
- En el cierre de las altas iniciales se arrancaron los contenedores existentes de revisión. En el navegador integrado se confirmó que ambas rutas de importación redirigen al acceso por DNI cuando falta sesión y que el formulario de activación muestra ambos campos de contraseña al recibir un código de prueba. La inspección de los importadores con una sesión iniciada y el envío de una contraseña nueva desde el navegador quedan pendientes. El recorrido con invitaciones válidas se comprobó por API y SMTP local. Sigue pendiente la entrega con un servidor SMTP real.

## Actualizar una instalación con cuentas existentes

La revisión Alembic `04cf5b8ad91e` añade las columnas de identidad y activación y los recibos de importación. Los usuarios existentes conservan UUID, hash de contraseña, rol, versión de credenciales y relaciones. El DNI inicial de esas filas queda vacío. Antes de servir el nuevo acceso a los usuarios, prepara y verifica el mapeo de identidades con una copia restaurada y un listado de cuentas autorizadas. Con el nuevo esquema aplicado y la aplicación todavía fuera de servicio, asocia cada DNI verificado al UUID exacto en una consola del backend configurada para esa base:

```console
python -m tools.assign_user_dni
```

La herramienta pide el DNI sin eco, rechaza conflictos y conserva contraseña, rol e historial. Comprueba el acceso con cuentas representativas antes de publicar el frontend nuevo. Una cuenta sin DNI asociado no puede iniciar una sesión nueva. Importarla de nuevo por correo no sustituye este procedimiento. Para una instalación nueva, `python -m tools.bootstrap_admin` solicita el DNI verificado y la contraseña del primer administrador.

## Correo en la futura VM

- Configura `BIOGAMED_PUBLIC_URL` con el origen HTTPS que abrirán los usuarios. Ajusta también la URL de API del frontend y sus orígenes CORS según la configuración del despliegue.
- Proporciona un servidor SMTP, puerto, remitente autorizado y, si se necesitan, credenciales privadas. `BIOGAMED_SMTP_SECURITY` admite `starttls` y `ssl`. El modo `none` se utiliza para el buzón local de revisión. Consulta [.env.example](../../.env.example).
- `BIOGAMED_ACTIVATION_TTL_HOURS` vale 24 por defecto. `BIOGAMED_INVITATION_COOLDOWN_SECONDS` aplica una espera de 60 segundos por cuenta entre envíos. La API también limita activaciones y confirmaciones/reenvíos por IP y proceso. Detrás de un proxy, configura el origen de IP confiable y los límites del despliegue. La revisión local utiliza una espera más corta para probar el reenvío.
- Verifica entrega, remitente y enlaces HTTPS en el entorno definitivo antes de importar cuentas reales. Mantén las credenciales SMTP fuera de Git y evita registrar cuerpos de peticiones de autenticación, CSV o fragmentos de enlaces en el proxy o en herramientas de observabilidad.
