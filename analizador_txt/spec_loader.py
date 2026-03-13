import json
import os
from typing import Dict, List, Optional


def read_json(path: str) -> Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(base_path: str, relative: str) -> str:
    if os.path.isabs(relative):
        return relative
    return os.path.normpath(os.path.join(os.path.dirname(base_path), relative))


def translate_shared_rules(shared: Dict, spec: Dict) -> List[Dict]:
    """Traduce reglas descriptivas de shared_rules.json a reglas ejecutables simples.

    Actualmente traduce:
    - type 'movement_detection' -> rule enum targeting field
    - type 'file' with check 'record.length' -> length rule
    Las demás reglas se dejan como info/formatting que serán aplicadas por checks de campo.
    """
    out: List[Dict] = []
    for r in shared.get("rules", []):
        rtype = r.get("type")
        if rtype == "movement_detection":
            out.append({
                "id": r.get("id"),
                "type": "enum",
                "field": r.get("field"),
                "params": {"allowed": r.get("allowed", [])},
                "message": r.get("message"),
                "shared": True,
            })
        elif rtype == "file":
            # buscar pattern record.length == N
            chk = r.get("check", "")
            if "record.length" in chk and "==" in chk:
                parts = chk.split("==")
                try:
                    expected = int(parts[1].strip())
                    out.append({"id": r.get("id"), "type": "length", "field": None, "params": {"length": expected}, "message": r.get("message"), "shared": True})
                except Exception:
                    continue
        else:
            # formatting/padding/info quedan implícitos; el validador hará checks por campo
            continue
    return out


def load_spec(path: str) -> Dict:
    """Carga y normaliza una spec (p.ej. m.json o l.json).

    Resultado: dict con claves principales: 'fields' (lista normalizada), 'rules' (lista traducida), 'record_length'
    """
    spec = read_json(path)

    # cargar base si aplica
    base = {"fields": []}
    if spec.get("base_spec"):
        base_path = resolve_path(path, spec["base_spec"])
        base = read_json(base_path)

    # empezar desde campos base
    fields_by_id: Dict[int, Dict] = {}
    for f in base.get("fields", []):
        fields_by_id[f.get("id")] = dict(f)

    # aplicar overrides: algunas specs usan 'field_overrides', otras usan 'fields' para declarar
    # los cambios respecto a la base. Unir ambos para mayor compatibilidad.
    for o in list(spec.get("field_overrides", [])) + list(spec.get("fields", [])):
        fields_by_id[o.get("id")] = {**fields_by_id.get(o.get("id"), {}), **o}

    # ordenar por start
    fields_list = sorted([v for v in fields_by_id.values()], key=lambda x: x.get("start", 0))

    # cargar y traducir shared_rules
    rules: List[Dict] = []
    if spec.get("shared_rules"):
        shared_path = resolve_path(path, spec["shared_rules"])
        shared = read_json(shared_path)
        rules.extend(translate_shared_rules(shared, spec))

    # añadir regla de longitud de registro si la spec la declara
    if spec.get("record_length"):
        rules.insert(0, {"id": "record_length", "type": "length", "field": None, "params": {"length": spec["record_length"]}, "message": "Longitud esperada del registro"})

    return {**spec, "fields": fields_list, "rules": rules}


def pick_movement_schema(movement_spec_path: str, raw_line: str) -> Optional[str]:
    """Dado el path de spec MO (m.json o l.json) y una línea, detecta movimiento usando movement_schemas.

    Retorna la clave del movement_schema (p.ej. 'M0', 'M1', 'L0', 'L1') o None si no se detecta.
    """
    spec = read_json(movement_spec_path)
    shared_rules = spec.get("shared_rules")
    # intentar usar movement_detection de shared_rules
    if shared_rules:
        shared = read_json(resolve_path(movement_spec_path, shared_rules))
        for r in shared.get("rules", []):
            if r.get("type") == "movement_detection":
                # start/end pueden venir como str en algunas specs; intentar convertir a int
                try:
                    start_idx = int(r.get("start", 1)) - 1
                except Exception:
                    start_idx = 0
                end_raw = r.get("end")
                try:
                    end_idx = int(end_raw) if end_raw is not None and end_raw != "" else None
                except Exception:
                    end_idx = None

                if end_idx is None:
                    val = raw_line[start_idx:]
                else:
                    # convertir end_idx a slice end (Python slice end is exclusive)
                    val = raw_line[start_idx:end_idx]
                val = val.strip()
                allowed = r.get("allowed", [])
                if val in allowed:
                    return val
    # fallback: mirar field overrides para clave_de_movimiento
    # fallback: mirar field_overrides o fields para clave_de_movimiento
    for f in list(spec.get("field_overrides", [])) + list(spec.get("fields", [])):
        if f.get("name") == "clave_de_movimiento":
            try:
                start_idx = int(f.get("start", 1)) - 1
            except Exception:
                start_idx = 0
            end_raw = f.get("end")
            try:
                end_idx = int(end_raw) if end_raw is not None and end_raw != "" else None
            except Exception:
                end_idx = None

            val = raw_line[start_idx:end_idx] if end_idx else raw_line[start_idx:]
            val = val.strip()
            # si entra en movement_schemas
            if val and val in spec.get("movement_schemas", {}):
                return val
    return None
