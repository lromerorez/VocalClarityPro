import os
import argparse
from pathlib import Path
import logging
import sys

# --- Configuración del Logging ---
log_dir = "logs_file_cleanup"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "file_cleanup.log")

logging.basicConfig(
    level=logging.INFO, # Nivel mínimo de mensajes a registrar
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
# ------------------------------------------------------------------

def find_and_clean_files(directory_path, dry_run, criteria):
    """
    Busca archivos en el directorio y subdirectorios.
    Si dry_run es True, solo muestra los archivos a borrar.
    Si dry_run es False, borra los archivos que no cumplen los criterios.
    """
    dir_path = Path(directory_path)

    if not dir_path.exists() or not dir_path.is_dir():
        logging.critical(f"❌ La ruta proporcionada no existe o no es un directorio válido: {directory_path}")
        return

    logging.info(f"Escaneando directorio: '{directory_path}' para archivos...")
    logging.info(f"Criterios para MANTENER el archivo: El nombre debe contener 'rubirico', 'Rubi' O '085205'.")
    logging.info(f"Modo: {'SIMULACIÓN (ningún archivo será borrado)' if dry_run else 'BORRADO REAL (¡PRECAUCIÓN!)'}")

    files_to_delete_count = 0
    files_kept_count = 0

    for file_path in dir_path.rglob('*'): # Recorre recursivamente todos los archivos y directorios
        if file_path.is_file(): # Solo procesar archivos
            file_name = file_path.name
            
            # Verificar si el nombre del archivo contiene alguno de los criterios
            # Usamos .lower() para 'rubirico' y 'Rubi' para que sea insensible a mayúsculas/minúsculas
            # '085205' se busca literalmente
            keep_file = False
            if "rubirico" in file_name.lower():
                keep_file = True
            elif "Rubi" in file_name: # Aquí 'Rubi' es sensible a mayúsculas/minúsculas como lo pediste
                keep_file = True
            elif "085205" in file_name:
                keep_file = True
            
            if not keep_file:
                files_to_delete_count += 1
                if dry_run:
                    logging.info(f"[SIMULACIÓN BORRADO] -> '{file_path}' (No cumple criterios)")
                else:
                    try:
                        file_path.unlink() # Borrar el archivo
                        logging.info(f"[BORRADO REAL] -> '{file_path}'")
                    except Exception as e:
                        logging.error(f"[ERROR BORRADO] No se pudo borrar '{file_path}': {e}", exc_info=True)
            else:
                files_kept_count += 1
                logging.debug(f"[MANTENIDO] -> '{file_path}' (Cumple criterios)") # Usa DEBUG para no saturar el log INFO

    logging.info(f"--- Resumen del Proceso ---")
    logging.info(f"Archivos encontrados que NO cumplen los criterios y serían borrados: {files_to_delete_count}")
    logging.info(f"Archivos encontrados que SÍ cumplen los criterios y serían mantenidos: {files_kept_count}")
    logging.info(f"Proceso finalizado. Revisa el log para detalles.")
    
    if dry_run:
        print("\n🏁 Proceso de SIMULACIÓN finalizado. NINGÚN archivo fue borrado.")
        print("Revisa el log en 'logs_file_cleanup/file_cleanup.log' para ver qué archivos *serían* borrados.")
        print("Si la lista es correcta, vuelve a ejecutar el script añadiendo '--confirm-delete' al comando.")
    else:
        print("\n🏁 Proceso de BORRADO REAL finalizado. Revisa el log en 'logs_file_cleanup/file_cleanup.log' para más detalles.")
        print("¡Los archivos listados como BORRADOS han sido eliminados de forma PERMANENTE!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Borra archivos que NO contienen criterios específicos en su nombre.")
    parser.add_argument("directory", help="Ruta de la carpeta donde buscar archivos.")
    parser.add_argument("--confirm-delete", action="store_true", 
                        help="¡CONFIRMA EL BORRADO REAL! Por defecto, el script solo simula el borrado.")
    args = parser.parse_args()

    # Definimos los criterios de búsqueda. El script busca "rubirico", "Rubi" o "085205".
    # Importante: 'rubirico' se compara en minúsculas, 'Rubi' es sensible a mayúsculas/minúsculas.
    # '085205' se busca textualmente.
    search_criteria = {
        "rubirico": {"case_sensitive": False}, # Buscamos "rubirico" o "Rubirico" o "RUBIRICO"
        "Rubi": {"case_sensitive": True},    # Buscamos "Rubi" (exacto)
        "085205": {"case_sensitive": True}   # Buscamos "085205" (exacto)
    }

    find_and_clean_files(args.directory, not args.confirm_delete, search_criteria)