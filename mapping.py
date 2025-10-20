from pathlib import Path

def resolve_classes_names_path(artifacts_dir: Path) -> Path | None:
    explicit = artifacts_dir / "paviment_model" / "yolov8-road-damage-old-classes-240724-1800" / "classes.names"
    if explicit.exists():
        return explicit
    for c in [artifacts_dir / "paviment_model" / "classes.names", artifacts_dir / "classes.names"]:
        if c.exists():
            return c
    try:
        found = list(artifacts_dir.rglob("classes.names"))
        if found:
            return found[0]
    except Exception:
        pass
    return None

def build_code_to_desc(code_to_desc: dict, artifacts_dir: Path) -> dict:
    code_to_desc = dict(code_to_desc or {})
    names = []
    classes = resolve_classes_names_path(artifacts_dir)
    if classes and classes.exists():
        with open(classes, "r", encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip()]
        for n in names:
            code_to_desc.setdefault(n, n)
    return code_to_desc, names
