from typing import Dict, List, Optional


def validate_record(record: Dict, rules: List[Dict], raw_line: Optional[str] = None, fields: Optional[List[Dict]] = None) -> Dict[str, List[Dict]]:
    """Aplica reglas declarativas a un registro parseado.

    - `record`: dict con pares campo:valor (valores tal como salen del slice posicional)
    - `rules`: lista de reglas traducidas (types: length, enum, cond, info, formatting, padding)
    - `raw_line`: la línea original (necesaria para reglas de archivo/longitud)
    - `fields`: lista de campos (para chequeos de 'required' y formateo)

    Devuelve un dict con dos listas: {'errors': [...], 'passes': [...]}.
    """
    errors = []
    passes: List[Dict] = []

    # Primero aplicar reglas explícitas
    for rule in rules:
        rid = rule.get("id")
        rtype = rule.get("type")
        field = rule.get("field")
        params = rule.get("params", {})
        rule_shared = bool(rule.get("shared", False))

        if rtype == "length":
            # longitud a nivel de registro (field puede ser None)
            expected = params.get("length")
            if expected is not None:
                if raw_line is None:
                    errors.append({"rule_id": rid, "field": field, "message": "No se proporcionó raw_line para comprobar longitud", "status": "error", "rule_source": "shared" if rule_shared else "spec"})
                else:
                    if len(raw_line) != expected:
                        errors.append({"rule_id": rid, "field": field, "message": f"Longitud esperada {expected}, actual {len(raw_line)}", "status": "error", "value": len(raw_line), "expected": expected, "rule_source": "shared" if rule_shared else "spec"})
                    else:
                        passes.append({"rule_id": rid, "field": field, "message": params.get("message", "Longitud OK"), "status": "pass", "value": len(raw_line), "expected": expected, "rule_source": "shared" if rule_shared else "spec"})
        elif rtype == "enum":
            allowed = params.get("allowed", [])
            val = record.get(field)
            if val not in allowed:
                errors.append({"rule_id": rid, "field": field, "message": f"Valor '{val}' no está en el conjunto permitido {allowed}", "status": "error", "value": val, "expected": allowed, "rule_source": "shared" if rule_shared else "spec"})
            else:
                passes.append({"rule_id": rid, "field": field, "message": params.get("message", "Valor permitido"), "status": "pass", "value": val, "expected": allowed, "rule_source": "shared" if rule_shared else "spec"})
        # elif rtype == "cond":
            # Regla condicional: sólo se ejecutará si en las reglas existe una entrada con
            # "type": "cond" (actualmente las specs proporcionadas no generan reglas cond).
            # Se mantiene el soporte para compatibilidad futura.
            # Estructura esperada en params: {if_field, if_value, then_field, then_type, then_params}
            # if_field = params.get("if_field")
            # if_value = params.get("if_value")
            # then_field = params.get("then_field")
            # then_type = params.get("then_type")
            # then_params = params.get("then_params", {})
            # if if_field is not None and record.get(if_field) == if_value:
            #     sub_rule = {"id": f"{rid}.then", "type": then_type, "field": then_field, "params": then_params}
            #     sub_res = validate_record(record, [sub_rule], raw_line=raw_line, fields=fields)
            #     # sub_res puede ser dict con errors y passes
            #     if isinstance(sub_res, dict):
            #         errors.extend(sub_res.get("errors", []))
            #         passes.extend(sub_res.get("passes", []))
            #     else:
            #         # compatibilidad: si sub_res es lista se extiende a errors
            #         errors.extend(sub_res)
        # 'info', 'formatting', 'padding' son manejadas abajo en chequeos de campos

    # Chequeos basados en campos: required + formatting/padding + expected
    if fields is not None:
        # comprobar por cada campo
        for f in fields:
            name = f.get("name")
            required = f.get("required", False)
            ftype = f.get("type")
            length = f.get("length")
            value = record.get(name, "")
            raw_value = value or ""

            # si la spec define "expected", obtenerlo (puede ser espacios)
            expected = f.get("expected")

            # if required:
            #     # considerar válido si tiene contenido distinto de sólo espacios
            #     # o si coincide exactamente con el valor 'expected' declarado (p.ej. 20 espacios)
            #     if raw_value.strip() == "" and not (expected is not None and raw_value == expected):
            #         errors.append({"rule_id": f"field.{name}.required", "field": name, "message": "Campo requerido vacío", "severity": "error"})
            if expected is not None:
                # comparación exacta (sin strip), tal cual viene del slice posicional
                if raw_value != expected:
                    errors.append({
                        "rule_id": f.get("id") if f.get("id") is not None else f"field.{name}.expected",
                        "field": name,
                        "message": f"Valor esperado '{expected}', encontrado '{raw_value}'",
                        "status": "error",
                        "value": raw_value,
                        "expected": expected,
                        "rule_source": "field",
                    })
                else:
                    passes.append({
                        "rule_id": f.get("id") if f.get("id") is not None else f"field.{name}.expected",
                        "field": name,
                        "message": f"Valor coincide con expected",
                        "status": "pass",
                        "value": raw_value,
                        "expected": expected,
                        "rule_source": "field",
                    })
            else:
                # formatting: alfanum debe estar justificado a la izquierda (no comenzar con espacio)
                # numeric debe estar justificado a la derecha (no terminar con espacio)
                if ftype == "alphanumeric":
                    # Si el campo contiene sólo espacios (padding) y no hay 'expected',
                    # no ejecutar comprobaciones de alineación para alfanuméricos.
                    if raw_value.strip() == "":
                        # campo vacío real (sólo espacios) -> saltar validaciones de formato para alfanum
                        continue
                    # si viene con espacios iniciales, marcar
                    if len(raw_value) > 0 and raw_value[0] == " ":
                        errors.append({"rule_id": f.get("id") if f.get("id") is not None else f"field.{name}.format", "field": name, "message": "Campo alfanumérico con espacios iniciales; debe ir justificado a la izquierda", "status": "warning", "value": raw_value, "rule_source": "field"})
                elif ftype == "numeric":
                    # Para numéricos no saltamos validaciones si vienen sólo espacios; evaluar formato
                    if len(raw_value) > 0 and raw_value.endswith(" "):
                        errors.append({"rule_id": f.get("id") if f.get("id") is not None else f"field.{name}.format", "field": name, "message": "Campo numérico con espacios finales; debe ir justificado a la derecha", "status": "warning", "value": raw_value, "rule_source": "field"})

    return {"errors": errors, "passes": passes}
