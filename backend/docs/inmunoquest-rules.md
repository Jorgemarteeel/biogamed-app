# Motor interno InmunoQuest: manual, modalidad básica

Base comprobada: main, 3423055041abd829d70ed9a5e639e7c3bf08948f, árbol limpio al comenzar. La gestión común ya tiene commit y no se mezcla ni se vuelve a confirmar. Cierre autorizado como entrega independiente del motor, sus pruebas y documentación; sin push.

## Fuente, versión y decisión de meta

Se ha leído Manual.docx, «INMUNOQUEST · Manual de instrucciones», Nov 16, 2026. Referencias: §3/3.1 (recorrido, ciclo, anillos), §5 (2–6 participantes y orden), §6.1–6.3 (turnos, casillas y evaluación humana), §7 (final) y §8 (variantes excluidas).

Reglas: `inmunoquest-manual-20261116-basic-v1`. Tablero: `inmunoquest-manual-board-v1`. No se importa el JSON de efectos HTML porque sus bancos y efectos son incompatibles. Se reutilizan la separación de dominio, estados/eventos inmutables, avance acotado y los límites de anillo comprobados; la fórmula explícita del manual construye de forma pura las 140 casillas, sin leer archivos durante las acciones. Los originales y su corrección histórica Jeriguinlla→Jeringuilla permanecen intactos.

**Decisión aprobada por el usuario el 18 de noviembre de 2026:** meta 140. Un avance que llega o supera 140 se limita a esa casilla y declara victoria. No exige tirada exacta ni pregunta final. La 139 se resuelve normalmente (Macrófago, nivel 4). Esta decisión sustituye expresamente la frase de §7 que menciona alcanzar/superar 139; la pregunta final aparece en §8 como variante y no se incorpora. No queda un bloqueo de meta en esta versión. Modificar posteriormente esta decisión requerirá otra versión, sin reinterpretar estados guardados. `FINISH_CELL = 140` es la única definición operativa de la meta para esta versión: validación de posiciones, reconocimiento de victoria y avance acotado la reutilizan; no es una opción configurable de partida. `START_CELL = 1` centraliza igualmente la salida.

## Estado y acciones

Identificadores de participante opacos, únicos y no vacíos, independientes de cuentas/nombres. Entre 2 y 6, cerrados en la preparación del estado. No decide identidad, invitaciones, modalidad ni permisos.

| Fase | Acción y resultado |
|---|---|
| ORDERING | `order_rolls`: una tirada 1–6 por cada participante pendiente. Orden descendente; solo empates vuelven a tirar. Se conservan los grupos de prioridad ya establecidos. |
| READY | `advance`: tirada de avance suministrada por el servidor futuro; posición limitada a 140 y resolución de llegada. |
| ROLL_AGAIN | Jeringuilla: `advance` otra vez, en el mismo turno, resolviendo la nueva llegada. No se requiere pregunta ni se genera dado automáticamente. |
| VIRUS_ROLL | `retreat_virus`: otra tirada 1–6 para retroceder, con límite inferior 1. No aplica la casilla de destino. Termina el turno y activa al siguiente, sin penalización futura. |
| CHOOSE_BANK | Cerebro: `choose_bank` entre los cinco bancos. Mantiene el nivel de la casilla; antes de elegir no hay requisito de pregunta. |
| QUESTION | `evaluate(True/False)` recibe únicamente una evaluación humana confiable. Acierto deja READY al mismo participante; fallo mantiene posición y activa al siguiente. |
| FINISHED | Victoria del participante activo; no permite nuevas acciones. |

Linfocito, Macrófago, Bazo, Matraz y ADN generan un requisito de banco/nivel, no una carta real. Niveles: 1–57/1; 58–98/2; 99–123/3; 124–139/4; 140 es meta. ADN ahora plantea pregunta y no avanza tres. Jeringuilla no es un banco de preguntas. Se evalúa una vez por fase; no hay comparación automática de texto ni cronómetro.

El estado contiene posiciones y grupos de orden, índice activo, fase, elección de Cerebro cuando procede y versiones. Orden final, requisito de pregunta y ganador se derivan, evitando copias independientes contradictorias. Las transiciones devuelven otro estado y una tupla de eventos. No se mutan estado ni diccionarios de tiradas. Los desempates se entregan por rondas completas de todos los grupos aún empatados: convención técnica de entrada, sin prioridad por plaza ni límite arbitrario de rondas.

## Ejemplos y límites geométricos

- Salida 1 + 5 → Jeringuilla 6: pide otra tirada. Un 4 lleva a Linfocito 10; tras acierto, otro 4 lleva a Jeringuilla 14 y vuelve a pedir dado sin cambiar de jugador.
- Jeringuilla 6 + 2 → Virus 8: pide otra tirada; un 6 retrocede a 2, no plantea su pregunta y pasa el turno. Cuando vuelva el turno propio se tira desde 2, sin saltarlo.
- Cerebro 95: elegir ADN pide inmunoterapias de nivel 2, sin elegir carta todavía.
- ADN 9: pregunta de nivel 1, sin desplazamiento automático.
- 138 + 1 → 139: pregunta normal, sin victoria. 139 + 1 o 139 + 6 → 140 y victoria directa.

El manual contempla Jeringuillas consecutivas, pero en su ciclo están a ocho casillas y un d6 no permite llegar directamente de una a otra. El motor vuelve a resolver cada llegada y permite nuevas Jeringuillas en el mismo turno; se prueba el recorrido válido con una pregunta acertada intermedia. No se inventa un dado de ocho ni se altera el tablero para simular la condición imposible. Análogamente, el primer Virus es 8 y la tirada máxima 6 deja como mínimo 2: el límite defensivo a salida está implementado, pero ningún Virus real del tablero permite rebasarla. No se fabrica un Virus en una casilla anterior.

