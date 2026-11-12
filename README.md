# BioGaMed: instalación nueva con Docker

Este es el punto de entrada para una **base nueva vacía**. No conecta con la demo ni con la base habitual. El `docker-compose.yml` anterior conserva la configuración local histórica y no debe usarse para este ensayo. Para actualizar una instalación con datos, antes se necesita copia, restauración de ensayo y autorización; este procedimiento no los sustituye.

## Requisitos

Docker Engine/Desktop con contenedores Linux y Compose v2 o superior (probado: Engine 29.6.2, Compose 5.3.1), Git y conexión a Docker Hub/PyPI/npm. No hacen falta Python, Node ni PostgreSQL instalados en el host. Imágenes: Python 3.10-slim, Node 20-alpine y PostgreSQL 15-alpine. Versiones efectivas comprobadas: Python 3.10.22, Node 20.20.2, npm 10.8.2 y PostgreSQL 15.18. Es una receta local verificada, no una guía de hosting/producción pública.

Clona el repositorio o extrae una copia de los archivos versionados. Desde su raíz, usa un **nombre de proyecto nuevo** que no coincida con ninguna instalación existente. Los comandos siguientes usan `biogamed_fresh`; puedes revisar los existentes con `docker compose ls`. Puertos predeterminados: frontend 14004 y API 19004, ambos solo en loopback. La base no publica puerto al host. No se montan directorios de código, node_modules, entornos Python ni volúmenes externos.

## Configuración (PowerShell)

Genera `.env` local sin mostrar secretos. No lo añadas a Git. `.env.example` documenta las variables sin valores secretos. Ejecuta esto solo en una copia nueva **sin `.env`**, nunca sobre una instalación existente:

```powershell
if (Test-Path .env) { throw '.env already exists; preserve it' }
function New-HexSecret {
    $bytes = New-Object byte[] 32
    $rng = [Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    return ([BitConverter]::ToString($bytes)).Replace('-', '').ToLowerInvariant()
}
@("POSTGRES_PASSWORD=$(New-HexSecret)", "SECRET_KEY=$(New-HexSecret)",
  'FRONTEND_PORT=14004', 'BACKEND_PORT=19004') | Set-Content -Encoding ascii .env
```

`POSTGRES_PASSWORD` se usa también en DATABASE_URL: usa el secreto hexadecimal generado para evitar problemas de escape URI. `SECRET_KEY` firma sesiones y comprobantes; debe ser independiente de otras instalaciones y conservarse estable. Compose exige ambas variables. Las variables `NEXT_PUBLIC_*` se incorporan al compilar frontend: el Compose pasa el puerto API mediante build arg, por lo que cambiarlo exige reconstruir frontend. CORS se configura con el origen frontend correspondiente. En otro host, adapta las URLs expresamente: localhost designa el ordenador donde está el navegador.

## Instalación, migración y arranque

```powershell
docker compose -p biogamed_fresh -f compose.install.yml build --no-cache
docker compose -p biogamed_fresh -f compose.install.yml up -d --no-build
docker compose -p biogamed_fresh -f compose.install.yml ps
docker compose -p biogamed_fresh -f compose.install.yml logs backend frontend
docker compose -p biogamed_fresh -f compose.install.yml exec backend alembic current
docker compose -p biogamed_fresh -f compose.install.yml exec backend pip check
```

El backend espera a PostgreSQL saludable, ejecuta `alembic upgrade head` y solo arranca si la migración termina correctamente. Frontend ejecuta `next start` sobre la compilación de producción. La compilación utiliza `npm ci` y package-lock; Python utiliza requirements con las restricciones completas de `requirements.lock.txt`, fijadas a las versiones ya verificadas del proyecto, instaladas de nuevo (sin copiar entornos). Para una instalación Python manual usa `python -m pip install -r requirements.txt -c requirements.lock.txt` dentro de un entorno nuevo; no omitas las restricciones.

Abre <http://localhost:14004> y registra una cuenta ficticia para comprobar el acceso. La API está en <http://localhost:19004/docs>. Las cuentas públicas son siempre estudiantes y no aceptan rol. La instalación empieza sin asignaturas, temáticas, preguntas ni partidas; el panel muestra el estado vacío y el acceso alternativo a bancos. No se podrán iniciar juegos hasta preparar contenido. No se ejecutan seeds ni se importan automáticamente archivos originales.

