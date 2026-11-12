# Mi cuenta y versión de credenciales

## Alcance y contratos

`/cuenta`, accesible desde el menú de cualquier cuenta autenticada, muestra correo y rol de solo lectura. Permite editar exclusivamente el nombre y cambiar la contraseña. No incorpora recuperación, correo, activación ni refresh tokens.

- `GET /auth/me`: contrato existente, sin hashes ni versión de credenciales en la respuesta.
- `PATCH /auth/me`: `{ "name": "Nombre visible" }`. Recorta espacios exteriores y admite 1–255 caracteres Unicode. Rechaza campos adicionales, incluidos correo, ID y rol. Devuelve el usuario actualizado; la cabecera refresca el nombre. Cancelar no escribe.
- `POST /auth/me/password`: `current_password`, `new_password`, `confirmation`. Rechaza campos adicionales. Contraseña actual incorrecta: 400 (no cierra una sesión válida). Confirmación distinta: 422. Credenciales cambiadas mientras se esperaba el bloqueo: 409. JWT inválido o revocado: 401.

Las operaciones identifican al usuario por la sesión vigente, nunca por un ID enviado en el formulario. El cambio de nombre no actualiza contextos ni copias históricas.

## Contraseñas y compatibilidad

Reproducción con la configuración instalada (Passlib 1.7.4/bcrypt 3.2.2): dos cadenas que comparten los primeros 72 bytes y difieren después verifican el mismo hash bcrypt. También sucede con 36 letras ñ (72 bytes) y sufijos diferentes. Se utilizaron cadenas sintéticas, no contraseñas de cuentas.

Las nuevas contraseñas de registro y cambio usan **Argon2id**, mediante `argon2-cffi==25.1.0`, dependencia mantenida y compatible con Python 3.10, consultada en el registro oficial de PyPI. Parámetros: memoria 64 MiB, tres iteraciones, paralelismo cuatro y sal aleatoria. No se introducen dependencias frontend.

Se conserva el intervalo existente de **8–255 caracteres Unicode**, contado en puntos de código tanto en servidor como en cliente (no unidades UTF-16 ni bytes). Hasta 255 caracteres de cuatro bytes son 1.020 bytes UTF-8; no existe truncamiento a 72 bytes en los hashes nuevos. No se recortan espacios ni se normalizan contraseñas. Los valores que no son Unicode codificable en UTF-8 se rechazan.

Los hashes bcrypt existentes siguen verificándose con Passlib, conservando necesariamente su semántica histórica de 72 bytes: un hash antiguo no contiene información para distinguir sufijos posteriores. No se cambian contraseñas ni se fuerza un restablecimiento. No se transforma el hash automáticamente al iniciar sesión, pues eso fijaría un sufijo que el hash antiguo no puede acreditar. Un cambio explícito y autorizado establece un hash Argon2id nuevo.

## Revocación y concurrencia

La migración aditiva `e64f73085196` (sobre `d53e62f74085`) añade `users.auth_version`, entero no nulo con valor inicial 0. Conserva hashes, roles y relaciones. Su downgrade está bloqueado para no revalidar tokens revocados.

El login firma `auth_version` en cada JWT. `get_current_user` consulta el usuario y compara la versión en cada petición autenticada, además del rol vigente. Un JWT antiguo sin esta propiedad equivale únicamente a versión 0; tras el primer cambio nunca recupera validez. Valores de otro tipo se rechazan.

El cambio bloquea la fila del usuario con `FOR UPDATE`, comprueba la versión que autorizó la petición y la contraseña actual, y guarda hash e incremento de versión en **la misma transacción**. Si otra petición ya confirmó el cambio, se rechaza la obsoleta. Un fallo de commit revierte ambos campos.

Se revisaron los puntos de decodificación JWT: las rutas protegidas de juegos, contenidos, administración, historial y seguimiento usan la dependencia común. No se encontraron conexiones WebSocket ni otras conexiones persistentes autenticadas. Los comprobantes firmados de importación son documentos de validación, no sesiones: su uso sigue exigiendo una sesión vigente independiente.

El cliente elimina su token al recibir confirmación y redirige a `/login?password=changed`, con aviso de inicio de sesión necesario. Las otras sesiones reciben 401 en su siguiente petición protegida. No se añaden tokens ni contraseñas a logs o almacenamiento de recuperación. Una petición ya autorizada no se cancela retroactivamente; las solicitudes posteriores se validan con la nueva versión.

## Migración y demo (12 de noviembre de 2026)

Se verificó la conexión de la demo `biogamed_docente_demo`, base `biogamed_demo`, host interno `db` y la identidad del clúster antes de escribir. Se detuvo su backend durante la copia y migración.

Se creó una copia completa externa al repositorio con `pg_dump -Fc`, se verificaron archivo, SHA-256 y `pg_restore --list`, y se restauró realmente en una base aislada nueva. Allí se ensayó la migración antes de aplicarla **solo a la demo**. Los registros de la copia se conservan fuera del repositorio; no se incorporan volcados ni credenciales.

