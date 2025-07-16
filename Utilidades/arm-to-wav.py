import os
import subprocess
from pathlib import Path
import logging
import sys

# --- Configuración del Logging ---
# Los logs se guardarán en una carpeta específica para la conversión de AMR a WAV
log_dir = "logs_amr_to_wav_conversion"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "amr_to_wav_conversion.log")

logging.basicConfig(
    level=logging.INFO, # Nivel mínimo de mensajes a registrar
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
# ------------------------------------------------------------------

def check_sox_installed():
    """Verifica si Sox está instalado en el sistema."""
    try:
        subprocess.run(["sox", "--version"], check=True, capture_output=True, text=True)
        logging.info("Sox está instalado y accesible en el PATH del sistema.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.critical("Sox no está instalado o no está en el PATH del sistema. Es necesario para la conversión.")
        logging.critical("Por favor, instala Sox. En Arch Linux: sudo pacman -S sox")
        return False

def convert_amr_to_wav(input_path, output_dir):
    """
    Convierte un archivo AMR a formato WAV (16-bit PCM).
    Sox es excelente para esto ya que AMR es un formato de voz.
    """
    input_path = Path(input_path)
    # Crear la ruta de salida con el mismo nombre y extensión .wav
    output_path = Path(output_dir) / (input_path.stem + ".wav")

    if output_path.exists():
        logging.warning(f"El archivo WAV de salida ya existe, sobrescribiendo: {output_path}")
        output_path.unlink() # Eliminar el archivo existente

    try:
        logging.info(f"Convirtiendo {input_path} (AMR) a {output_path} (WAV)...")
        # Usamos -b 16 para asegurar que el WAV de salida sea de 16 bits PCM.
        # Sox manejará la descompresión de AMR a WAV de forma automática.
        result = subprocess.run(
            ["sox", str(input_path), "-b", "16", str(output_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=3600 # Tiempo límite de 1 hora para archivos muy grandes
        )
        logging.info(f"[✅] Archivo convertido con éxito: {output_path}")
        if result.stdout:
            logging.debug(f"Sox Stdout: {result.stdout.strip()}")
        if result.stderr:
            logging.debug(f"Sox Stderr: {result.stderr.strip()}")
        return True
    except subprocess.TimeoutExpired:
        logging.error(f"[⚠️] La conversión de {input_path} a WAV excedió el tiempo límite ({3600/3600} hora).")
        if output_path.exists():
            output_path.unlink()
        return False
    except subprocess.CalledProcessError as e:
        logging.error(f"[❌] Error al convertir {input_path} a WAV: {e.returncode}")
        logging.error(f"  Stdout (Sox): {e.stdout.strip()}")
        logging.error(f"  Stderr (Sox): {e.stderr.strip()}")
        if output_path.exists():
            output_path.unlink()
        return False
    except FileNotFoundError:
        logging.error("El comando 'sox' no fue encontrado. Esto debería ser detectado al inicio.")
        return False
    except Exception as e:
        logging.error(f"[❌] Error inesperado al procesar {input_path}: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    if not check_sox_installed():
        sys.exit(1)

    # Pedimos al usuario la ruta de la carpeta que contiene los archivos AMR
    input_folder_str = input("Introduce la ruta de la CARPETA que contiene los archivos AMR a convertir a WAV: ")
    input_folder = Path(input_folder_str)

    if not input_folder.exists() or not input_folder.is_dir():
        logging.critical(f"❌ La ruta proporcionada no existe o no es un directorio válido: {input_folder_str}")
        sys.exit(1)

    output_base_dir = "converted_amr_to_wav_files"
    os.makedirs(output_base_dir, exist_ok=True)
    logging.info(f"Los archivos WAV convertidos se guardarán en: {output_base_dir}")

    files_to_convert = []
    # Solo buscamos archivos .amr, ya que es el enfoque del script
    amr_ext = ".amr" 

    logging.info(f"Escaneando directorio: {input_folder} y sus subdirectorios para archivos AMR...")
    # rglob busca recursivamente en subdirectorios
    files_to_convert.extend(input_folder.rglob(f"*{amr_ext}"))
    
    if not files_to_convert:
        logging.warning(f"No se encontraron archivos {amr_ext} en el directorio: {input_folder} o sus subdirectorios para convertir a WAV.")
        sys.exit(0) # Salir limpiamente si no hay archivos
    
    logging.info(f"Se encontraron {len(files_to_convert)} archivos AMR para convertir a WAV.")

    for amr_file in files_to_convert:
        convert_amr_to_wav(amr_file, output_base_dir)

    logging.info("🏁 Proceso de conversión de AMR a WAV finalizado.")
    print(f"\n🏁 Proceso de conversión de AMR a WAV finalizado. Revisa '{log_dir}/amr_to_wav_conversion.log' para más detalles.")