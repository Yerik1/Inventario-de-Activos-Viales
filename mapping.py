"""
mapping.py
-----------
Descripción general:
Proporciona funciones auxiliares para resolver la ubicación del archivo `classes.names`
dentro del árbol de artefactos y construir un diccionario de códigos de clase → descripción
humana. Es esencial para traducir etiquetas de detección a nombres comprensibles en
reportes, overlays y CSVs.

Estructura:
- resolve_classes_names_path(): busca el archivo `classes.names` en ubicaciones posibles.
- build_code_to_desc(): combina el diccionario por defecto con los nombres reales leídos.
"""
from pathlib import Path

"""
    Descripción:
        Busca el archivo `classes.names` dentro de la carpeta de artefactos, revisando rutas
        específicas conocidas y, si no lo encuentra, realiza una búsqueda recursiva.

    Entradas:
        - artifacts_dir (Path): carpeta raíz donde se guardan los modelos y sus clases.

    Salidas:
        - (Path | None): ruta al archivo encontrado o None si no existe.

    Variables declaradas:
        - explicit (Path): ruta más específica donde se espera encontrar el archivo.
        - c (Path): rutas alternativas dentro del directorio de artefactos.
        - found (list[Path]): resultado de la búsqueda recursiva.
    """
def resolve_classes_names_path(artifacts_dir: Path) -> Path | None:
    # [Ruta explícita esperada
    explicit = artifacts_dir / "paviment_model" / "yolov8-road-damage-old-classes-240724-1800" / "classes.names"
    if explicit.exists():
        return explicit

    # [Rutas alternativas]
    for c in [artifacts_dir / "paviment_model" / "classes.names", artifacts_dir / "classes.names"]:
        if c.exists():
            return c

    # [Búsqueda recursiva en caso de estructuras distintas]
    try:
        found = list(artifacts_dir.rglob("classes.names"))
        if found:
            return found[0]
    except Exception:
        pass

    # [Si no se encuentra nada, retornar None]
    return None

"""
    Descripción:
        Construye un diccionario actualizado de código → descripción. Si encuentra
        un archivo `classes.names`, agrega sus etiquetas al diccionario base.

    Entradas:
        - code_to_desc (dict): diccionario inicial (por ejemplo, CODE_TO_DESC_DEFAULT).
        - artifacts_dir (Path): carpeta raíz donde buscar el archivo de clases.

    Salidas:
        - (tuple[dict, list[str]]): diccionario actualizado y lista de nombres leídos.

    Variables declaradas:
        - names (list[str]): nombres de clases leídos desde `classes.names`.
        - classes (Path|None): ruta detectada del archivo `classes.names`.
    """
def build_code_to_desc(code_to_desc: dict, artifacts_dir: Path) -> dict:
    # [Copiar diccionario base para no modificar el original]
    code_to_desc = dict(code_to_desc or {})
    names = []

    # [Intentar resolver la ruta al archivo de clases]
    classes = resolve_classes_names_path(artifacts_dir)

    # [Si el archivo existe, leer líneas no vacías]
    if classes and classes.exists():
        with open(classes, "r", encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip()]

        # [Agregar cualquier clase nueva no presente en el diccionario]
        for n in names:
            code_to_desc.setdefault(n, n)

    # [Retornar resultados]
    return code_to_desc, names
