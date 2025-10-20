from pathlib import Path
from tkinter import Tk, ttk, filedialog, messagebox
import threading
import os
#os.environ["TQDM_DISABLE"] = "1"

from config import ARTIFACTS_DIR, CONFIG_JSON, CODE_TO_DESC_DEFAULT, GPS_FILETYPES
from checks import check_environment, read_video_duration
from no_gps import make_gps_stub
from loader import load_ml_processor
from patches import patch_gps_sources, patch_workflows_gps, wrap_safe_predict, patch_overlay_utils, install_tqdm_bridge
from mapping import build_code_to_desc
from run_workflow import run_workflow
from translate_csvs import translate_and_save
from ui import run_with_progress
from ui import ProgressUI

class LauncherUI(Tk):
    def __init__(self):
        super().__init__()
        self.title("Inventario de Activos Viales")
        self.geometry("520x240")
        self.resizable(False, False)

        self.video_path: Path | None = None
        self.output_dir: Path | None = None

        title = ttk.Label(self, text="Inventario de Activos Viales", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(18, 6))

        # fila de info
        self.lbl_video = ttk.Label(self, text="Video: (no seleccionado)")
        self.lbl_video.pack(fill="x", padx=16, pady=(6, 0))
        self.lbl_out = ttk.Label(self, text="Carpeta de salida: (no seleccionada)")
        self.lbl_out.pack(fill="x", padx=16, pady=(2, 10))

        # botones
        frm = ttk.Frame(self)
        frm.pack(pady=8)

        self.btn_video = ttk.Button(frm, text="Seleccionar video (.mp4)", command=self.select_video)
        self.btn_video.grid(row=0, column=0, padx=6, pady=6)

        self.btn_out = ttk.Button(frm, text="Seleccionar carpeta de salida", command=self.select_output_dir)
        self.btn_out.grid(row=0, column=1, padx=6, pady=6)

        self.btn_start = ttk.Button(self, text="Empezar", command=self.start_process, state="disabled")
        self.btn_start.pack(pady=(6, 8))

        # pie
        ttk.Label(self, text="Seleccione video y carpeta de salida, luego presione Empezar.").pack(pady=(0, 6))

    def select_video(self):
        p = filedialog.askopenfilename(
            title="Seleccionar video de entrada (.mp4)",
            filetypes=[("Archivos de video", "*.mp4")]
        )
        if p:
            self.video_path = Path(p)
            self.lbl_video.config(text=f"Video: {self.video_path.name}")
        self._update_start_state()

    def select_output_dir(self):
        d = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if d:
            self.output_dir = Path(d)
            self.lbl_out.config(text=f"Carpeta de salida: {self.output_dir}")
        self._update_start_state()

    def _update_start_state(self):
        ok = (self.video_path is not None) and (self.output_dir is not None)
        self.btn_start.config(state=("normal" if ok else "disabled"))

    def start_process(self):
        if not self.video_path or not self.output_dir:
            return
        self.withdraw()  # ocultamos el menú
        # NO lo re-mostramos aquí; lo hará el botón "Volver al menú"
        run_pipeline_with_ui(self.video_path, self.output_dir,
                             on_back=lambda: self.deiconify())

