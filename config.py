from pathlib import Path

# ---- CONFIG ----
INPUT_VIDEO = "Carretera_2.mp4"            # Cambia si tu video tiene otro nombre
ARTIFACTS_DIR = Path("./artifacts")
CONFIG_JSON = "./models_config.json"
# -----------------

# Diccionario de códigos -> descripciones (puedes ajustarlo según tu taxonomía)
CODE_TO_DESC_DEFAULT = {
    "D00": "Grieta Vertical",
    "D10": "Grieta e Intervalo Lineal Transversal",
    "D20": "Piel de cocodrilo",
    "D40": "Protuberancia, baches",
    "D43": "Desenfoque de paso peatonal",
    "D44": "Desenfoque de linea blanca",
}

# Extensiones permitidas para GPS
GPS_FILETYPES = [
    ("Archivos GPS", "*.csv *.gpx *.json"),
    ("CSV", "*.csv"),
    ("GPX", "*.gpx"),
    ("JSON", "*.json"),
]
