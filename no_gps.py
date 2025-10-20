import numpy as np
import pandas as pd

class NoGPS:
    """
    Stub de GPS: provee tablas y arrays esperados por el pipeline.
    Incluye columnas necesarias y arrays 1D vacíos para secciones.
    """
    def __init__(self, vid_duration: float):
        # DataFrames con columnas que el pipeline usa
        self.df_points = pd.DataFrame(
            columns=["frame", "time", "latitude", "longitude", "distances", "section"]
        )
        self.df_sections = pd.DataFrame(
            columns=["section_id", "start_frame", "end_frame", "length_m"]
        )

        # Aliases que el calculator/workflow buscan
        self.gps_df = self.df_points.copy()
        self.gps_sections_df = self.df_sections.copy()

        # Arrays de secciones (DEBEN ser 1D, aunque vacíos)
        self.section_latitude  = np.array([], dtype=float)
        self.section_longitude = np.array([], dtype=float)
        self.section_distances = np.array([], dtype=float)
        self.section_ids       = np.array([], dtype=int)

        # Atributos comunes
        self.routes = []
        self.route = None
        self.points = []
        self.data = []
        self.metrics = {}
        self.sections = []

        # Métricas y tiempos
        eps = 1e-3
        self.gps_duration = max(float(vid_duration) - eps, 0.0)
        self.gps_fps = 1.0
        self.start_time = None
        self.end_time = None
        self.total_distance_m = 0.0
        self.sections_distance = 0.0

    def __len__(self):
        return 0

    def __getattr__(self, name):
        # Para cualquier atributo no definido, retornar algo neutro
        return None

    def generate_gps_metrics(self, gps_sections_distance=None):
        self.sections_distance = gps_sections_distance or 0.0
        self.metrics = {
            "sections_distance": self.sections_distance,
            "count_points": 0,
            "total_distance_m": self.total_distance_m,
            "gps_duration": self.gps_duration
        }
        # Mantener consistencia de alias y arrays 1D vacíos
        self.gps_df = self.df_points.copy()
        self.gps_sections_df = self.df_sections.copy()
        if self.section_latitude is None:  self.section_latitude  = np.array([], dtype=float)
        if self.section_longitude is None: self.section_longitude = np.array([], dtype=float)
        if self.section_distances is None: self.section_distances = np.array([], dtype=float)
        if self.section_ids is None:       self.section_ids       = np.array([], dtype=int)

    def get_sections_table(self):
        return self.gps_sections_df.copy()

    def get_points_table(self):
        return self.gps_df.copy()

    def get_frame_gps(self, frame_index):
        return {
            "lat": None, "lon": None, "time": None,
            "latitude": None, "longitude": None,
            "frame": frame_index, "section": None, "distances": None
        }

    def sync_with_video(self, video_fps=None, n_frames=None):
        if (video_fps is None) or (video_fps <= 0) or (n_frames is None) or (n_frames <= 0):
            return
        frames = np.arange(int(n_frames), dtype=int)
        times = frames / float(video_fps)

        self.df_points = pd.DataFrame({
            "frame": frames,
            "time": times,
            "latitude": np.nan,
            "longitude": np.nan,
            "distances": np.linspace(0.0, float(len(frames) - 1), len(frames)),
            "section": np.zeros(len(frames), dtype=int)
        })
        self.gps_df = self.df_points.copy()

        self.df_sections = pd.DataFrame(columns=["section_id", "start_frame", "end_frame", "length_m"])
        self.gps_sections_df = self.df_sections.copy()

    def to_geojson(self, *args, **kwargs):
        return {"type": "FeatureCollection", "features": []}


def make_gps_stub(video_duration: float):
    """Devuelve una función loader compatible con workflows.GPS_Data_Loader."""
    def _gps_stub(source_type, gps_in, config, **kwargs):
        return NoGPS(video_duration)
    return _gps_stub
