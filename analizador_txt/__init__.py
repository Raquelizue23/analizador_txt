"""Paquete principal para el analizador de archivos de longitud fija.

Los módulos incluidos son:
- parser: lectura y parseo posicional de líneas
- models: modelos Pydantic para registros
- rules_engine: aplicación de reglas sobre registros parseados
- ui: entrypoint Streamlit
- reports: funciones para exportar resultados
"""

__all__ = ["parser", "models", "rules_engine", "ui", "reports"]
