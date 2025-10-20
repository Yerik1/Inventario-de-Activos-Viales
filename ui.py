"""
ui.py
------
Descripción general:
Este módulo implementa la INTERFAZ GRÁFICA de progreso con Tkinter para mostrar barras
de avance, logs en tiempo real y acciones finales (abrir carpeta / volver al menú).
No incluye la lógica del procesamiento; se limita a recibir eventos
(“update_task”, “write_log”, etc.) encolados desde hilos de trabajo y reflejarlos en la UI.

Estructura:
- Función _canonical: normaliza nombres de tareas de progreso a rótulos estándar.
- Clase ProgressUI (Tk): ventana con barras de progreso, log y footer con acciones.
  * Métodos principales:
      - _make_row: crea una fila de progreso (label + barra + porcentaje).
      - update_task: actualiza porcentaje de una tarea.
      - write_log: agrega líneas al panel de log.
      - enqueue: encola llamadas a métodos de UI desde otros hilos.
      - _pump / _schedule_pump: bucle seguro de despacho de eventos.
      - stop / _on_close: cierre seguro de la ventana.
      - show_actions: muestra botones “Abrir carpeta” y “Volver al menú”.
- Helper run_with_progress: envoltorio simple para ejecutar un target con esta UI.

"""

from __future__ import annotations

import threading
import queue
import tkinter as tk
from tkinter import ttk
import os, sys, subprocess

"""
    Descripción:
        Normaliza el texto que viene de tqdm (u otras fuentes) para mapearlo a rótulos
        conocidos de la UI (p. ej., “Processing batches”, “Processing frames”).

    Entradas:
        - name (str): texto arbitrario que describe la tarea de progreso.

    Salidas:
        - (str): rótulo normalizado (“Processing batches”, “Processing frames”, o el
                 texto original sin espacios extremos si no aplica).

    Notas de implementación:
        - Se pasa a minúscula y se comparan prefijos. Si no hay match, se retorna
          el texto “limpio” o “progress” como fallback cuando está vacío.
    """
def _canonical(name: str) -> str:

    # [Normalización de espacios y minúsculas]
    n = (name or "").strip().lower()

    # [Mapeo por prefijo a rótulos estables de UI]
    if n.startswith("processing batches"):
        return "Processing batches"
    if n.startswith("processing frames"):
        return "Processing frames"

    # [Retorno por defecto: texto sin espacios o “progress”]
    return name.strip() or "progress"


"""
    Descripción:
        Ventana principal de progreso. Muestra múltiples filas de barras, un área de log,
        y un pie de acciones al finalizar. Recibe eventos desde un hilo worker mediante
        una cola thread-safe.

    Entradas (constructor):
        - title (str, opcional): título de la ventana.

    Salidas:
        - Instancia de tk.Tk lista para ejecutar con .mainloop().

    Variables de instancia (declaradas en __init__):
        - _rows (dict): mapea nombre de tarea -> widgets y estado {"label","bar","pct","total"}.
        - _after_id (int|None): id del after() activo para cancelar el ciclo al cerrar.
        - _running (bool): flag de ciclo de bombeo de eventos.
        - _q (queue.Queue): cola de acciones (tuplas) encoladas desde otros hilos.
        - log (tk.Text): widget de texto para mensajes.
        - _footer (ttk.Frame): contenedor del pie de acciones.
        - _open_btn (ttk.Button|None): referencia opcional (no usada estrictamente).
    """