Para detener y volver a arrancar conservando datos:

```powershell
docker compose -p biogamed_fresh -f compose.install.yml stop
docker compose -p biogamed_fresh -f compose.install.yml up -d --no-build
```

No uses `down -v`, prune ni limpiezas globales. El volumen queda asociado al nombre del proyecto; no cambies ese nombre para recuperar una instalación existente. La contraseña de PostgreSQL no se cambia editando `.env` sobre un volumen ya inicializado.

## Primer administrador

Solo en la instalación nueva cuya conexión acabas de verificar:

```powershell
docker compose -p biogamed_fresh -f compose.install.yml exec backend python -m tools.bootstrap_admin
```

Introduce nombre, correo y contraseña (entrada oculta) y confirma esta última. Crea una **cuenta nueva**, nunca promueve ni modifica una existente. Reutiliza las validaciones y Argon2id; la transacción con bloqueo PostgreSQL evita dos altas iniciales simultáneas. Se niega si ya existe cualquier administrador o si el correo ya está registrado. No registra contraseñas y no añade endpoints públicos. El operador con acceso a la consola controla el aprovisionamiento; no ejecutes el comando contra conexiones no verificadas. Después usa el login normal y la administración de roles para gestionar cuentas. El aprovisionador `provision_demo_admin.py` sigue reservado a la demo y no se usa aquí.

## Verificación realizada y límites (12-11-2026)

Copia de `66c56178570493e1fe019b432a6e9dbd93b4e527` mediante git archive, más las correcciones de instalación de esta entrega. Proyecto independiente `biogamed_clean_20261112`, frontend <http://localhost:14004>, backend 19004, red y volumen nuevos. Sin datos/credenciales copiados y sin reutilizar dependencias.

| Paso | Resultado |
| --- | --- |
| Instalación frontend | npm ci limpio: 419 paquetes; compilación Next 16.4.5 y tipos correctos |
| Instalación backend | pip desde cero con restricciones; pip check correcto |
| Migraciones | Las 17 revisiones desde base vacía hasta e64f73085196, sin stamp ni seeds |
| Arranque | PostgreSQL saludable, Uvicorn y Next en modo producción disponibles |
| Autenticación | Alta estudiante y login por HTTP correctos; rol extra rechazado 422; API admin rechazada 403 |
| Panel sin contenido | Login autenticado y panel revisados en navegador integrado; estado vacío y apertura del acceso alternativo correctos; catálogo e historial vacíos verificados por API |
| Primer administrador | Cuenta nueva creada por consola en esta base; rechazo de correo estudiante existente y de segundo bootstrap; estudiante conserva rol |
| Regresiones | 9 pruebas de cuenta y administración en SQLite aislado dentro de la imagen nueva |

Estado final del ensayo: dos cuentas ficticias, cero preguntas/asignaturas/partidas. Los secretos generados quedan fuera del repositorio; no se publica la credencial del ensayo. No se modificó ni reinició la demo ni la instalación habitual.

Límites: no se probaron juegos sin cargar contenido, ni restauración de copias, carga, hosting, correo o CI/CD. npm ci informa ocho avisos moderados; no se ejecutó audit fix ni se alteró el lockfile frontend. Persiste el aviso de TestClient/httpx. Las etiquetas de imágenes pueden cambiar sus parches: la receta fija ramas y dependencias Python/npm, pero no pretende una reproducción binaria con imágenes por digest. Validar otras arquitecturas/SO y actualizar runtimes es trabajo separado. La instalación de producción local no equivale a endurecimiento para exposición pública.

### Persistencia tras reinicio

Se detuvieron y arrancaron exclusivamente los tres contenedores de `biogamed_clean_20261112` con stop y up -d --no-build, conservando el mismo volumen. Coinciden ID, nombre, correo y rol de la cuenta ficticia antes/después; siguen existiendo dos usuarios. Login y /auth/me devuelven 200 y la revisión sigue en e64f73085196. Frontend responde 200 (comprobación HTTP, sin repetir revisión visual). No se repitieron compilación ni pruebas. `biogamed_fresh` es el nombre ilustrativo de los comandos; no había un proyecto activo con ese nombre. Para reiniciar el ensayo existente se usa su nombre real y su directorio de copia, no se cambia el proyecto ni el volumen.
