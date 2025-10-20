"""
main.py
------------------
Descripción general:
Este módulo implementa la LÓGICA PRINCIPAL del programa:
- Validaciones iniciales del entorno y del video.
- Selección opcional de fuente GPS (o stub si no hay archivo).
- Carga del modelo ML y parches auxiliares.
- Ejecución del workflow con una UI de progreso (ProgressUI del módulo ui del proyecto).
- Manejo del cierre de ventanas.
- Traducción de CSVs resultantes al finalizar.

Este archivo NO contiene la interfaz del menú (eso está en main_ui.py).
Se comunica con ProgressUI y otros módulos utilitarios.

"""

from __future__ import annotations

from pathlib import Path
from tkinter import Tk, filedialog, messagebox
import threading
import sys

# Dependencias internas del proyecto
from config import ARTIFACTS_DIR, CONFIG_JSON, CODE_TO_DESC_DEFAULT, GPS_FILETYPES
from checks import check_environment, read_video_duration
from no_gps import make_gps_stub
from loader import load_ml_processor
from patches import (
    patch_gps_sources, patch_workflows_gps, wrap_safe_predict,
    patch_overlay_utils, install_tqdm_bridge
)
from mapping import build_code_to_desc
from run_workflow import run_workflow
from translate_csvs import translate_and_save
from ui import ProgressUI
from main_ui import MainUI

"""
   Ejecuta el pipeline completo con una UI de progreso (ventana de barras y acciones finales).

   Entradas:
     - input_video: Path al video .mp4 a procesar.
     - output_dir:  Path a la carpeta donde se guardan los resultados.
     - on_back:     Callable sin argumentos; se invoca para "volver al menú" (re-mostrar la ventana del launcher).

   Salidas:
     - No retorna valor útil. Maneja excepciones mostrando/propagando errores según el flujo.
       Al finalizar exitoso: traduce los CSVs con translate_and_save.

   Resumen interno por bloques:
     1) Validación de entorno + lectura de metadatos del video.
     2) Selección opcional de entrada GPS o creación de stub.
     3) Carga de modelo ML, parches y mapeos de códigos a descripciones.
     4) Preparación de carpeta de salida.
     5) Lanzamiento de ProgressUI y del hilo trabajador (worker) que corre run_workflow.
     6) Manejo del cierre por “X”: confirmar si se cancela en medio del proceso o volver al menú si ya terminó.
     7) Al terminar, traducir CSVs (si aplica).
   """
