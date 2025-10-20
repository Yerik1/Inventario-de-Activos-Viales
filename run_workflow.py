from pavimentados.processing.workflows import Workflow_Processor

def run_workflow(input_video: str,
                 ml_processor,
                 gps_source_type: str = "loc",
                 gps_input=None,
                 batch_size: int = 8,
                 video_output_file: str = "Salidas/salida_detectada.mp4",
                 min_fotogram_distance: int = 1):
    workflow = Workflow_Processor(
        input_video,
        image_source_type="video",
        gps_source_type=gps_source_type,
        gps_input=gps_input
    )
    results = workflow.execute(
        ml_processor,
        batch_size=batch_size,
        video_output_file=video_output_file,
        min_fotogram_distance=min_fotogram_distance
    )
    return results