class ProgressUI(tk.Tk):

    def __init__(self, title="Procesando…"):
        # [Inicialización base de Tk]
        super().__init__()
        self.title(title)
        self.geometry("520x300")
        self.resizable(False, False)

        # [Estructuras de estado internas]
        self._rows = {}          # dict de filas de progreso
        self._after_id = None    # id del ciclo after() para cancelación
        self._running = True     # flag de ciclo activo
        self._q = queue.Queue()  # cola thread-safe para eventos de UI

        # [Fila(s) inicial(es) de progreso: crea rótulos por defecto]
        self._make_row("Processing batches")
        self._make_row("Processing frames")

        # [Área de log: solo lectura para el usuario]
        self.log = tk.Text(self, height=4, state="disabled")
        self.log.pack(fill="x", padx=12, pady=(6, 10))

        # [Pie de acciones (rellenado al final con show_actions)]
        self._footer = ttk.Frame(self)
        self._footer.pack(fill="x", padx=12, pady=(0, 10))
        self._footer.pack_propagate(False)
        self._open_btn = None  # (placeholder si lo deseas referenciar luego)

        # [Ciclo de bombeo de cola: arranca el loop que despacha acciones en UI]
        self._schedule_pump()

        # [Cierre seguro: evita callbacks huérfanos]
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    """
        Descripción:
            Crea (si hace falta) una fila de progreso con label, barra y porcentaje.

        Entradas:
            - name (str): nombre de la tarea (se normaliza con _canonical).

        Salidas:
            - None (efecto: widgets agregados al contenedor y estado interno).

        """
    def _make_row(self, name: str) -> None:

        # [ormaliza y evita duplicados]
        name = _canonical(name)
        if name in self._rows:
            return

        # [Construcción de la fila de UI]
        frm = ttk.Frame(self)
        frm.pack(fill="x", padx=12, pady=(12 if not self._rows else 6, 0))

        lbl = ttk.Label(frm, text=name)
        lbl.pack(anchor="w")

        bar = ttk.Progressbar(frm, orient="horizontal", mode="determinate", maximum=100)
        bar.pack(fill="x", pady=4)

        pct = ttk.Label(frm, text="0%")
        pct.pack(anchor="e")

        # [Guarda referencias y estado]
        self._rows[name] = {"label": lbl, "bar": bar, "pct": pct, "total": 0}

    """
        Descripción:
            Actualiza el porcentaje de una tarea. Si la tarea no existe, la crea.
            Se muestra únicamente el porcentaje (0–100).

        Entradas:
            - name (str): nombre de la tarea (tqdm u otro emisor).
            - n (int|float): progreso actual (iteración/contador).
            - total (int|float|None): total esperado para calcular %; si no hay, %→0.
            - _rate_text (str|None): texto de tasa (no usado en UI).
            - _eta_text (str|None): texto de ETA (no usado en UI).

        Salidas:
            - None (efecto: barra y etiqueta de % actualizadas).

        Detalles:
            - Guarda “total” en el estado de la fila por si te interesa en futuros cálculos.
    """
    def update_task(self, name, n, total, _rate_text=None, _eta_text=None) -> None:

        # [Localiza/crea la fila y normaliza total]
        name = _canonical(name)
        row = self._rows.get(name)
        if not row:
            self._make_row(name)
            row = self._rows[name]

        total = int(total) if total else 0
        row["total"] = total

        # [Calcular % de forma segura]
        pct = int((int(n) / total) * 100) if total else 0

        # [Actualizar widgets]
        row["bar"]["value"] = pct
        row["pct"]["text"] = f"{pct}%"

    """
        Descripción:
            Agrega una línea de texto al panel de log (auto-scroll).

        Entradas:
            - text (str): mensaje a añadir.

        Salidas:
            - None (efecto: se actualiza el Text y se desplaza al final).
        """
    def write_log(self, text: str) -> None:

        # [Habilitar edición, insertar texto, auto-scroll y volver a deshabilitar]
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    """
        Descripción:
            Encola de manera thread-safe una llamada a un método/función de la UI
            para ser ejecutada en el hilo principal (evita llamadas directas desde hilos).

        Entradas:
            - fn (callable): función a ejecutar en el hilo de UI.
            - *args, **kwargs: argumentos para la función.

        Salidas:
            - None (efecto: item encolado, ejecutado por _pump() en el main thread).

        Notas:
            - Usa queue.Queue non-blocking; si falla la encolada, se ignora con seguridad.
        """
    def enqueue(self, fn, *args, **kwargs) -> None:
        try:
            self._q.put(("call", fn, args, kwargs), block=False)
        except Exception:
            # [Fallo no crítico de encolado: no romper la UI]
            pass

    """
        Descripción:
            Bucle de despacho de eventos encolados. Extrae items de la cola y los ejecuta.
            Mantiene la UI reactiva sin bloquear el mainloop.

        Entradas:
            - (ninguna; usa self._q y self._running)

        Salidas:
            - None (efecto: ejecuta llamadas de UI pendientes y reprograma su siguiente ciclo).

    """
    def _pump(self) -> None:

        # [Intentar vaciar cola]
        try:
            while True:
                kind, *rest = self._q.get_nowait()
                if kind == "call":
                    fn, args, kwargs = rest
                    try:
                        fn(*args, **kwargs)
                    except tk.TclError:
                        # UI cerrándose; ignora sin romper loop
                        pass
        except queue.Empty:
            pass
        except Exception:
            # [Cualquier otro error: no reventar el loop de interfaz]
            pass

        # [Reprogramar si la UI sigue viva]
        if self._running:
            self._schedule_pump()

    """
        Descripción:
            Programa la próxima ejecución de _pump() usando after(). Guarda el id para
            cancelarlo en stop().

        Entradas:
            - (ninguna)

        Salidas:
            - None (efecto: self._after_id actualizado).
        """
    def _schedule_pump(self) -> None:

        try:
            self._after_id = self.after(50, self._pump)
        except tk.TclError:
            # Ventana destruida o cerrándose
            pass

    """
        Descripción:
            Detiene el ciclo programado (_after) de la UI antes de destruir la ventana.
            Evita callbacks tardíos que generen errores.

        Entradas:
            - (ninguna)

        Salidas:
            - None (efecto: _running=False y after_cancel si aplica).
        """
    def stop(self) -> None:

        self._running = False
        if self._after_id is not None:
            try:
                self.after_cancel(self._after_id)
            except tk.TclError:
                pass
            self._after_id = None

    """
        Descripción:
           Callback del evento de cerrar ventana (WM_DELETE_WINDOW).
           Realiza cierre seguro: detiene el ciclo y destruye la ventana.

        Entradas:
           - (evento implícito del sistema de ventanas)

        Salidas:
           - None (efecto: ventana destruida).
        """
    def _on_close(self) -> None:
        # [Detener ciclo y destruir sin dejar afters pendientes]
        self.stop()
        try:
            self.destroy()
        except tk.TclError:
            pass

    """
        Descripción:
            Muestra en el “footer” dos botones: (1) abrir la carpeta de salida y
            (2) “Volver al menú” (ejecuta callback on_back), pensados para usarse
            al finalizar el procesamiento.

        Entradas:
            - out_dir (str): ruta de la carpeta a abrir en el explorador del SO.
            - on_back (callable): función sin argumentos para “volver al menú”.

        Salidas:
            - None (efecto: footer poblado con los botones).

        """

    def show_actions(self, out_dir: str, on_back) -> None:

        # [Limpiar footer]
        for w in self._footer.winfo_children():
            w.destroy()

        # [Función interna para abrir rutas por SO]
        def _open_folder(path):
            try:
                if sys.platform.startswith("win"):
                    os.startfile(path)                # Windows
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", path])  # macOS
                else:
                    subprocess.Popen(["xdg-open", path])  # Linux
            except Exception as e:
                self.write_log(f"No se pudo abrir la carpeta: {e}")

        # [Contenedor y botones]
        row = ttk.Frame(self._footer)
        row.grid(row=0, column=0, sticky="ew")
        row.columnconfigure(0, weight=1)  # separador elástico

        btn_open = ttk.Button(row, text="Abrir carpeta de salida",
                              command=lambda: _open_folder(out_dir))
        btn_back = ttk.Button(row, text="Volver al menú",
                              command=lambda: (self.destroy(), on_back()))

        # Distribución: [abrir][espaciador elástico][volver]
        btn_open.grid(row=0, column=0, padx=(0, 6), pady=2, sticky="w")
        ttk.Label(row, text="").grid(row=0, column=1, sticky="ew")
        btn_back.grid(row=0, column=2, padx=(6, 0), pady=2, sticky="e")

        # [Refuerzos de visualización]
        self._footer.update_idletasks()
        try:
            self.attributes("-topmost", True)
            self.after(600, lambda: self.attributes("-topmost", False))
        except Exception:
            pass


"""
    Descripción:
        Helper para ejecutar una función “target” en un hilo de fondo mientras
        se muestra esta UI de progreso. Es un atajo por si no tienes una UI
        más compleja integrada.

    Entradas:
        - target (callable): función sin argumentos que realiza el trabajo.
        - title (str, opcional): título de ventana.

    Salidas:
        - Devuelve el valor de retorno de target si todo sale bien.
        - Relanza excepciones de target tras cerrar la UI.

    """
def run_with_progress(target, *, title="Procesando…"):

    ui = ProgressUI(title=title)

    # [Estructuras para pasar resultado/errores entre hilos]
    result_holder = {"value": None, "error": None}
    done = threading.Event()

    def _runner():
        # [Ejecutar target y capturar errores]
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
        # [Cerrar UI cuando termine el worker]
        if done.is_set():
            ui.stop()
            ui.after(300, ui.destroy)
            return
        ui.after(150, _check_done)

    ui.after(150, _check_done)
    ui.mainloop()

    # [Propagar error o devolver resultado]
    if result_holder["error"]:
        raise result_holder["error"]
    return result_holder["value"]