def run_pipeline_with_ui(input_video: Path, output_dir: Path, on_back):
    # Validaciones y preparación
    check_environment(str(input_video), ARTIFACTS_DIR, CONFIG_JSON)
    video_duration, fps, nframes = read_video_duration(str(input_video))
    gps_source_type, gps_input = maybe_select_gps()

    # Cargar modelo y parches
    ml_processor = load_ml_processor(str(ARTIFACTS_DIR), CONFIG_JSON)
    wrap_safe_predict(ml_processor)
    code_to_desc, _ = build_code_to_desc(CODE_TO_DESC_DEFAULT, ARTIFACTS_DIR)
    patch_overlay_utils(code_to_desc)

    # Si no hay GPS real, parchea NoGPS
    if gps_input is None:
        gps_stub = make_gps_stub(video_duration)
        patch_gps_sources(gps_stub)
        patch_workflows_gps(gps_stub)

    # Salida de video dentro de output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    video_out = str(Path(output_dir) / "salida_detectada.mp4")

    # Lanzar ProgressUI + worker
    ui = ProgressUI(title="Procesando video…")

    def ui_send(name, n, total, rate, eta):
        ui.enqueue(ui.update_task, name, n, total, rate, eta)

    import threading, sys
    res = {"val": None, "err": None}
    done = threading.Event()

    def worker():
        try:
            install_tqdm_bridge(lambda d, n, t, r, e: ui.enqueue(ui.update_task, d or "progress", n, t, r, e), max_hz=8)
            res["val"] = run_workflow(
                str(input_video),
                ml_processor,
                gps_source_type=gps_source_type or "loc",
                gps_input=gps_input,
                batch_size=8,
                video_output_file=str(Path(output_dir) / "salida_detectada.mp4"),
                min_fotogram_distance=1
            )
        except Exception as e:
            res["err"] = e
        finally:
            done.set()
            ui.enqueue(ui.write_log, "✔ Proceso finalizado.")
            # ¡Botones! (los dibuja el hilo de UI)
            ui.enqueue(ui.show_actions, str(output_dir), on_back)

    th = threading.Thread(target=worker, daemon=True)
    th.start()

    # 👇 Handler al cerrar con la “X”
    ui._closing = False  # evita cierres duplicados

    def _on_close():
        # Si ya estamos cerrando, ignora clics repetidos
        if getattr(ui, "_closing", False):
            return

        if not done.is_set():
            # >>> AÚN PROCESANDO: confirmar — el messagebox es modal al UI
            ans = messagebox.askyesno(
                "Cerrar",
                "Aún se está procesando.\n¿Desea cancelar y salir?",
                parent=ui
            )
            if not ans:
                # Usuario dijo NO → mantener la ventana abierta
                return

            # Confirmado: cerramos todo
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
            # hilo de trabajo es daemon=True, así que podemos terminar el proceso
            sys.exit(0)
        else:
            # >>> YA TERMINÓ: no matar la app; vuelve al menú
            ui._closing = True
            try:
                ui.stop()
            except:
                pass
            try:
                ui.destroy()
            except:
                pass
            on_back()  # re-muestra el launcher

    ui.protocol("WM_DELETE_WINDOW", _on_close)

    ui.mainloop()

    if res["err"]:
        raise res["err"]

    # Traducir CSVs dentro de la carpeta de salida
    if done.is_set():
        translate_and_save(res["val"], ARTIFACTS_DIR, code_to_desc, output_dir)

def translate_csvs_after(results, output_dir: Path, code_to_desc: dict):
    translate_and_save(results, ARTIFACTS_DIR, code_to_desc, output_dir)
    print("Listo. CSVs traducidos y guardados en:", output_dir)

def select_input_video():
    """Abre un cuadro de diálogo para elegir un archivo .mp4"""
    Tk().withdraw()  # Oculta la ventana principal de Tk
    file_path = filedialog.askopenfilename(
        title="Seleccionar video de entrada",
        filetypes=[("Archivos de video", "*.mp4")],
    )
    if not file_path:
        raise SystemExit("No se seleccionó ningún archivo de video.")
    return Path(file_path)

def maybe_select_gps() -> tuple[str | None, str | None]:
    """
    Devuelve (gps_source_type, gps_input) o (None, None) si corremos sin GPS.
    - gps_input: ruta al archivo CSV/GPX/JSON
    - gps_source_type: dejamos 'loc' por compatibilidad; muchos loaders detectan
      por extensión. Si tu workflow requiere un tipo específico, ajústalo aquí.
    """
    # Preguntar si desea usar GPS
    Tk().withdraw()
    use_gps = messagebox.askyesno(
        "¿Usar GPS?",
        "¿Desea seleccionar un archivo de GPS (CSV/GPX/JSON)?\n"
        "Si elige 'No', se ejecutará sin GPS."
    )
    if not use_gps:
        return None, None

    gps_path = filedialog.askopenfilename(
        title="Seleccionar archivo de GPS",
        filetypes=GPS_FILETYPES,
    )
    if not gps_path:
        # Si canceló aquí, seguimos sin GPS
        return None, None

    # Por defecto usamos 'loc' y dejamos que el loader detecte por extensión.
    gps_source_type = "loc"
    return gps_source_type, gps_path

def _progress_callback(desc, n, total, rate_text, eta_text):
    # Mapear nombres de tqdm a los rótulos que queremos en la UI
    name = str(desc or "").strip() or "progress"
    # reenviar a la UI: lo hace run_with_progress a través de un closure
    # Aquí no tenemos la UI todavía, así que haremos el bind en la llamada:
    pass



def main():
    app = LauncherUI()
    app.mainloop()

if __name__ == "__main__":
    main()
