"""
config.py
---------
Descripción general:
Este módulo centraliza la **configuración** de la aplicación: rutas por defecto,
carpetas de artefactos/modelos, ruta al archivo de configuración del modelo,
diccionario de códigos → descripciones legibles y los tipos de archivo permitidos
para la fuente de GPS. No contiene lógica de negocio ni interfaz.

Cómo se usa:
- Otros módulos (p. ej., `pipeline_logic.py`, `checks.py`, `mapping.py`, `ui.py`)
  importan estas constantes para mantener un único punto de verdad.
- Puedes ajustar nombres/rutas sin tocar el resto del código.
"""
from pathlib import Path

# ---- CONFIG ----
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
