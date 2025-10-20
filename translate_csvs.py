import re
import pandas as pd
from pathlib import Path
from mapping import resolve_classes_names_path

code_re = re.compile(r"\b([A-Za-z]\d{2})\b")  # p.ej. D00, D10, D44

def _idx_to_name(x, names):
    try:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            i = int(x)
            if 0 <= i < len(names):
                return names[i]
    except Exception:
        pass
    return x

def _map_code_string(s: str, code_to_desc: dict) -> str:
    def _sub(m):
        code = m.group(1)
        return code_to_desc.get(code, code)
    return code_re.sub(_sub, s)

def _to_readable(x, names, code_to_desc):
    x = _idx_to_name(x, names)
    if isinstance(x, (list, tuple)):
        return [_to_readable(e, names, code_to_desc) for e in x]
    if isinstance(x, str):
        return _map_code_string(x, code_to_desc)
    try:
        return _map_code_string(str(x), code_to_desc)
    except Exception:
        return x

def translate_and_save(results: dict, artifacts_dir: Path, code_to_desc: dict, output_dir: Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Guardando CSVs en: {output_dir}")
    # 1) Cargar names si existen
    names = []
    _classes = resolve_classes_names_path(artifacts_dir)
    if _classes and _classes.exists():
        with open(_classes, "r", encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip()]
        for n in names:
            code_to_desc.setdefault(n, n)

    # ---- A) data_resulting
    if "data_resulting" in results:
        df = pd.DataFrame(results["data_resulting"])
        if "classes" in df.columns:
            df["classes"] = df["classes"].apply(lambda v: _to_readable(v, names, code_to_desc))
        if "class_id" in df.columns:
            df["class_id_readable"] = df["class_id"].apply(
                lambda v: code_to_desc.get(str(_idx_to_name(v, names)), str(_idx_to_name(v, names)))
            )
        df.to_csv(output_dir / "data_resulting.csv", index=False)
        df.to_csv(output_dir / "data_resulting_legible.csv", index=False)
        print("data_resulting.csv traducido")

    # ---- B) data_resulting_fails
    if "data_resulting_fails" in results:
        df = pd.DataFrame(results["data_resulting_fails"])
        if "classes" in df.columns:
            df["classes"] = df["classes"].apply(lambda v: _to_readable(v, names, code_to_desc))
        if "class_id" in df.columns:
            df["class_id_readable"] = df["class_id"].apply(
                lambda v: code_to_desc.get(str(_idx_to_name(v, names)), str(_idx_to_name(v, names)))
            )
        df.to_csv(output_dir / "data_resulting_fails.csv", index=False)
        df.to_csv(output_dir / "data_resulting_fails_legible.csv", index=False)
        print("data_resulting_fails.csv traducido")

    # ---- C) table_summary_sections: códigos como nombres de columnas
    if "table_summary_sections" in results:
        df = pd.DataFrame(results["table_summary_sections"])
        new_cols = {}
        for col in df.columns:
            m = code_re.fullmatch(str(col))
            if m:
                code = m.group(1)
                new_cols[col] = code_to_desc.get(code, code)
        if new_cols:
            df_legible = df.rename(columns=new_cols)
        else:
            df_legible = df.copy()
        pd.DataFrame(results["table_summary_sections"]).to_csv(output_dir / "table_summary_sections.csv", index=False)
        df_legible.to_csv(output_dir / "table_summary_sections_legible.csv", index=False)
        print("table_summary_sections_legible.csv generado")
