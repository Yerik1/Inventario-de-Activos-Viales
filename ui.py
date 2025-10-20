# ui.py
import threading
import queue
import tkinter as tk
from tkinter import ttk
import os, sys, subprocess

def _canonical(name: str) -> str:
    """Normaliza descripciones de tqdm a rótulos conocidos."""
    n = (name or "").strip().lower()
    if n.startswith("processing batches"):
        return "Processing batches"
    if n.startswith("processing frames"):
        return "Processing frames"
    return name.strip() or "progress"

class ProgressUI(tk.Tk):
    def __init__(self, title="Procesando…"):
        super().__init__()
        self.title(title)
        self.geometry("520x300")
        self.resizable(False, False)

        self._rows = {}
        self._after_id = None
        self._running = True

        self._q = queue.Queue()

        self._make_row("Processing batches")
        self._make_row("Processing frames")

        self.log = tk.Text(self, height=4, state="disabled")
        self.log.pack(fill="x", padx=12, pady=(6, 10))

        self._footer = ttk.Frame(self)
        self._footer.pack(fill="x", padx=12, pady=(0, 10))
        self._footer.pack_propagate(False)
        self._open_btn = None  # se crea al final

        # ciclo UI
        self._schedule_pump()

        # Cierre seguro (evita "invalid command name ..._pump")
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _make_row(self, name):
        name = _canonical(name)
        if name in self._rows:
            return
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=12, pady=(12 if not self._rows else 6, 0))
        lbl = ttk.Label(frm, text=name)
        lbl.pack(anchor="w")
        bar = ttk.Progressbar(frm, orient="horizontal", mode="determinate", maximum=100)
        bar.pack(fill="x", pady=4)
        pct = ttk.Label(frm, text="0%")
        pct.pack(anchor="e")
        self._rows[name] = {"label": lbl, "bar": bar, "pct": pct, "total": 0}

    def update_task(self, name, n, total, _rate_text=None, _eta_text=None):
        """Actualiza barra: dejamos SOLO el porcentaje."""
        name = _canonical(name)
        row = self._rows.get(name)
        if not row:
            self._make_row(name)
            row = self._rows[name]
        total = int(total) if total else 0
        row["total"] = total
        pct = int((int(n) / total) * 100) if total else 0
        row["bar"]["value"] = pct
        row["pct"]["text"] = f"{pct}%"

    def write_log(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def enqueue(self, fn, *args, **kwargs):
        try:
            self._q.put(("call", fn, args, kwargs), block=False)
        except Exception:
            pass

    def _pump(self):
        try:
            while True:
                kind, *rest = self._q.get_nowait()
                if kind == "call":
                    fn, args, kwargs = rest
                    try:
                        fn(*args, **kwargs)
                    except tk.TclError:
                        # UI ya cerrándose; ignora
                        pass
        except queue.Empty:
            pass
        except Exception:
            # cualquier otro fallo, no rompas el loop
            pass

        if self._running:
            self._schedule_pump()

    def _schedule_pump(self):
        # Guarda el id para poder cancelarlo al cerrar
        try:
            self._after_id = self.after(50, self._pump)
        except tk.TclError:
            # Si ya se destruyó, ignorar
            pass

    def stop(self):
        # Cancela el ciclo after antes de destruir
        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    def _on_close(self):
        self.stop()
        try:
            self.destroy()
        except tk.TclError:
            pass

    def show_actions(self, out_dir: str, on_back):
        """Muestra botones para abrir carpeta y volver al menú tras finalizar."""
        # Limpia el footer y crea dos botones
        for w in self._footer.winfo_children():
            w.destroy()

        def _open_folder(path):
            import os, sys, subprocess
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])
                else:
                    subprocess.Popen(["xdg-open", path])
            except Exception as e:
                self.write_log(f"No se pudo abrir la carpeta: {e}")

        # Contenedor con grid para que siempre se vean
        row = ttk.Frame(self._footer)
        row.grid(row=0, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)  # separador elástico

        btn_open = ttk.Button(row, text="Abrir carpeta de salida",
                                      command=lambda: _open_folder(out_dir))
        btn_back = ttk.Button(row, text="Volver al menú",
                                      command=lambda: (self.destroy(), on_back()))

        # distribuye: [btn_open][espacio elástico][btn_back]
        btn_open.grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")
        ttk.Label(row, text="").grid(row=0, column=1, sticky="ew")
        btn_back.grid(row=0, column=2, padx=(6, 0), pady=2, sticky="e")

        # Fuerza layout y trae al frente (por si quedó tapado)
        self._footer.update_idletasks()
        try:
            self.attributes("-topmost", True)
            self.after(600, lambda: self.attributes("-topmost", False))
        except Exception:
            pass





def run_with_progress(target, *, title="Procesando…"):
    """(No la estamos usando en tu main ahora, la dejo por si la prefieres)"""
    ui = ProgressUI(title=title)
    result_holder = {"value": None, "error": None}
    done = threading.Event()

    def _runner():
        try:
            result_holder["value"] = target()
        except Exception as e:
            result_holder["error"] = e
        finally:
            done.set()
            ui.enqueue(ui.write_log, "✔ Proceso finalizado.")

    th = threading.Thread(target=_runner, daemon=True)
    th.start()

    def _check_done():
        if done.is_set():
            ui.stop()
            ui.after(300, ui.destroy)
            return
        ui.after(150, _check_done)

    ui.after(150, _check_done)
    ui.mainloop()

    if result_holder["error"]:
        raise result_holder["error"]
    return result_holder["value"]
