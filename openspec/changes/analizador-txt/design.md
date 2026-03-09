## Context

Basado en la propuesta, construiremos una aplicación en Python que valide archivos planos (.txt) de longitud fija. El usuario cargará un archivo y seleccionará el tipo de archivo (MO, MD, ME o FL). El programa, al parsear cada línea, debe determinar automáticamente el tipo de movimiento de esa fila (por ejemplo M1, M2, etc.) leyendo posiciones/indicadores definidos en la especificación; según el movimiento detectado aplicará la estructura de reglas correspondiente. El sistema procesará línea por línea, aplicará reglas (posición inicio/fin, longitud, formato, enumerados, rangos, regex) y devolverá un reporte estructurado de errores por fila.

Restricciones importantes tomadas del proyecto: usar `pydantic` para modelos y validaciones, y `streamlit` para la interfaz de usuario. Los archivos MO tienen 852 posiciones por fila y ~71 reglas que varían según el tipo de movimiento; los otros tipos (MD, ME, FL) también usan registros de longitud fija aunque sus longitudes y número de movimientos varían.

## Goals / Non-Goals

- **Goals:**
- Proveer una aplicación Streamlit que permita validar archivos .txt de longitud fija por tipo. La aplicación debe detectar automáticamente el tipo de movimiento de cada fila y aplicar las reglas específicas de ese movimiento.
- Implementar un motor reutilizable de parseo y validación que use Pydantic y reglas declarativas.
- Generar reportes descargables (CSV/JSON) y una vista interactiva con filtros y conteos.
- Diseñar la app para procesar archivos grandes sin consumir memoria excesiva (streaming/lectura por bloques).

**Non-Goals:**
- Integración automática con pipelines externos en esta primera entrega (se podrá añadir luego).
- Reemplazar sistemas ETL existentes; la app entrega validación y reportes, no ingestión en producción.

## Decisions

1. Arquitectura por capas (módulos):
   - `parser`: lectura por líneas, soporte de lectura por bloques/streaming y conversión de línea fija a `dict` según mapa de campos. Además debe incluir un subcomponente de detección de tipo de movimiento que, usando la especificación (posiciones, valores o patrones), clasifique cada fila en su movimiento correspondiente.
   - `specs` (datos): archivos de especificación por capability en `openspec/specs/` que describen campos (start, end, length, name), reglas por tipo de movimiento y reglas/criterios de detección de movimiento. Cada spec deberá incluir un bloque `movement_detection` que indique cómo identificar el movimiento (p. ej. posición X contiene valor Y, regex en posiciones A-B, o una prioridad de checks).
   - `models`: modelos Pydantic que representan una fila validada o un objeto intermedio. Se usarán tanto modelos estáticos (cuando aplique) como modelos dinámicos generados en tiempo de ejecución para movimientos con esquemas conocidos. El pipeline será: parsear línea → detectar movimiento → mapear a modelo/reglas del movimiento → validar.
   - `rules_engine`: aplica reglas declarativas (tipo, regex, rango, longitud) sobre el `dict` parseado y/o sobre el `pydantic` model.
   - `ui` (streamlit): componentes para carga y selección de tipo de archivo; la UI mostrará el conteo y distribución de movimientos detectados, previews por movimiento y permitirá, si se desea, anular manualmente la detección para una fila o un lote (modo experto). También mostrará filtros y exportación de resultados.
   - `reports`: generación y exportación de reportes (CSV/JSON) y resumen estadístico.

   Razonamiento: separar responsabilidades facilita pruebas, mantenimiento y reutilización en otros contextos (CLI, integración en pipelines).

2. Representación de campos, detección y reglas (declarativa):
   - Cada especificación (por capability, p. ej. `mo-file`, `md-file`) incluirá un archivo JSON/YAML que declara:
     - los campos con `name`, `start`, `end`, `length` y metadatos opcionales (`type`, `allowed_values`, `regex`, `alignment`, `pad_char`, `usage`),
     - las reglas por tipo de movimiento (lista de reglas identificadas: id, descripción, campo, check-type, params),
     - y un bloque `movement_detection` que describe cómo identificar cada tipo de movimiento (por ejemplo: check en posición X=="M1", regex en posiciones A-B, valores en un set, o una lista de checks ordenados por prioridad).
   - El `rules_engine` iterará las reglas del movimiento detectado y devolverá errores estructurados.

   Razonamiento: incluir la lógica de detección en la spec permite que el parser clasifique filas sin código nuevo y hace la solución más configurable.

3. Reglas posicionales comunes (aplican a todos los archivos y movimientos):

