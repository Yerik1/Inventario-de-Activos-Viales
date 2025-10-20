import numpy as np

def patch_gps_sources(gps_stub):
    import pavimentados.analyzers.gps_sources as gps_sources
    _Original_GPS_Data_Loader = gps_sources.GPS_Data_Loader
    gps_sources.GPS_Data_Loader = gps_stub
    return _Original_GPS_Data_Loader

def patch_workflows_gps(gps_stub):
    import pavimentados.processing.workflows as workflows
    if hasattr(workflows, "GPS_Data_Loader"):
        workflows.GPS_Data_Loader = gps_stub

def wrap_safe_predict(ml_processor):
    _orig_predict = ml_processor.processor.yolov8_paviment_model.predict

    def _safe_predict(img_batch):
        try:
            return _orig_predict(img_batch)
        except ValueError as e:
            if "need at least one array to stack" in str(e):
                empty_boxes = np.zeros((0, 4), dtype=float)
                empty_scores = np.zeros((0,), dtype=float)
                empty_classes = np.zeros((0,), dtype=int)
                return empty_boxes, empty_scores, empty_classes
            raise
    ml_processor.processor.yolov8_paviment_model.predict = _safe_predict

def patch_overlay_utils(code_to_desc: dict):
    import pavimentados.processing.utils as _utils

    def _map_first_line(text: str) -> str:
        parts = str(text).split("\n")
        if parts:
            parts[0] = code_to_desc.get(parts[0], parts[0])
        return "\n".join(parts)

    _original_create_output = getattr(_utils, "create_output_from_results", None)

    if callable(_original_create_output):
        def _create_output_from_results_mapped(results, *args, **kwargs):
            out = _original_create_output(results, *args, **kwargs)
            try:
                import pandas as pd
                if isinstance(results, pd.DataFrame) and "final_classes" in results.columns and "score" in results.columns:
                    _res2 = results.copy()
                    _res2["__mapped_text__"] = _res2.apply(
                        lambda row: _map_first_line(f"{row.final_classes}\n{round(row.score, 4)}"), axis=1
                    )
                    _res2["final_classes"] = _res2["__mapped_text__"].apply(lambda s: s.split("\n")[0])
                    return _original_create_output(_res2, *args, **kwargs)
            except Exception:
                pass
            return out
        _utils.create_output_from_results = _create_output_from_results_mapped

    _original_put_text = getattr(_utils, "put_text", None)
    if callable(_original_put_text):
        def _put_text_with_mapping(frame, text, position, color=(255, 255, 255)):
            try:
                text = _map_first_line(text)
            except Exception:
                pass
            return _original_put_text(frame, text, position, color=color)
        _utils.put_text = _put_text_with_mapping

def install_tqdm_bridge(callback, max_hz=10):
    """
    Llama a callback(desc, n, total, rate_text, eta_text) con rate-limit.
    """
    import time
    try:
        import tqdm as _tqdm_mod
    except Exception:
        return

    min_dt = 1.0 / float(max_hz)
    state = {"last_t": 0.0, "last_pct": {}}

    def _should_emit(desc, n, total):
        now = time.perf_counter()
        pct = int((n / total) * 100) if total else 0
        last_pct = state["last_pct"].get(desc, -1)
        if pct != last_pct and (now - state["last_t"]) >= min_dt:
            state["last_t"] = now
            state["last_pct"][desc] = pct
            return True
        return False

    def _wrap(TQDM_CLS):
        if getattr(TQDM_CLS, "__patched_ui__", False):
            return TQDM_CLS
        _init, _update = TQDM_CLS.__init__, TQDM_CLS.update
        _set_desc = getattr(TQDM_CLS, "set_description", None)

        def __init__(self, *a, **k):
            _init(self, *a, **k)
            self._ui_desc = getattr(self, "desc", None) or "progress"
            self._ui_total = getattr(self, "total", 0) or 0
            try:
                if _should_emit(self._ui_desc, getattr(self, "n", 0), self._ui_total):
                    r = self.format_dict.get("rate", None)
                    e = self.format_dict.get("remaining", None)
                    eta = getattr(self, "format_interval", lambda x: None)(e) if e is not None else None
                    callback(self._ui_desc, getattr(self, "n", 0), self._ui_total, r, eta)
            except Exception:
                pass

        def __update(self, n=1):
            ret = _update(self, n)
            try:
                desc = getattr(self, "_ui_desc", None) or getattr(self, "desc", None) or "progress"
                total = getattr(self, "_ui_total", 0) or getattr(self, "total", 0) or 0
                if _should_emit(desc, getattr(self, "n", 0), total):
                    r = self.format_dict.get("rate", None)
                    e = self.format_dict.get("remaining", None)
                    eta = getattr(self, "format_interval", lambda x: None)(e) if e is not None else None
                    callback(desc, getattr(self, "n", 0), total, r, eta)
            except Exception:
                pass
            return ret

        def __set_description(self, desc=None, **kwargs):
            if _set_desc:
                _set_desc(self, desc=desc, **kwargs)
            self._ui_desc = desc or self._ui_desc

        TQDM_CLS.__init__ = __init__
        TQDM_CLS.update = __update
        if _set_desc:
            TQDM_CLS.set_description = __set_description
        TQDM_CLS.__patched_ui__ = True
        return TQDM_CLS

    try:
        _wrap(_tqdm_mod.tqdm)
    except Exception:
        pass
    try:
        from tqdm import auto as _auto
        _wrap(_auto.tqdm)
    except Exception:
        pass