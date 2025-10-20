from pavimentados.processing.processors import MultiImage_Processor

def load_ml_processor(artifacts_path: str, config_file: str) -> MultiImage_Processor:
    return MultiImage_Processor(
        artifacts_path=str(artifacts_path),
        config_file=config_file
    )