## Compatibilidad y futura persistencia (no implementada)

`trivial_movement.py` y sus pruebas son compatibilidad del HTML para el servicio interno `trivial_persistence` y las copias existentes. No hay partida pública operativa que se cambie en esta entrega. No se modifican esos estados, versiones o servicios ni se crean nuevos mediante el motor manual. Los dos tipos de estado se rechazan mutuamente. El nuevo motor no está importado por routers ni por servicios de persistencia; no constituye un segundo modo jugable.

La integración posterior deberá:

- Guardar versión de reglas/tablero y estado coherente del manual; ampliar las validaciones actuales de 1–4 local/2–4 online a la preparación acordada de 2–6 y registrar rondas/desempates. Conservar lectura/ejecución histórica solo de versiones que lo necesiten; no usar flags de penalización heredados en el manual.
- Adaptar bancos: las copias antiguas restringen a Linfocito/Macrófago/Matraz/Jeringuilla y no admiten Bazo/ADN. El formato abierto y la respuesta de referencia requieren otra versión de copia. No reconstruir copias ausentes ni modificar las existentes.
- Sustituir para las partidas nuevas el plazo obligatorio de 60 segundos de las presentaciones antiguas: deadline_at actualmente no es nulo y tiene una restricción de fecha. El manual no debe pasar por ese contrato ni recibir un plazo inventado. Conservar tiempos históricos.
- Reutilizar autenticación vigente, bloqueo de partida, versión y recibos idempotentes. La futura capa autenticada obtendrá al actor desde get_current_user, comprobará participante/turno/lector y generará los dados del servidor. Ningún endpoint permitirá al cliente decidirlos. El motor puro no autoriza ni protege por sí solo reintentos de red. Sus acciones siempre afectan al participante activo derivado del orden: no reciben un actor autenticado ni demuestran quién las solicita. Rechaza identidades/órdenes/índices incoherentes y acciones incompatibles con la fase; la autorización de la cuenta y del lector corresponde al futuro servicio.
- Asociar la evaluación humana con la presentación y el contenido congelado. La fase QUESTION de este motor expresa una necesidad de pregunta, no demuestra que alguien haya recibido una carta.

No se añade ahora esquema, migración, selector/consumo/repetición de cartas, permisos del lector, salas, cronómetro, resultados históricos nuevos o frontend. No se alteran Trivial individual, Pasapalabra ni la gestión de contenidos.

## Verificación

Pruebas puras sin conftest del backend, sin importar app.main/database/FastAPI/SQLAlchemy. Dependencias ya instaladas de una imagen existente; proceso temporal Docker con red deshabilitada, sistema de archivos de solo lectura y /tmp efímero. No arranca ni cambia servicios de habitual/demo/revisión, no recibe conexiones de base ni secretos. El intérprete auxiliar local no tenía pytest: se utilizó la imagen existente sin instalar nada.

Casos: cinco bancos, límites de anillo, Jeringuilla repetida en turno y Jeringuilla→Virus, segunda tirada de Virus y ausencia de resolución/penalización, elección de los cinco bancos en Cerebro, evaluación correcta/incorrecta, 2–6 participantes, múltiples grupos de empate y desempates repetidos, dados/estados/acciones inválidos, versiones incompatibles, llegada exacta/exceso a 140, pregunta normal en 139 y rechazo de acciones tras victoria. Barrido de todas las posiciones 1–139 y seis tiradas; inmutabilidad y resultados/eventos reproducibles. Se ejecuta también la suite histórica de movimiento sin cambiar sus expectativas.

Desde backend, en un entorno de pruebas con pytest/pydantic ya instalados:

```text
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest --noconftest -p no:cacheprovider tests/test_inmunoquest_rules.py tests/test_trivial_movement.py -q
```

Evidencia anterior: **110 casos aprobados** en 2,63 s, incluidos los casos históricos; no eran 110 casos nuevos.

## Revisión y cierre del motor (18 de noviembre de 2026)

Se vuelve a contrastar el manual original (apartados 3, 5, 6 y 7–8) con las decisiones aprobadas. No se encuentra un defecto funcional en las reglas. Se elimina la repetición del valor de meta en la implementación mediante FINISH_CELL, sin cambiar el comportamiento ni la versión. No se reorganizan servicios ni el resto de la arquitectura.

Evidencia nueva: **127 pruebas aprobadas en 2,28 s** mediante el mismo comando anterior, en una ejecución temporal con red deshabilitada y montaje del código de solo lectura, sin servicios ni conexiones de base de datos. Comprende las 110 pruebas anteriores, ejecutadas de nuevo, y **17 casos adicionales**: matriz de cinco acciones en las siete fases (incluida FINISHED), orden de turnos distinto del de plazas, contenido y atribución de eventos de pregunta/Virus/evaluación/victoria, meta fija de la versión, seis identidades inválidas y estados sin participante activo válido o con ganador inactivo.

Se comprueban estáticamente las dependencias del módulo: solo dataclasses, enum y collections.abc; no importa HTTP, ORM, archivos, reloj ni generadores de azar. Las entradas de dado son datos suministrados: la generación segura y los permisos quedan para la integración. Se conserva y prueba el rechazo entre estados del HTML y estados del manual, sin reinterpretación histórica.

No hay cambios en esquema, datos, servicios existentes o entornos de aplicación. La revisión no constituye una prueba de persistencia, concurrencia, permisos del lector o partida jugable: esas piezas aún no están integradas.

No hay pantallas que revisar ni cambios frontend que requieran tipos/lint/compilación. Las pruebas de persistencia PostgreSQL anteriores no se repiten ni se presentan como validación de una integración que todavía no existe.
