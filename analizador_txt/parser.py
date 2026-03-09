from typing import Dict, Iterator


def read_lines(path: str, chunk_size: int = 1000) -> Iterator[str]:
    """Lee un archivo de texto en streaming, devolviendo líneas una a una.

    Mantener la lectura en streaming evita cargar todo el archivo en memoria.
    """
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            yield line.rstrip("\n")


def parse_line(line: str, spec: Dict) -> Dict:
    """Parsea una línea de longitud fija según una spec positional.

    La spec debe contener una lista `fields` con objetos {name, start, end} (1-based, inclusive).
    Retorna un dict con pares campo:valor.
    """
    result = {}
    for field in spec.get("fields", []):
        name = field.get("name")
        start = field.get("start", 1) - 1
        end = field.get("end")  # inclusive
        if end is None:
            value = line[start:]
        else:
            value = line[start:end]
        result[name] = value
    return result