Se conservaron **5 usuarios, 718 preguntas, 59 sesiones y 351 respuestas**. Las huellas de los campos de usuario preexistentes coincidieron antes y después de migrar; todos partieron de versión 0. La comprobación posterior de cambio de contraseña modificó únicamente el hash y versión de la cuenta ficticia existente elegida. Se verificó que preguntas, partidas y respuestas no cambiaron. El nombre usado en la revisión se restauró.

La base habitual no se ha migrado ni escrito. Siguen pendientes allí `c42d51e63f74`, `d53e62f74085` y esta `e64f73085196`; necesitan su propio procedimiento autorizado de copia y ensayo antes de desplegar este código.

## Comprobaciones y límites

- 25 pruebas backend relacionadas (cuenta, administración y asignaturas): permisos propios para los tres roles; nombres y campos adicionales; registro, login, contraseñas largas/Unicode, bcrypt heredado; contraseña actual incorrecta, confirmación, revocación de tokens anteriores con/sin versión, nuevo login, segundo cambio y rollback. Se prueba el rechazo de tokens revocados en cuenta, historial, contenido, administración y Pasapalabra.
- Una prueba con PostgreSQL aislado real: dos cambios concurrentes con la misma versión, exactamente uno confirmado y otro 409; comprobación Alembic sin diferencias de modelo.
- Pruebas frontend de nombre, cancelación, validaciones, doble envío, errores y cierre de sesión; regresión relacionada de edición de metadatos. Tipos, lint y compilación correctos.
- Demo: cambio real autorizado por API con la cuenta ficticia existente, contraseña anterior rechazada, dos JWT anteriores revocados y nuevo login correcto. La credencial final se conserva únicamente en el archivo privado de acceso existente, fuera del repositorio.
- Navegador integrado: entrada desde el menú por teclado, datos de solo lectura, nombre guardado y reflejado en cabecera, cancelación y error accesible; escritorio 1366×768 y móvil 390×844 sin desbordamiento horizontal. Se observó que recargar la sesión anterior tras el cambio dirige al login y que el nuevo acceso funciona.
- **Comprobación manual del usuario y aprobación visual:** el usuario confirma el cambio de contraseña desde el formulario, el acceso con la nueva, el rechazo de la anterior y la pérdida de acceso de otra sesión. Esta evidencia es una revisión manual comunicada por el usuario, distinta de las pruebas automatizadas y de la revisión del navegador integrado. Queda cerrado el pendiente manual de envío del formulario.
- No se realizaron pruebas de carga ni auditoría exhaustiva de tecnologías de apoyo. El coste de Argon2 debe dimensionarse al preparar producción. No se repitieron baterías de los motores ni se generaron partidas.

Revisión: [Mi cuenta en la demo](http://localhost:13004/cuenta), entrando con una cuenta ficticia existente. Guardar nombre y Cancelar son explícitos; el cambio de contraseña cierra todas las sesiones. La aplicación habitual requiere primero las migraciones pendientes y no es el destino de estas pruebas.

### Ajuste de organización de Mi cuenta

La pantalla conserva una columna y dos tarjetas: **Datos de la cuenta** (correo y rol de solo lectura, nombre con Guardar/Cancelar) y **Seguridad**. El enlace superior es «Volver al panel» con destino explícito `/dashboard`.

Guardar nombre se deshabilita si el valor recortado está vacío, supera 255 puntos de código o coincide con el guardado. Cancelar restaura el nombre y su foco. Son formularios independientes: Enter no envía el otro formulario.

Seguridad comienza plegada. «Cambiar contraseña» abre los tres campos y enfoca la contraseña actual. Cada campo dispone de mostrar/ocultar con etiqueta específica y estado accesible, sin enviar el formulario. Se conservan autocomplete y pegado. «Guardar nueva contraseña» es la acción explícita. Cancelar limpia campos, error y visibilidad; cierra y devuelve el foco al botón de apertura. Un error recuperable conserva el formulario y sus valores. Las contraseñas permanecen solo en el estado de memoria del formulario, nunca en almacenamiento del navegador.

Comprobaciones de este ajuste: cinco pruebas frontend de cuenta (incluidas independencia, validación del nombre, visibilidad, cancelación, discrepancia entre contraseñas y error recuperable), tipos y lint. Navegador integrado a 1366×768 y 390×844: sin desbordamiento horizontal; apertura, controles de visibilidad con teclado, validación nativa vacía y foco de apertura/cancelación correctos. Se comprobó el nombre inválido y Cancelar sin guardar. Se reutiliza la comprobación anterior de guardado del nombre. Durante este ajuste no se cambiaron contraseñas. Posteriormente el usuario confirmó la revisión manual del envío y la revocación descrita arriba. No hay cambios de API, seguridad, migraciones ni dependencias respecto a la primera entrega.
