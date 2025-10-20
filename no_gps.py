"""
no_gps.py
----------
Descripción general:
Este módulo define una clase **NoGPS**, utilizada como “stub” o simulación de datos GPS
cuando el pipeline no dispone de un archivo real. Proporciona las mismas estructuras
(tablas y arrays) que las clases reales de GPS, pero vacías o con valores neutros,
permitiendo que el resto del flujo de trabajo funcione sin errores.

Estructura:
- Clase NoGPS: simula un dataset GPS mínimo y compatible con el pipeline.
- Función make_gps_stub(): retorna un "loader" que crea instancias de NoGPS.
"""
import numpy as np
import pandas as pd

"""
   Clase: NoGPS
   ------------
   Descripción:
       Simula un conjunto de datos GPS vacío. Se usa cuando el flujo se ejecuta
       sin un archivo GPS real. Mantiene la misma interfaz (atributos y métodos)
       que el objeto GPS original para asegurar compatibilidad con workflows.

   Entradas (constructor):
       - vid_duration (float): duración del video en segundos, usada para sincronizar.

   Salidas:
       - Objeto NoGPS con DataFrames y arrays vacíos.

   Variables declaradas en __init__:
       - df_points, df_sections: DataFrames vacíos con las columnas esperadas.
       - gps_df, gps_sections_df: alias para compatibilidad con otros módulos.
       - section_latitude, section_longitude, section_distances, section_ids:
         arrays vacíos (1D) que simulan estructuras reales.
       - routes, route, points, data, metrics, sections: atributos vacíos genéricos.
       - gps_duration: duración del GPS simulada (≈ vid_duration).
       - gps_fps: valor por defecto (1.0).
       - start_time, end_time: marcadores temporales (None).
       - total_distance_m, sections_distance: métricas en metros (inicialmente 0).
   """
