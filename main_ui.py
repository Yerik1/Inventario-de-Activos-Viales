"""
main_ui.py
----------------
Descripción general:
Este módulo implementa la INTERFAZ GRÁFICA (GUI) principal de la aplicación usando Tkinter.
Separa la lógica de procesamiento de la capa de presentación. Aquí se gestiona:
- Ventana inicial para seleccionar video .mp4 y carpeta de salida.
- Habilitar el botón "Empezar" cuando ambas rutas son válidas.
- Llamar a la lógica del pipeline y controlar el “volver al menú” tras finalizar.
- Punto de entrada (main) de la app.

"""

from pathlib import Path
from tkinter import Tk, ttk, filedialog
from main import run_with_ui

"""
    Clase de interfaz principal (ventana menú).
    Entradas:  (ninguna en el constructor)
    Salidas:   Ventana Tk que orquesta la selección de paths y el disparo del pipeline.
    """
class MainUI(Tk):

    def __init__(self):
        # [Inicialización de la ventana y estado]
        super().__init__()
        self.title("Inventario de Activos Viales")
        self.geometry("520x240")
        self.resizable(False, False)

        # - video_path: ruta al archivo .mp4 seleccionado por el usuario (None si no se ha elegido).
        # - output_dir: ruta a la carpeta de salida (None si no se ha elegido).
        self.video_path: Path | None = None
        self.output_dir: Path | None = None

        # [Header de la ventana]
        title = ttk.Label(self, text="Inventario de Activos Viales", font=("Segoe UI", 14, "bold"))
        title.pack(pady=(18, 6))

        # [Fila de información de selección actual]
        self.lbl_video = ttk.Label(self, text="Video: (no seleccionado)")
        self.lbl_video.pack(fill="x", padx=16, pady=(6, 0))
        self.lbl_out = ttk.Label(self, text="Carpeta de salida: (no seleccionada)")
        self.lbl_out.pack(fill="x", padx=16, pady=(2, 10))

        # [Botonera principal]
        frm = ttk.Frame(self)
        frm.pack(pady=8)

        self.btn_video = ttk.Button(frm, text="Seleccionar video (.mp4)", command=self.select_video)
        self.btn_video.grid(row=0, column=0, padx=6, pady=6)

        self.btn_out = ttk.Button(frm, text="Seleccionar carpeta de salida", command=self.select_output_dir)
        self.btn_out.grid(row=0, column=1, padx=6, pady=6)

        # Botón Empezar: deshabilitado hasta que haya video y carpeta
        self.btn_start = ttk.Button(self, text="Empezar", command=self.start_process, state="disabled")
        self.btn_start.pack(pady=(6, 8))

        # [Pie de ayuda]
        ttk.Label(self, text="Seleccione video y carpeta de salida, luego presione Empezar.").pack(pady=(0, 6))

    """
        Abre el diálogo de archivo para escoger el .mp4.
        Entradas:  interacción del usuario (diálogo).
        Salidas:   actualiza self.video_path y etiqueta visual; revalida el botón Empezar.
        """
    def select_video(self):

        # [Abrir diálogo y asignar selección]
        videoPath = filedialog.askopenfilename(
            title="Seleccionar video de entrada (.mp4)",
            filetypes=[("Archivos de video", "*.mp4")]
        )

        # - videoPath: str | "" ruta absoluta seleccionada; cadena vacía si se cancela.
        if videoPath:
            self.video_path = Path(videoPath)
            self.lbl_video.config(text=f"Video: {self.video_path.name}")
        # [Revalidar si se puede habilitar “Empezar”]
        self._update_start_state()

    """
        Abre el diálogo para seleccionar la carpeta de salida.
        Entradas:  interacción del usuario (diálogo).
        Salidas:   actualiza self.output_dir y etiqueta visual; revalida el botón Empezar.
        """
    def select_output_dir(self):
        outputPath = filedialog.askdirectory(title="Seleccionar carpeta de salida")

        # - outputPath: str | "" ruta absoluta seleccionada; cadena vacía si se cancela.
        if outputPath:
            self.output_dir = Path(outputPath)
            self.lbl_out.config(text=f"Carpeta de salida: {self.output_dir}")
        self._update_start_state()

    """
        Habilita o deshabilita el botón “Empezar” según haya video y carpeta de salida.
        Entradas:  estado interno self.video_path y self.output_dir.
        Salidas:   actualiza estado del botón.
        """
    def _update_start_state(self):

        # [Comprobación de disponibilidad]
        ok = (self.video_path is not None) and (self.output_dir is not None)
        self.btn_start.config(state=("normal" if ok else "disabled"))

    """
        Ejecuta la interfaz de progreso y oculta el menú.
        Entradas:  self.video_path (Path), self.output_dir (Path)
        Salidas:   invoca run_with_ui; al finalizar, callback re-muestra el menú.
        """
    def start_process(self):
        # [Validación previa]
        if not self.video_path or not self.output_dir:
            return

        # [Ocultar menú mientras corre el pipeline]
        self.withdraw()

        # [Lanzar pipeline. on_back vuelve a mostrar el menú tras terminar o cerrar]
        run_with_ui(
            input_video=self.video_path,
            output_dir=self.output_dir,
            on_back=lambda: self.deiconify()
        )


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
