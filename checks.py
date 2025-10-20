"""
checks.py
---------
Descripción general :
Este módulo concentra utilidades de **verificación del entorno** y **lectura de metadatos del video**.
Se usa típicamente al inicio del pipeline para asegurar que:
- El video de entrada existe y es legible.
- La carpeta de artefactos/modelos existe y contiene `classes.names`.
- El archivo de configuración JSON existe (o se indica cómo crearlo).
- Se puede abrir el video con OpenCV y obtener FPS, #frames y duración > 0.

Estructura:
- must(cond, msg): helper para validar condiciones y terminar el proceso con un mensaje claro.
- check_environment(input_video, artifacts_dir, config_json): valida rutas y contenidos mínimos.
- read_video_duration(input_video): abre el video con OpenCV y retorna (duración_s, fps, nframes).

"""
import os, glob
from pathlib import Path

"""
   Descripción:
       Asegura una condición booleana. Si es falsa, aborta el programa con el mensaje dado.

   Entradas:
       - cond (bool): condición a verificar.
       - msg  (str):  mensaje de error a mostrar si la condición falla.

   Salidas:
       - None (efecto: puede lanzar SystemExit si cond es False).
   """
def must(cond, msg):
    # [Validación y salida controlada]
    if not cond:
        raise SystemExit(msg)

"""
    Descripción:
        Verifica que el **video de entrada**, la **carpeta de artefactos** y el **config JSON**
        cumplan requisitos mínimos antes de procesar.

    Entradas:
        - input_video (str): ruta al archivo de video de entrada (p. ej., .mp4).
        - artifacts_dir (Path): carpeta raíz donde están los modelos/artefactos.
        - config_json (str): ruta al archivo JSON de configuración del pipeline.

    Salidas:
        - None (efecto: valida o aborta con mensajes explicativos).

    Variables declaradas:
        - classes_found (bool): indica si se localizó algún archivo `classes.names`
          dentro de artifacts_dir de manera recursiva.
    """
def check_environment(input_video: str, artifacts_dir: Path, config_json: str):
    # ---------- [Validar rutas base] ----------
    must(os.path.exists(input_video), f"No se encontró el video: {input_video}")
    must(artifacts_dir.exists(), f"No existe la carpeta de modelos: {artifacts_dir}")

    # ---------- [Buscar classes.names de forma recursiva] ----------
    # Nota: usamos glob recursivo para permitir distintas estructuras de carpetas.
    classes_found = any(
        p.endswith("classes.names")
        for p in glob.glob(str(artifacts_dir / "**" / "*"), recursive=True)
    )
    must(classes_found, "No se encontró 'classes.names' dentro de ./artifacts (verifica la descompresión del modelo)." )

    # ---------- [Verificar config.json (o sugerir contenido base)] ----------
    must(os.path.exists(config_json), f"No existe {config_json}. Crea uno con:\n"
                                      "{\n"
                                      '  "signal_model": {"enabled": false},\n'
                                      '  "paviment_model": {"yolo_threshold": 0.25, "yolo_iou": 0.45, "yolo_max_detections": 100}\n'
                                      "}\n" )

"""
    Descripción:
        Abre el video con OpenCV y retorna metadatos básicos:
        **(duración_en_segundos, fps, número_de_frames)**.
        Garantiza que la duración sea > 0; de lo contrario, sugiere re-encode.

    Entradas:
        - input_video (str): ruta al video fuente.

    Salidas:
        - (tuple[float, float, float]): (video_duration, fps, nframes).

    Variables declaradas:
        - cap (cv2.VideoCapture): manejador de captura de OpenCV.
        - fps (float): cuadros por segundo reportados por el contenedor/códec.
        - nframes (float): número total de frames (puede ser estimado por algunos contenedores).
        - video_duration (float): duración calculada en segundos.
    """
def read_video_duration(input_video: str) -> tuple[float, float, float]:
    # ---------- [Importar OpenCV] ----------
    try:
        import cv2
    except ImportError:
        # Sugerimos paquete binario común; si requieren headless pueden usar opencv-python-headless.
        raise SystemExit("Falta OpenCV. Instala con: pip install opencv-python")

    # ---------- [Abrir video y leer metadatos] ----------
    cap = cv2.VideoCapture(input_video)
    must(cap.isOpened(), f"No se pudo abrir el video con OpenCV: {input_video}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0

    # Liberar el recurso de inmediato para no bloquear archivos.
    cap.release()

    # ---------- [Calcular y validar duración] ----------
    video_duration = (nframes / fps) if (fps > 0 and nframes > 0) else 0.0
    must(video_duration > 0.0, f"Duración del video es 0.0s (fps={fps}, frames={nframes}). "
                               f"Revisa el archivo o re-encódalo (p. ej., con HandBrake).")

    # ---------- [Retornar metadatos] ----------
    return float(video_duration), float(fps), float(nframes)