class NoGPS:
    def __init__(self, vid_duration: float):
        # [Crear DataFrames vacíos con las columnas esperadas]
        self.df_points = pd.DataFrame(
            columns=["frame", "time", "latitude", "longitude", "distances", "section"]
        )
        self.df_sections = pd.DataFrame(
            columns=["section_id", "start_frame", "end_frame", "length_m"]
        )

        # [Crear alias para compatibilidad con otros componentes del pipeline]
        self.gps_df = self.df_points.copy()
        self.gps_sections_df = self.df_sections.copy()

        # [Inicializar arrays 1D vacíos con tipos correctos]
        self.section_latitude  = np.array([], dtype=float)
        self.section_longitude = np.array([], dtype=float)
        self.section_distances = np.array([], dtype=float)
        self.section_ids       = np.array([], dtype=int)

        # [Atributos comunes esperados por otras clases]
        self.routes = []
        self.route = None
        self.points = []
        self.data = []
        self.metrics = {}
        self.sections = []

        # [Métricas y tiempos básicos]
        eps = 1e-3
        self.gps_duration = max(float(vid_duration) - eps, 0.0)
        self.gps_fps = 1.0
        self.start_time = None
        self.end_time = None
        self.total_distance_m = 0.0
        self.sections_distance = 0.0

    """Devuelve 0, indicando que no hay puntos GPS."""
    def __len__(self):
        return 0

    """
        Descripción:
            Intercepta accesos a atributos inexistentes devolviendo None.
            Evita errores si el pipeline intenta acceder a propiedades GPS reales.
        """
    def __getattr__(self, name):
        # Para cualquier atributo no definido, retornar algo neutro
        return None

    """
        Descripción:
            Genera un diccionario de métricas GPS (vacías o nulas) para mantener
            compatibilidad con el pipeline.

        Entradas:
            - gps_sections_distance (float|None): distancia total de secciones.

        Salidas:
            - None (efecto: actualiza self.metrics y los DataFrames alias).

        """
    def generate_gps_metrics(self, gps_sections_distance=None):
        # [Actualizar distancia y métricas simuladas]
        self.sections_distance = gps_sections_distance or 0.0
        self.metrics = {
            "sections_distance": self.sections_distance,
            "count_points": 0,
            "total_distance_m": self.total_distance_m,
            "gps_duration": self.gps_duration
        }

        # [Asegurar consistencia de alias y arrays]
        self.gps_df = self.df_points.copy()
        self.gps_sections_df = self.df_sections.copy()
        if self.section_latitude is None:  self.section_latitude  = np.array([], dtype=float)
        if self.section_longitude is None: self.section_longitude = np.array([], dtype=float)
        if self.section_distances is None: self.section_distances = np.array([], dtype=float)
        if self.section_ids is None:       self.section_ids       = np.array([], dtype=int)

    """Retorna una copia del DataFrame de secciones simuladas."""
    def get_sections_table(self):
        return self.gps_sections_df.copy()

    """Retorna una copia del DataFrame de puntos GPS simulados."""
    def get_points_table(self):
        return self.gps_df.copy()

    """
        Descripción:
            Devuelve un diccionario con los campos esperados para un frame dado.
            Todos los valores son None o neutros.

        Entradas:
            - frame_index (int): número del frame solicitado.

        Salidas:
            - dict: con campos latitude, longitude, time, etc.
        """
    def get_frame_gps(self, frame_index):
        return {
            "lat": None, "lon": None, "time": None,
            "latitude": None, "longitude": None,
            "frame": frame_index, "section": None, "distances": None
        }

    """
        Descripción:
            Sincroniza el stub GPS con la cantidad de frames del video.
            Genera un DataFrame con tiempo y distancia lineales ficticios.

        Entradas:
            - video_fps (float|None): cuadros por segundo del video.
            - n_frames (int|None): total de frames.

        Salidas:
            - None (efecto: actualiza df_points y df_sections vacíos).     
    """
    def sync_with_video(self, video_fps=None, n_frames=None):
        if (video_fps is None) or (video_fps <= 0) or (n_frames is None) or (n_frames <= 0):
            return

        # [Generar arrays base]
        frames = np.arange(int(n_frames), dtype=int)
        times = frames / float(video_fps)

        # [Crear DataFrame de puntos GPS vacíos pero sincronizados con el video]
        self.df_points = pd.DataFrame({
            "frame": frames,
            "time": times,
            "latitude": np.nan,
            "longitude": np.nan,
            "distances": np.linspace(0.0, float(len(frames) - 1), len(frames)),
            "section": np.zeros(len(frames), dtype=int)
        })
        self.gps_df = self.df_points.copy()

        # [Reiniciar secciones (vacías)]
        self.df_sections = pd.DataFrame(columns=["section_id", "start_frame", "end_frame", "length_m"])
        self.gps_sections_df = self.df_sections.copy()

    """
        Descripción breve:
            Genera un GeoJSON vacío (sin features), manteniendo compatibilidad
            con funciones que esperan exportar geometrías.

        Entradas:
            - *args, **kwargs: ignorados (solo para compatibilidad de firma).

        Salidas:
            - dict: estructura GeoJSON vacía.
        """
    def to_geojson(self, *args, **kwargs):
        return {"type": "FeatureCollection", "features": []}


"""
    Descripción breve:
        Devuelve una función “loader” compatible con workflows.GPS_Data_Loader.
        Esta función, al ser llamada, retornará una instancia de NoGPS simulando
        una fuente GPS basada en la duración del video.

    Entradas:
        - video_duration (float): duración del video en segundos.

    Salidas:
        - (_gps_stub): función que retorna NoGPS(video_duration).

    """
def make_gps_stub(video_duration: float):
    """Devuelve una función loader compatible con workflows.GPS_Data_Loader."""
    def _gps_stub(source_type, gps_in, config, **kwargs):
        # Ignora argumentos y retorna instancia simulada
        return NoGPS(video_duration)
    return _gps_stub
