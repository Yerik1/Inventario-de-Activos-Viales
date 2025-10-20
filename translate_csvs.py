"""
translate_csvs.py
-----------------
Descripción general del módulo (.py):
Utilidades para **hacer legibles** los resultados del pipeline y **guardarlos como CSV**.
Convierte códigos de clase (p. ej., D00, D10, D44) o índices numéricos a nombres
descriptivos usando un diccionario `code_to_desc` y/o el archivo `classes.names`
en tu carpeta de artefactos. Luego persiste varias tablas en la carpeta de salida.

Estructura:
- _idx_to_name(): traduce un índice numérico al nombre de clase, si existe en `names`.
- _map_code_string(): reemplaza códigos tipo "D00" por su descripción en un string.
- _to_readable(): convierte valores (escalares/listas/strings) a su forma legible.
- translate_and_save(): orquesta la carga de names, la traducción y el guardado de CSV.
"""
import re
import pandas as pd
from pathlib import Path
from mapping import resolve_classes_names_path

# Expresión regular para capturar códigos como D00, D10, D44, etc.
code_re = re.compile(r"\b([A-Za-z]\d{2})\b")  # p.ej. D00, D10, D44

"""
    Descripción:
        Si `x` es un índice (int/float no bool) dentro del rango de `names`,
        retorna `names[int(x)]`; de lo contrario retorna `x` sin cambios.

    Entradas:
        - x (int|float|any): posible índice de clase u otro valor.
        - names (list[str]): lista de nombres de clase (en orden) leída de `classes.names`.

    Salidas:
        - (str|any): nombre de clase si aplica; si no, el valor original.

    Variables/Detalles:
        - i (int): conversión segura a entero para indexar `names`.
    """
def _idx_to_name(x, names):
    try:
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            i = int(x)
            if 0 <= i < len(names):
                return names[i]
    except Exception:
        pass
    return x

"""
    Descripción:
        Reemplaza dentro del string todos los códigos tipo "D00"/"D10"/... por su
        descripción más legible usando `code_to_desc`.

    Entradas:
        - s (str): texto de entrada (p. ej., "D00\\n0.89").
        - code_to_desc (dict[str,str]): mapa código -> descripción legible.

    Salidas:
        - (str): string con los códigos reemplazados cuando aplique.
    """
def _map_code_string(s: str, code_to_desc: dict) -> str:
    def _sub(m):
        code = m.group(1)
        return code_to_desc.get(code, code)
    return code_re.sub(_sub, s)

"""
    Descripción :
        Convierte un dato arbitrario a una representación legible:
        - Si es índice numérico válido → nombre de clase.
        - Si es lista/tupla → procesa recursivamente cada elemento.
        - Si es string → sustituye códigos ("D00") por descripciones.
        - Si es otro tipo → intenta convertir a string y mapear códigos.

    Entradas:
        - x (any): valor a convertir (índice, string, lista, etc.).
        - names (list[str]): nombres de clase disponibles (puede ser vacío).
        - code_to_desc (dict[str,str]): códigos → descripciones legibles.

    Salidas:
        - (any): valor transformado (mismo tipo si lista/tupla; string si era string;
                 caso general, string mapeado o valor original si no aplica).
    """
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

"""
    Descripción breve:
        Traduce las tablas clave del `results` a una forma legible y las guarda en CSV:
        - data_resulting[(_legible)]
        - data_resulting_fails[(_legible)]
        - table_summary_sections[(_legible)] (renombrando columnas que sean códigos)

    Entradas:
        - results (dict): objeto/estructura retornada por el workflow con varias tablas.
        - artifacts_dir (Path): carpeta de artefactos donde se busca `classes.names`.
        - code_to_desc (dict[str,str]): mapa base de códigos → descripciones (se ampliará).
        - output_dir (Path): carpeta donde guardar los CSV (se crea si no existe).

    Salidas:
        - None (efecto: archivos .csv escritos en `output_dir` y prints informativos).

    Variables declaradas:
        - names (list[str]): nombres leídos desde `classes.names` (si existe).
        - _classes (Path|None): ruta detectada para el archivo `classes.names`.
        - df (pd.DataFrame): variable temporal para las distintas tablas.
        - new_cols (dict): mapeo de columnas para renombrar códigos en el resumen.
    """
def translate_and_save(results: dict, artifacts_dir: Path, code_to_desc: dict, output_dir: Path):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"Guardando CSVs en: {output_dir}")

    # ---------- [Cargar names si existen y ampliar diccionario] ----------
    names = []
    _classes = resolve_classes_names_path(artifacts_dir)
    if _classes and _classes.exists():
        with open(_classes, "r", encoding="utf-8") as f:
            names = [l.strip() for l in f if l.strip()]
        for n in names:
            code_to_desc.setdefault(n, n)

    # ---------- [data_resulting] ----------
    if "data_resulting" in results:
        df = pd.DataFrame(results["data_resulting"])

        # Mapear columna "classes" si está presente
        if "classes" in df.columns:
            df["classes"] = df["classes"].apply(lambda v: _to_readable(v, names, code_to_desc))

        # Agregar columna legible para "class_id" si existe
        if "class_id" in df.columns:
            df["class_id_readable"] = df["class_id"].apply(
                lambda v: code_to_desc.get(str(_idx_to_name(v, names)), str(_idx_to_name(v, names)))
            )

        # Guardar CSVs (crudo y legible)
        df.to_csv(output_dir / "data_resulting.csv", index=False)
        df.to_csv(output_dir / "data_resulting_legible.csv", index=False)
        print("data_resulting.csv traducido")

    # ---------- [data_resulting_fails] ----------
    if "data_resulting_fails" in results:
        df = pd.DataFrame(results["data_resulting_fails"])

        # Mapear columna "classes" si está presente
        if "classes" in df.columns:
            df["classes"] = df["classes"].apply(lambda v: _to_readable(v, names, code_to_desc))

        # Agregar columna legible para "class_id" si existe
        if "class_id" in df.columns:
            df["class_id_readable"] = df["class_id"].apply(
                lambda v: code_to_desc.get(str(_idx_to_name(v, names)), str(_idx_to_name(v, names)))
            )

        # Guardar CSVs (crudo y legible)
        df.to_csv(output_dir / "data_resulting_fails.csv", index=False)
        df.to_csv(output_dir / "data_resulting_fails_legible.csv", index=False)
        print("data_resulting_fails.csv traducido")

    # ---------- [table_summary_sections: renombrar columnas-código] ----------
    if "table_summary_sections" in results:
        df = pd.DataFrame(results["table_summary_sections"])

        # Construir mapeo solo para columnas que sean exactamente códigos (p. ej., "D00")
        new_cols = {}
        for col in df.columns:
            m = code_re.fullmatch(str(col))
            if m:
                code = m.group(1)
                new_cols[col] = code_to_desc.get(code, code)

        # Renombrar si hay cambios
        if new_cols:
            df_legible = df.rename(columns=new_cols)
        else:
            df_legible = df.copy()

        # Guardar versión cruda y legible
        pd.DataFrame(results["table_summary_sections"]).to_csv(output_dir / "table_summary_sections.csv", index=False)
        df_legible.to_csv(output_dir / "table_summary_sections_legible.csv", index=False)
        print("table_summary_sections_legible.csv generado")
