## 1. Entorno y estructura

-- [x] 1.1 Crear estructura de paquete `analizador_txt/` con submódulos `parser`, `models`, `rules_engine`, `ui` y `reports`.
-- [x] 1.2 Añadir `requirements.txt` o `pyproject.toml` con dependencias mínimas (`pydantic`, `streamlit`).

## 2. Parser y especificaciones

-- [x] 2.1 Implementar `analizador_txt/parser.py` con función `read_lines(path, chunk_size=1000)` que itera en streaming.
-- [x] 2.2 Implementar `analizador_txt/parser.py` función `parse_line(line: str, spec: dict) -> dict` que mapea posiciones a campos según la spec.
-- [x] 2.3 Añadir formato de specs (JSON/YAML) en `analizador_txt/specs/mo-file/spec.json` y en `openspec/changes/analizador-txt/specs/mo-file/spec.json`.

## 3. Modelos y validaciones

-- [x] 3.1 Implementar `analizador_txt/models.py` con modelos Pydantic base (`BaseRecordModel`) y ejemplo `MORecordModel`.
-- [ ] 3.2 Integrar validaciones básicas de tipo/longitud en los modelos cuando aplique.

## 4. Motor de reglas

-- [x] 4.1 Implementar `analizador_txt/rules_engine.py` que reciba `dict` parseado y lista de reglas y devuelva errores estructurados.
-- [x] 4.2 Implementar soporte para reglas condicionales (si campo X==V entonces validar Y).

## 5. Interfaz y reporting

-- [x] 5.1 Implementar `analizador_txt/ui.py` (Streamlit) con upload, selección de tipo, ejecución y vista de resultados.
-- [x] 5.2 Implementar `analizador_txt/reports.py` para exportar resultados a CSV/JSON y resumen estadístico.

## 6. Documentación y ejemplos

- [ ] 6.1 Actualizar README con instrucciones de ejecución `streamlit run` y ejemplo de uso.
- [ ] 6.2 Incluir ejemplos de líneas para MD/ME/FL en `openspec/changes/analizador-txt/examples/`.