def run_with_ui(input_video: Path, output_dir: Path, on_back):

    # ---------- [Validaciones y metadatos de video] ----------
    # - video_duration, fps, nframes: metadatos básicos del video de entrada.
    check_environment(str(input_video), ARTIFACTS_DIR, CONFIG_JSON)
    video_duration, fps, nframes = read_video_duration(str(input_video))

    # ---------- [Selección GPS (opc.)] ----------
    # - gps_source_type: str | None, tipo lógico de fuente (ej. 'loc'); usado por loaders.
    # - gps_input: str | None, ruta al archivo GPS seleccionado o None si se corre sin GPS.
    gps_source_type, gps_input = maybe_select_gps()

    # ---------- [Modelo ML y parches] ----------
    # Cargar el procesador ML y aplicar parches de seguridad/superposición.
    ml_processor = load_ml_processor(str(ARTIFACTS_DIR), CONFIG_JSON)
    wrap_safe_predict(ml_processor)

    # Mapeo de códigos a descripciones (para overlays y traducciones)
    code_to_desc, _ = build_code_to_desc(CODE_TO_DESC_DEFAULT, ARTIFACTS_DIR)
    patch_overlay_utils(code_to_desc)

    # Si no hay GPS real, parchear un stub consistente con la duración del video
    if gps_input is None:
        gps_stub = make_gps_stub(video_duration)
        patch_gps_sources(gps_stub)
        patch_workflows_gps(gps_stub)

    # ---------- [Preparar carpeta de salida] ----------
    output_dir.mkdir(parents=True, exist_ok=True)
    video_out = str(Path(output_dir) / "salida_detectada.mp4")

    # ---------- [Lanzar UI de progreso + hilo worker] ----------
    ui = ProgressUI(title="Procesando video…")

    # Estructuras para comunicar resultado/errores entre hilos
    res: dict[str, object] = {"val": None, "err": None}
    done = threading.Event()  # se marca al finalizar el worker

    """
        Hilo trabajador que ejecuta run_workflow.
        Entradas:  usa cierres sobre input_video/output_dir/etc.
        Salidas:   setea res["val"] o res["err"], y encola acciones finales en la UI.
    """
    def worker():
        try:
            # Puente entre tqdm y ProgressUI para reportar progreso a ~8 Hz
            install_tqdm_bridge(
                lambda d, n, t, r, e: ui.enqueue(ui.update_task, d or "progress", n, t, r, e),
                max_hz=8
            )

            # Ejecuta el workflow principal con tus parámetros
            res["val"] = run_workflow(
                str(input_video),
                ml_processor,
                gps_source_type=gps_source_type or "loc",
                gps_input=gps_input,
                batch_size=8,
                video_output_file=video_out,
                min_fotogram_distance=1
            )

        except Exception as e:
            res["err"] = e
        finally:

            # [Señal: el worker terminó]
            done.set()
            # [Log y botones finales en la UI]
            ui.enqueue(ui.write_log, "✔ Proceso finalizado.")
            ui.enqueue(ui.show_actions, str(output_dir), on_back)

    # Lanzar worker en modo daemon (permite salir del proceso al cerrar)
    th = threading.Thread(target=worker, daemon=True)
    th.start()

    # ---------- [Manejo de cierre] ----------
    # Variables:
    # - ui._closing: flag para prevenir cierres múltiples.
    ui._closing = False

    """
        Callback de cierre de la ventana de progreso.
        Entradas:  evento de “WM_DELETE_WINDOW”.
        Salidas:   según el estado, o cancela (confirmando) o destruye la UI y vuelve al menú.
    """
    def _on_close():
        # [Evitar interferencia por clics repetidos]
        if getattr(ui, "_closing", False):
            return

        # [Si el worker NO ha terminado, confirmar cierre/aborto]
        if not done.is_set():
            ans = messagebox.askyesno(
                "Cerrar",
                "Aún se está procesando.\n¿Desea cancelar y salir?",
                parent=ui
            )
            if not ans:
                return  # el usuario decide continuar procesando

            # Confirmado: cerrar todo de manera segura
            ui._closing = True
            try:
                ui.stop()
            except:
                pass
            try:
                ui.quit()
            except:
                pass
            try:
                ui.destroy()
            except:
                pass

            # Al ser daemon=True, el hilo muere con el proceso
            sys.exit(0)
        else:
            # [Si ya terminó, cerrar la ventana de progreso y volver al menú]
            ui._closing = True
            try:
                ui.stop()
            except:
                pass
            try:
                ui.destroy()
            except:
                pass
            on_back()

    # Vincular protocolo de cierre de la ventana
    ui.protocol("WM_DELETE_WINDOW", _on_close)

    # Iniciar loop de la ventana de progreso (bloqueante)
    ui.mainloop()

    # Si el worker lanzó error, propagarlo tras cerrar el loop
    if res["err"]:
        raise res["err"]  # dejar que lo maneje el caller si quiere

    # ---------- [Post-procesado: traducir CSVs] ----------
    # Si todo terminó OK, traducir y guardar CSVs en la carpeta de salida
    if done.is_set():
        translate_and_save(res["val"], ARTIFACTS_DIR, code_to_desc, output_dir)

    """
    Traduce CSVs a partir de los resultados y guarda en output_dir.

    Entradas:
      - results:   objeto devuelto por run_workflow (estructura propia de tu proyecto).
      - output_dir: Path de la carpeta destino.
      - code_to_desc: dict de código -> descripción humana.

    Salidas:
      - None (efecto: archivos CSV traducidos escritos en disco).
    """
def translate_csvs_after(results, output_dir: Path, code_to_desc: dict):

    # [Delegar al helper de tu proyecto]
    translate_and_save(results, ARTIFACTS_DIR, code_to_desc, output_dir)
    print("Listo. CSVs traducidos y guardados en:", output_dir)


"""
    Diálogo opcional para seleccionar archivo GPS (CSV/GPX/JSON).
    Entradas:  ninguna directa; abre cuadros de diálogo modales.
    Salidas:   (gps_source_type, gps_input) o (None, None) si se corre sin GPS.

    Notas:
    - Por compatibilidad, se devuelve 'loc' como tipo por defecto y el loader detecta por extensión.
    - Si el usuario cancela en cualquiera de los pasos, se asume ejecución sin GPS.
"""
def maybe_select_gps() -> tuple[str | None, str | None]:

    # [Ocultar ventana raíz temporal para no mostrar un Tk vacío]
    Tk().withdraw()

    # [Preguntar si se desea usar GPS]
    use_gps = messagebox.askyesno(
        "¿Usar GPS?",
        "¿Desea seleccionar un archivo de GPS (CSV/GPX/JSON)?\n"
        "Si elige 'No', se ejecutará sin GPS."
    )
    if not use_gps:
        return None, None

    # [Seleccionar archivo GPS]
    gps_path = filedialog.askopenfilename(
        title="Seleccionar archivo de GPS",
        filetypes=GPS_FILETYPES,
    )
    if not gps_path:
        return None, None

    # [Devolver tipo por defecto y la ruta elegida]
    gps_source_type = "loc"
    return gps_source_type, gps_path

"""
    Punto de entrada de la aplicación.
    Entradas:  ninguna.
    Salidas:   ejecuta el loop principal de Tkinter.
    """
def main():

    # [Crear y ejecutar ventana principal]
    app = MainUI()
    app.mainloop()


if __name__ == "__main__":
    main()