- Cada campo declara `length` esperada. Si el valor real ocupa menos posiciones, el resto debe estar rellenado según `pad_char` (p. ej. espacio `' '` o `'0'`). Las specs incluirán `usage` que describe reglas como "rellenar con 0 únicamente" o "rellenar con espacios".
- Campos alfanuméricos deben estar alineados a la izquierda (`alignment: left`); los numéricos a la derecha (`alignment: right`). El `rules_engine` validará la alineación y que los caracteres de relleno son los esperados.
- Validación de longitud total de fila: cada spec declarará la longitud fija total del registro (por ejemplo 852 para MO). El parser verificará que la línea tenga al menos esa longitud; si es mayor, se marcará como error; si es menor, se considerará inválida salvo que las reglas indiquen que el resto se debe interpretar como padding de espacios —esto se definirá por spec.
- Reglas de formato y padding: para campos numéricos que deben ir rellenados a la izquierda con ceros, la spec indicará `pad_char: '0'` y `alignment: right`. Para campos alfanuméricos que deben ir con espacios al final, `pad_char: ' '` y `alignment: left`.
- Las reglas posicionales están normalizadas: cada regla puede referirse a un campo por `name` o por rango posicional; el motor reportará `field`, `expected_length`, `actual_length`, `padding_ok` y mensajes claros cuando haya discrepancias.

   Razonamiento: estandarizar estas reglas evita duplicidad y hace que las especificaciones por movimiento sean compactas (solo describen diferencias o reglas adicionales).

3. Uso de Pydantic:
   - Pydantic se usará para: coerción de tipos, validaciones básicas (longitudes, formatos) y para definir modelos reutilizables.
   - Para reglas complejas o condicionales por movimiento, el `rules_engine` se encargará; Pydantic complementa con validaciones de esquema.

   Razonamiento: Pydantic ofrece validaciones expresivas y mensajes de error claros; sin embargo, no siempre cubre reglas posicionales complejas por sí solo.

4. Procesamiento y rendimiento:
   - Lectura por streaming (iterator sobre líneas) y procesamiento por lotes (p. ej. 1k líneas por lote).
   - La UI mostrará un modo "preview" (primeras N líneas) y un modo completo que procesa en background y actualiza progreso.
   - Para archivos muy grandes se ofrecerá un modo de exportar resultados parciales (por lote) y/o ejecutar validación en background con descarga posterior.

5. Formato de salida de errores (contrato):
   Cada error será un objeto con campos: `row_number`, `raw_line`, `file_type`, `movement_type`, `field`, `rule_id`, `message`, `severity`.

6. Tests y calidad:
   - `pytest` con fixtures que contienen ejemplos válidos e inválidos por movimiento.
   - Tests unitarios para `parser`, `rules_engine` y `models`.

## Riesgos / Trade-offs

- [Rendimiento] Procesar archivos grandes puede consumir CPU/IO y memoria si no se maneja en streaming → Mitigación: diseñar pipeline por lotes y limitar operaciones en memoria; permitir ejecución asíncrona o por worker.
- [Complejidad de reglas] 71 reglas para MO con variaciones por movimiento pueden hacer complejas las reglas declarativas → Mitigación: crear un esquema de pruebas exhaustivo; dividir reglas en categorías reutilizables; documentar cada regla con ejemplos.
- [Modelo dinámico] Generar modelos Pydantic dinámicos por movimiento agrega complejidad de mantenimiento → Mitigación: preferir modelos estáticos cuando sea posible y usar `rules_engine` para lógica dinámica.
- [UX] Mostrar muchos errores en la UI puede ser abrumador → Mitigación: agrupar/sumarizar errores y mostrar primero los tipos de error más críticos; permitir paginación y filtros.

## Migration Plan

1. Entrega inicial: empaquetar la aplicación como un módulo Python y un entrypoint `streamlit run` (README con instrucciones). Lanzamiento en un entorno controlado.
2. Validación con archivos de ejemplo y corrección de reglas observadas en producción.
3. Si se integra en pipelines: añadir hooks de salida (CSV/JSON) y un pequeño CLI para ejecución no interactiva.
4. Monitoreo y métricas: tiempo de procesamiento por archivo, memoria usada, ratio de filas inválidas.

## Open Questions

- ¿Puedes proporcionar ejemplos (líneas) para los otros tres tipos de archivo (`MD`, `ME`, `FL`)? Has indicado que `MD` puede tener hasta 4 tipos de movimiento —por favor aporta ejemplos para cada movimiento si es posible.
- ¿Cómo se determina actualmente el tipo de movimiento en tus archivos? ¿Hay una posición fija que lo identifique (p. ej. campo en posiciones 1–2) o se usa una combinación/patrón más complejo? Esto definirá el formato del bloque `movement_detection` en las specs.
- ¿Deseas soporte para reglas dependientes entre campos (p. ej. si campo A tiene X, entonces campo B debe cumplir Y)? Si sí, indicar ejemplos.
- ¿Cuál es el volumen típico de filas por archivo y el tamaño en MB? Esto ayudará a ajustar el enfoque de rendimiento y el tamaño de los lotes de procesamiento.


---

Archivo creado a partir de la propuesta: `openspec/changes/analizador-txt/design.md`.
