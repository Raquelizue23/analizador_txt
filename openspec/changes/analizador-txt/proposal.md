## Por qué

Los equipos reciben archivos planos (.txt) de cuatro tipos diferentes que contienen registros de longitud fija con posiciones específicas para cada campo. Actualmente no existe una herramienta consistente para validar que cada fila cumpla las reglas por tipo de movimiento (p. ej. M1, M2), lo que provoca errores en downstream, retrabajo y falta de confianza en los procesos automatizados. Necesitamos una herramienta de validación rápida y reproducible para mejorar la calidad de datos antes de su ingestión.

La solución propuesta es una aplicación en Python (interfaz web ligera con Streamlit) que permita a un usuario cargar uno de los cuatro archivos, seleccionar el tipo de archivo y —cuando corresponda— el tipo de movimiento dentro del archivo, y ejecutar una validación basada en reglas (posición inicio/fin, longitud, formato, valores permitidos, etc.).

## Qué cambia

- Añadir una aplicación en Python que permita cargar y validar archivos .txt de longitud fija desde una interfaz Streamlit.
- Implementar un motor de parsing y validación basado en reglas configurables por tipo de movimiento.
- Definir modelos de datos y validaciones con Pydantic para garantizar tipos y formatos.
- Producir reportes de validación (errores por fila y resumen) y exportarlos (CSV/JSON).
- Añadir especificaciones formales (specs) por capacidad para dejar requisitos claros y consultables.
- Incluir pruebas automatizadas que validen el motor de reglas y los modelos Pydantic.

Ninguno de estos cambios es BREAKING para código existente (se crea como un módulo/aplicación nueva), salvo que se integre posteriormente en pipelines ya en producción.

## Capacidades

### New Capabilities
- `mo-file`: Reglas y validación para archivos de tipo MO. Cada fila tiene 852 posiciones; existen ~71 reglas totales que varían según el tipo de movimiento (p. ej. M1, M2). Esta especificación detallará los campos (posición inicio/fin), reglas por movimiento y ejemplos válidos/erróneos.
- `md-file`: Reglas y validación para archivos de tipo MD.
- `me-file`: Reglas y validación para archivos de tipo ME.
- `fl-file`: Reglas y validación para archivos de tipo FL.
- `parser-core`: Núcleo de parseo que convierte una línea fija en un objeto intermedio (dict) según un mapa de campos por especificación.
- `pydantic-models`: Modelos Pydantic que representen una fila validada y expresen restricciones de tipo y formato reutilizables por el `rules-engine`.
- `rules-engine`: Motor de validación que aplica las reglas (posición, longitud, expresiones regulares, rangos, enumerados) por tipo de movimiento y retorna errores estructurados.
- `streamlit-ui`: Interfaz de usuario en Streamlit para subir archivos, seleccionar tipo, ejecutar validación y mostrar/exportar resultados.
- `validation-reporting`: Generación de reportes (resumen y detalle por fila) y exportación a CSV/JSON.

### Modified Capabilities

- Ninguna por ahora.

## Impacto

- Código nuevo: se añadirá un paquete/módulo Python (p. ej. `analizador_txt/`) con submódulos para `parser`, `models`, `rules`, `ui` y `reports`.
- Dependencias nuevas: `pydantic`, `streamlit` (y utilidades de test como `pytest`).
- APIs/Integraciones: inicialmente ninguna; la aplicación será autónoma. Si se integra a pipelines existentes, habrá que acordar interfaces de entrada/salida.
- Rendimiento: los archivos pueden ser grandes; el parser y la UI deben manejar streaming/lectura por bloques para no agotar memoria.
- Documentación y ejemplos: incluir ejemplos de líneas válidas/erróneas y una guía de uso en la UI.

---

