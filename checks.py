import os, glob
from pathlib import Path

def must(cond, msg):
    if not cond:
        raise SystemExit(msg)

def check_environment(input_video: str, artifacts_dir: Path, config_json: str):
    must(os.path.exists(input_video), f"No se encontró el video: {input_video}")
    must(artifacts_dir.exists(), f"No existe la carpeta de modelos: {artifacts_dir}")

    classes_found = any(
        p.endswith("classes.names")
        for p in glob.glob(str(artifacts_dir / "**" / "*"), recursive=True)
    )
    must(classes_found, "No se encontró 'classes.names' dentro de ./artifacts (verifica la descompresión del modelo)." )

    must(os.path.exists(config_json), f"No existe {config_json}. Crea uno con:\n"
                                      "{\n"
                                      '  "signal_model": {"enabled": false},\n'
                                      '  "paviment_model": {"yolo_threshold": 0.25, "yolo_iou": 0.45, "yolo_max_detections": 100}\n'
                                      "}\n" )

def read_video_duration(input_video: str) -> tuple[float, float, float]:
    try:
        import cv2
    except ImportError:
        raise SystemExit("Falta OpenCV. Instala con: pip install opencv-python")
    cap = cv2.VideoCapture(input_video)
    must(cap.isOpened(), f"No se pudo abrir el video con OpenCV: {input_video}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
    nframes = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
    cap.release()
    video_duration = (nframes / fps) if (fps > 0 and nframes > 0) else 0.0
    must(video_duration > 0.0, f"Duración del video es 0.0s (fps={fps}, frames={nframes}). "
                               f"Revisa el archivo o re-encódalo (p. ej., con HandBrake).")
    return float(video_duration), float(fps), float(nframes)
