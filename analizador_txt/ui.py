import json
import streamlit as st
from parser import read_lines, parse_line
from reports import export_json
from spec_loader import load_spec, pick_movement_schema
from rules_engine import validate_record


def run_ui():
    st.title("Analizador TXT - Validación de registros de longitud fija")

    # elegir tipo de archivo (MO, MD, ME, FL)
    file_type = st.selectbox("Tipo de archivo", ["MO", "MD", "ME", "FL"])

    uploaded = st.file_uploader("Sube un archivo .txt", type=["txt"])
    if uploaded is None:
        st.info("Sube un archivo para comenzar la validación.")
        return

    # Leer contenido en memoria (preview) para demo; producción debería usar stream
    raw = uploaded.read().decode("utf-8", errors="replace")
    content = raw.splitlines()
    st.write(f"Lineas detectadas: {len(content)}")

    if len(content) == 0:
        st.warning("Archivo vacío")
        return

    # Para MO usamos specs/mo-file
    if file_type == "MO":
        spec_path = "analizador_txt/specs/mo-file/m.json"
        base_spec_path = "analizador_txt/specs/mo-file/base.json"
        shared_path = "analizador_txt/specs/mo-file/shared_rules.json"

        # Detectar movimiento usando la primera línea (suponemos uniformidad)
        detected = pick_movement_schema(spec_path, content[0])

        # Si no se detecta o no es M/L, usar únicamente la base.json (modo genérico)
        if detected is None:
            st.info("No se detectó movimiento M/L en la primera línea; usando 'base.json' para validar todas las líneas.")
            movement_spec_file = base_spec_path
        else:
            # st.info(f"Movimiento detectado: {detected}")
            # según movimiento elegir archivo específico (M -> m.json, L -> l.json)
            if detected.startswith("M"):
                movement_spec_file = "analizador_txt/specs/mo-file/m.json"
            elif detected.startswith("L"):
                movement_spec_file = "analizador_txt/specs/mo-file/l.json"
            else:
                # Si se detecta otra clave distinta de M/L, también caer en modo base
                st.info(f"Movimiento detectado '{detected}' no es M/L; usando 'base.json' para validación.")
                movement_spec_file = base_spec_path

        # cargar spec final
        spec = load_spec(movement_spec_file)

        # procesar cada línea: parsear y validar
        # en los fields [] de spec esta el layout correspondiente al movimiento, armado de la base y del json del movimiento
        results = []
        for i, line in enumerate(content, start=1): #recorre cada linea
            parsed = parse_line(line, {"fields": spec["fields"]}) #extraer el valor de cada posición
            # detectar movimiento por línea
            detected_line = pick_movement_schema(movement_spec_file, line)
            res = validate_record(parsed, spec.get("rules", []), raw_line=line, fields=spec.get("fields"))
            # res ahora es dict {errors:[], passes:[]}
            errs = res.get("errors", [])
            passes = res.get("passes", [])
            results.append({"row": i, "movement": detected_line, "ok": len(errs) == 0, "errors": errs, "passes": passes})

        st.write("### Resumen por línea")
        # construir mapa de campos para buscar start/end
        field_map = {f.get("name"): f for f in spec.get("fields", [])}

        for r in results:
            if r["ok"]:
                st.success(f"Linea {r['row']} (mov: {r.get('movement')}): OK")
            else:
                st.error(f"Linea {r['row']} (mov: {r.get('movement')}): {len(r['errors'])} errores")
                
                for e in r["errors"]:
                    rid = e.get("rule_id")
                    ef = e.get("field")
                    message = e.get("message")
                    value = e.get("value")
                    expected = e.get("expected")

                    start_end = None
                    if ef:
                        # ef normalmente es el name del campo; buscar en field_map
                        fmeta = field_map.get(ef)
                        if not fmeta:
                            # intentar extraer nombre desde rule_id tipo 'field.<name>.*'
                            if isinstance(rid, str) and rid.startswith("field."):
                                parts = rid.split(".")
                                if len(parts) >= 2:
                                    candidate = parts[1]
                                    fmeta = field_map.get(candidate)
                        if fmeta:
                            start_end = (fmeta.get("start"), fmeta.get("end"))

                    # si la regla es generada tipo 'field.<name>.*' y tenemos metadata, mostrar el id numérico del campo
                    display_id = rid
                    if isinstance(rid, str) and rid.startswith("field.") and ef:
                        fmeta = field_map.get(ef)
                        if not fmeta:
                            parts = rid.split(".")
                            if len(parts) >= 2:
                                candidate = parts[1]
                                fmeta = field_map.get(candidate)
                        if fmeta and fmeta.get("id") is not None:
                            display_id = fmeta.get("id")

                    if start_end:
                        st.write(f" - Regla {display_id} (mov: {r.get('movement')}) (pos {start_end[0]}-{start_end[1]}): {message} => valor: {value} esperado: {expected}")
                    else:
                        st.write(f" - Regla {display_id} (mov: {r.get('movement')}): {message} => valor: {value} esperado: {expected}")

        # ofrecer un único botón para descargar el JSON de resultados
        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        st.download_button("Descargar JSON", data=json_str, file_name="results.json", mime="application/json")

    elif file_type == "MD":
        # Para MD usamos specs/md-file
        spec_path = "analizador_txt/specs/md-file/inicios.json"
        base_spec_path = "analizador_txt/specs/md-file/base.json"
        # Detectar movimiento usando la primera línea (I, C, S)
        detected = pick_movement_schema(spec_path, content[0])

        if detected is None:
            st.info("No se detectó tipo de movimiento (I/C/S) en la primera línea; usando 'base.json' para validar todas las líneas.")
            movement_spec_file = base_spec_path
        else:
            # según tipo elegir archivo específico
            if detected == "I":
                movement_spec_file = "analizador_txt/specs/md-file/inicios.json"
            elif detected == "C":
                movement_spec_file = "analizador_txt/specs/md-file/compensaciones.json"
            elif detected == "S":
                movement_spec_file = "analizador_txt/specs/md-file/fswaps.json"
            else:
                st.info(f"Tipo de movimiento detectado '{detected}' no es I/C/S; usando 'base.json' para validación.")
                movement_spec_file = base_spec_path

        # cargar spec final
        spec = load_spec(movement_spec_file)

        # procesar cada línea: parsear y validar
        results = []
        for i, line in enumerate(content, start=1):
            parsed = parse_line(line, {"fields": spec["fields"]})
            detected_line = pick_movement_schema(movement_spec_file, line)
            res = validate_record(parsed, spec.get("rules", []), raw_line=line, fields=spec.get("fields"))
            errs = res.get("errors", [])
            passes = res.get("passes", [])
            results.append({"row": i, "movement": detected_line, "ok": len(errs) == 0, "errors": errs, "passes": passes})

        st.write("### Resumen por línea")
        field_map = {f.get("name"): f for f in spec.get("fields", [])}

        for r in results:
            if r["ok"]:
                st.success(f"Linea {r['row']} (mov: {r.get('movement')}): OK")
            else:
                st.error(f"Linea {r['row']} (mov: {r.get('movement')}): {len(r['errors'])} errores")
                for e in r["errors"]:
                    rid = e.get("rule_id")
                    ef = e.get("field")
                    message = e.get("message")
                    value = e.get("value")
                    expected = e.get("expected")

                    start_end = None
                    if ef:
                        fmeta = field_map.get(ef)
                        if not fmeta:
                            if isinstance(rid, str) and rid.startswith("field."):
                                parts = rid.split(".")
                                if len(parts) >= 2:
                                    candidate = parts[1]
                                    fmeta = field_map.get(candidate)
                        if fmeta:
                            start_end = (fmeta.get("start"), fmeta.get("end"))

                    display_id = rid
                    if isinstance(rid, str) and rid.startswith("field.") and ef:
                        fmeta = field_map.get(ef)
                        if not fmeta:
                            parts = rid.split(".")
                            if len(parts) >= 2:
                                candidate = parts[1]
                                fmeta = field_map.get(candidate)
                        if fmeta and fmeta.get("id") is not None:
                            display_id = fmeta.get("id")

                    if start_end:
                        st.write(f" - Regla {display_id} (mov: {r.get('movement')}) (pos {start_end[0]}-{start_end[1]}): {message} => valor: {value} esperado: {expected}")
                    else:
                        st.write(f" - Regla {display_id} (mov: {r.get('movement')}): {message} => valor: {value} esperado: {expected}")

        json_str = json.dumps(results, ensure_ascii=False, indent=2)
        st.download_button("Descargar JSON", data=json_str, file_name="results_md.json", mime="application/json")

    else:
        st.warning("Soporte actual sólo para MO y MD (implementación mínima).")

run_ui()
