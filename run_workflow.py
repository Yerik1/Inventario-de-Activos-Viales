"""
run_workflow.py
---------------
Descripción general:
Encapsula la ejecución del **workflow principal** de la librería `pavimentados`.
Coordina el procesamiento del video, aplicando el modelo ML y las entradas de GPS,
y devuelve los resultados estructurados. Actúa como una capa intermedia entre
la lógica de alto nivel y la API del paquete pavimentados.

Estructura:
- run_workflow(): configura y ejecuta el `Workflow_Processor` con los parámetros dados.

Requisitos:
- Paquete externo `pavimentados.processing.workflows`.
"""
from pavimentados.processing.workflows import Workflow_Processor

"""
    Descripción:
        Ejecuta el procesamiento principal del flujo de trabajo con el modelo cargado.
        Se encarga de crear el objeto `Workflow_Processor`, configurarlo y correrlo.

    Entradas:
        - input_video (str): ruta al archivo de video de entrada.
        - ml_processor: instancia del modelo (retornada por load_ml_processor()).
        - gps_source_type (str): tipo de fuente GPS (“loc”, “file”, etc.).
        - gps_input: ruta o fuente de datos GPS (None si no se usa).
        - batch_size (int): tamaño de lote de frames para procesar por iteración.
        - video_output_file (str): ruta del video de salida con detecciones dibujadas.
        - min_fotogram_distance (int): distancia mínima entre fotogramas procesados.

    Salidas:
        - (objeto results): resultados del método `workflow.execute()` del procesador.

    Variables declaradas:
        - workflow (Workflow_Processor): instancia del flujo principal.
        - results (objeto): salida del método execute() con los resultados procesados.
    """
def run_workflow(input_video: str,
                 ml_processor,
                 gps_source_type: str = "loc",
                 gps_input=None,
                 batch_size: int = 8,
                 video_output_file: str = "Salidas/salida_detectada.mp4",
                 min_fotogram_distance: int = 1):

    # [Crear instancia del workflow con las fuentes especificadas]
    workflow = Workflow_Processor(
        input_video,
        image_source_type="video",
        gps_source_type=gps_source_type,
        gps_input=gps_input
    )

    # [Ejecutar procesamiento principal]
    results = workflow.execute(
        ml_processor,
        batch_size=batch_size,
        video_output_file=video_output_file,
        min_fotogram_distance=min_fotogram_distance
    )

    # [Retornar resultados]
    return results
