"""
loader.py
---------
Descripción general:
Este módulo encapsula la creación del **procesador de imágenes** basado en la clase
`MultiImage_Processor` del paquete `pavimentados`. Sirve como capa de inicialización
de modelos de detección (por ejemplo YOLO) a partir de los archivos y configuraciones
definidos en el proyecto.

Estructura:
- Función load_ml_processor(): crea y retorna una instancia configurada del procesador ML.

Requisitos:
- Módulo externo `pavimentados.processing.processors`.
"""
from pavimentados.processing.processors import MultiImage_Processor

"""
   Descripción:
       Carga e inicializa un procesador de imágenes multi-modelo (MultiImage_Processor)
       usando las rutas de artefactos y archivo de configuración JSON.

   Entradas:
       - artifacts_path (str): ruta a la carpeta donde se encuentran los modelos y pesos.
       - config_file (str): ruta al archivo JSON con la configuración del modelo.

   Salidas:
       - (MultiImage_Processor): instancia lista para usar del procesador ML.
   """
def load_ml_processor(artifacts_path: str, config_file: str) -> MultiImage_Processor:
    # [Crear y retornar instancia del procesador de imágenes]
    return MultiImage_Processor(
        artifacts_path=str(artifacts_path),
        config_file=config_file
    )
