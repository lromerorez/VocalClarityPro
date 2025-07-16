import os
import argparse
import torchaudio
import torch
import subprocess
import noisereduce as nr
from pathlib import Path
from demucs.pretrained import get_model
from demucs.apply import apply_model
import logging
import sys
import platform
import warnings
from tqdm import tqdm

# --- Configuración del Logging ---
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, "audio_processing.log")

logging.basicConfig(
    level=logging.INFO, # Nivel mínimo de mensajes a registrar
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, encoding='utf-8'), # Asegura codificación UTF-8
        logging.StreamHandler(sys.stdout) # También log a la consola
    ]
)

# Función para verificar la instalación de sox
def check_sox_installed():
    try:
        subprocess.run(["sox", "--version"], check=True, capture_output=True, text=True)
        logging.info("Sox está instalado y accesible en el PATH del sistema.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.error("Sox no está instalado o no está en el PATH del sistema.")
        logging.error("Por favor, instala Sox. En Arch Linux: sudo pacman -S sox")
        return False

# Conversión automática con sox
def convert_audio(input_path):
    output_path = Path(str(input_path) + "_converted.wav")
    if output_path.exists():
        logging.warning(f"Archivo de conversión temporal ya existe, sobrescribiendo: {output_path}")
        output_path.unlink() # Eliminar el archivo existente para evitar conflictos

    try:
        logging.info(f"Intentando convertir audio con sox: {input_path} a {output_path}")
        result = subprocess.run(
            ["sox", str(input_path), "-b", "16", "-e", "signed-integer", str(output_path)],
            check=True,
            capture_output=True,
            text=True,
            timeout=600 # Añadir un timeout de 10 minutos para conversiones largas
        )
        logging.info(f"[⚙] Archivo convertido con sox: {output_path}")
        if result.stdout:
            logging.debug(f"Sox Stdout: {result.stdout.strip()}")
        if result.stderr:
            logging.debug(f"Sox Stderr: {result.stderr.strip()}")
        return output_path
    except subprocess.TimeoutExpired:
        logging.error(f"[⚠️] La conversión con sox para {input_path} excedió el tiempo límite ({600/60} minutos).")
        if output_path.exists():
            output_path.unlink() # Limpiar archivo parcial
        return None
    except subprocess.CalledProcessError as e:
        logging.error(f"[⚠️] Error al convertir el archivo con sox: {input_path}")
        logging.error(f"  Código de salida: {e.returncode}")
        logging.error(f"  Stdout (Sox): {e.stdout.strip()}")
        logging.error(f"  Stderr (Sox): {e.stderr.strip()}")
        if output_path.exists():
            output_path.unlink() # Limpiar archivo parcial
        return None
    except FileNotFoundError:
        logging.error("El comando 'sox' no fue encontrado. Asegúrate de que sox esté instalado y en tu PATH.")
        return None
    except Exception as e:
        logging.error(f"[⚠️] Error inesperado durante la conversión con sox para {input_path}: {e}", exc_info=True)
        if output_path.exists():
            output_path.unlink() # Limpiar archivo parcial
        return None

# Aplicar reducción de ruido
def reduce_noise(y, sr):
    try:
        logging.info("Aplicando reducción de ruido.")
        # Convierte y a numpy, manteniendo los canales si es estéreo
        y_np = y.cpu().numpy()

        if y_np.ndim == 2 and y_np.shape[0] == 2: # Si es estéreo
            y_nr = nr.reduce_noise(y=y_np, sr=sr)
            logging.info("Reducción de ruido aplicada a audio estéreo.")
        elif y_np.ndim == 2 and y_np.shape[0] == 1: # Si es mono (1, muestras)
            y_nr = nr.reduce_noise(y=y_np.squeeze(0), sr=sr).reshape(1, -1) # Reduce y asegura (1, muestras)
            logging.info("Reducción de ruido aplicada a audio mono (1 canal).")
        else: # Fallback si el formato no es el esperado
            logging.warning(f"Formato de voces inesperado para denoising ({y_np.shape}). Saltando reducción de ruido.")
            y_nr = y_np # No aplicar denoise
        
        # Convertir de nuevo a tensor de PyTorch
        return torch.from_numpy(y_nr).to(y.device)
    except Exception as e:
        logging.error(f"[❌] Error en reducción de ruido: {e}", exc_info=True)
        return y # Devuelve el audio original si hay un error

# Función para normalizar el volumen
def normalize_volume(audio_tensor, target_peak_db=-1.0):
    """
    Normaliza el volumen de un tensor de audio por pico a un nivel deseado en dB.
    audio_tensor: tensor de PyTorch (canales, muestras) o (batch, canales, muestras)
    target_peak_db: Nivel de pico deseado en dBFS (ej. -1.0 para -1 dBFS).
    """
    try:
        logging.info(f"Aplicando normalización de volumen a pico de {target_peak_db} dB.")
        
        # Convertir target_peak_db a un factor lineal
        target_amplitude = 10**(target_peak_db / 20)

        # Encontrar el pico absoluto del audio
        # Si tiene dimensión de batch (3D), buscar el pico en todas las dimensiones excepto el batch
        # Si tiene 2D (canales, muestras), buscar el pico en todas las dimensiones
        current_peak = audio_tensor.abs().max()

        if current_peak == 0:
            logging.warning("El audio es silencioso, no se puede normalizar.")
            return audio_tensor

        # Calcular el factor de escalado necesario
        scale_factor = target_amplitude / current_peak
        
        # Aplicar el escalado
        normalized_audio = audio_tensor * scale_factor
        logging.info(f"Volumen normalizado. Factor de escalado aplicado: {scale_factor:.4f}.")
        return normalized_audio
    except Exception as e:
        logging.error(f"[❌] Error en la normalización de volumen: {e}", exc_info=True)
        return audio_tensor # Devuelve el audio original si hay un error

# Procesar archivo individual
def process_file(model, file_path, base_output_dir, apply_denoise, apply_normalize, save_stems, device):
    original_file_path = file_path # Guardar la ruta original para el log final
    temp_converted_path = None # Para limpiar archivos temporales de sox

    try:
        logging.info(f"[DEMUCS] Procesando: {original_file_path}")
        waveform, sr = None, None
        
        try:
            # Intentar cargar directamente con torchaudio
            waveform, sr = torchaudio.load(str(file_path))
            logging.info(f"Archivo cargado con éxito por torchaudio: {file_path}")
        except Exception as e:
            logging.warning(f"No se pudo cargar {file_path} directamente con torchaudio. Error: {e}. Intentando conversión con Sox...", exc_info=True)
            # Intentar conversión con sox
            temp_converted_path = convert_audio(file_path)
            if not temp_converted_path:
                logging.error(f"Omitiendo {original_file_path} debido a un fallo en la conversión.")
                return # Salir si la conversión no fue exitosa
            file_path = temp_converted_path # Usar el archivo convertido para el resto del procesamiento
            try:
                waveform, sr = torchaudio.load(str(file_path))
                logging.info(f"Archivo convertido cargado con éxito: {file_path}")
            except Exception as e:
                logging.error(f"[❌] No se pudo cargar el archivo (incluso después de la conversión con Sox): {file_path}\n{e}", exc_info=True)
                return # Salir si no se puede cargar ni el archivo convertido

        if waveform is None or sr is None:
            logging.error(f"[❌] No se pudo cargar la forma de onda o la tasa de muestreo para {original_file_path}.")
            return

        # Demucs espera (batch, channels, samples). Asegurar 3 dimensiones y 2 canales.
        if waveform.ndim == 1:
            waveform = waveform.unsqueeze(0)
            logging.info("Forma de onda mono 1D convertida a (1, muestras).")
        elif waveform.ndim > 2:
            logging.error(f"[❌] Tensor con más de 2 dimensiones: {original_file_path}. Se esperaban 1 o 2, se obtuvieron {waveform.ndim}")
            return
        
        if waveform.shape[0] == 1: # Si es mono (1 canal)
            waveform = waveform.repeat(2, 1) # Duplicar el canal para hacerlo estéreo (2, muestras)
            logging.info("Forma de onda mono convertida a estéreo (2 canales) duplicando el canal.")
        elif waveform.shape[0] > 2: # Si tiene más de 2 canales, convertir a estéreo promediando o tomando los primeros
            logging.warning(f"Archivo con {waveform.shape[0]} canales. Remuestreando a estéreo (2 canales).")
            if waveform.shape[0] >= 2:
                waveform = waveform[:2, :] # Tomar los dos primeros canales
            else: 
                waveform = waveform.mean(dim=0, keepdim=True).repeat(2, 1) # Promediar a mono y luego duplicar
            logging.info(f"Forma de onda remuestreada a 2 canales.")

        if waveform.ndim == 2:
            waveform = waveform.unsqueeze(0)
            logging.info("Forma de onda ajustada a 3 dimensiones (batch, channels, samples).")

        waveform = waveform.to(device)
        logging.info(f"Forma de onda movida a dispositivo: {device}.")

        # Aplicar el modelo Demucs
        try:
            logging.info(f"Aplicando el modelo Demucs a {original_file_path}...") 
            stems = apply_model(model, waveform, device=device) 
            logging.info(f"Modelo Demucs aplicado con éxito a {original_file_path}.")
        except Exception as e:
            logging.error(f"[❌] Error al aplicar el modelo Demucs a {original_file_path}: {e}", exc_info=True)
            return

        if stems.shape[0] < 1:
             logging.error(f"[❌] El modelo Demucs no devolvió ningún stem para {original_file_path}.")
             return
        
        stem_names = ['vocals', 'drums', 'bass', 'other'] 
        
        # --- Lógica de directorios de salida ---
        current_output_dir = base_output_dir
        if save_stems:
            # Si se guardan stems, creamos una subcarpeta para el archivo original
            current_output_dir = base_output_dir / original_file_path.stem
            current_output_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Directorio de salida para stems de '{original_file_path.name}': {current_output_dir}")
        else:
            # Si no se guardan stems, solo necesitamos el directorio base para la voz principal
            base_output_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Directorio de salida para voces procesadas: {base_output_dir}")

        # Procesar y guardar stems
        for i, stem_tensor in enumerate(stems[0]): # Iterar sobre los stems del primer (y único) batch
            stem_name = stem_names[i] if i < len(stem_names) else f"stem_{i}"
            
            logging.info(f"Procesando stem: {stem_name}")

            processed_stem_audio = stem_tensor # Empezamos con el stem original

            # Aplicar reducción de ruido si está activada
            if apply_denoise:
                logging.info(f"Aplicando reducción de ruido al stem: {stem_name}.")
                processed_stem_audio = reduce_noise(processed_stem_audio, sr)

            # Aplicar normalización si está activada
            if apply_normalize:
                logging.info(f"Aplicando normalización de volumen al stem: {stem_name}.")
                processed_stem_audio = normalize_volume(processed_stem_audio)
            
            # Determinar la ruta de guardado
            if stem_name == 'vocals':
                # La pista vocal procesada siempre tiene el sufijo _vocalclarity.wav
                output_file_name = original_file_path.stem + "_vocalclarity.wav"
                output_path = base_output_dir / output_file_name # Siempre va al directorio base
            elif save_stems:
                # Los otros stems procesados van a la subcarpeta específica del archivo
                output_file_name = f"{original_file_path.stem}_{stem_name}.wav"
                output_path = current_output_dir / output_file_name
            else:
                # Si no se guardan stems y no es la vocal, simplemente no se guarda
                logging.info(f"Omitiendo guardar stem '{stem_name}' ya que --save-stems no está activado y no es la pista vocal principal.")
                continue # Saltar al siguiente stem

            # Guardar el archivo de audio procesado (o el stem si --save-stems está activo)
            torchaudio.save(str(output_path), processed_stem_audio.cpu(), sr, encoding="PCM_S", bits_per_sample=16)
            logging.info(f"[✅] Archivo guardado: {output_path}")

    except Exception as e:
        logging.critical(f"[❌] Error CRÍTICO inesperado al procesar {original_file_path}: {e}", exc_info=True)
    finally:
        # Limpiar el archivo temporal de sox si fue creado
        if temp_converted_path and temp_converted_path.exists():
            try:
                temp_converted_path.unlink()
                logging.info(f"Archivo temporal eliminado: {temp_converted_path}")
            except Exception as e:
                logging.warning(f"No se pudo eliminar el archivo temporal {temp_converted_path}: {e}")

# Bloque principal de ejecución
if __name__ == "__main__":
    # --- Verificaciones de Compatibilidad ---
    python_major, python_minor = sys.version_info.major, sys.version_info.minor
    if not (python_major == 3 and python_minor in [10, 11]):
        warnings.warn(f"Estás usando Python {python_major}.{python_minor}. "
                      f"Se recomienda Python 3.10 o 3.11 para una mejor compatibilidad con Demucs y PyTorch.")
        logging.warning(f"Estás usando Python {python_major}.{python_minor}. "
                        f"Se recomienda Python 3.10 o 3.11 para una mejor compatibilidad con Demucs y PyTorch.")

    # Verificar si sox está instalado al inicio
    if not check_sox_installed():
        sys.exit(1)

    # --- Configuración del dispositivo (Siempre CPU para tu caso) ---
    device = "cpu"
    logging.info("Demucs se ejecutará en CPU (configuración para equipos de bajos recursos). Esto puede ser más lento.")
    
    parser = argparse.ArgumentParser(description="Herramienta de procesamiento de audio con separación de voces y reducción de ruido.")
    parser.add_argument("--path", required=True, help="Ruta del archivo o carpeta de entrada. Se procesarán todos los archivos de audio detectados.")
    parser.add_argument("--denoise", action="store_true", help="Aplicar reducción de ruido a las voces separadas.")
    parser.add_argument("--normalize", action="store_true", help="Normalizar el volumen de las voces separadas a un pico de -1 dBFS.")
    parser.add_argument("--save-stems", action="store_true", help="Guardar todos los stems (voces, batería, bajo, otros) separados por Demucs en una subcarpeta.")
    args = parser.parse_args()

    files = []
    audio_exts = [".wav", ".mp3", ".flac", ".aac", ".m4a", ".ogg"]

    path = Path(args.path)
    if not path.exists():
        logging.error(f"❌ La ruta proporcionada no existe: {args.path}")
        sys.exit(1)

    if path.is_file():
        if path.suffix.lower() in audio_exts:
            files.append(path)
            logging.info(f"Archivo único detectado: {path}")
        else:
            logging.error(f"❌ El archivo proporcionado '{path}' no es un formato de audio compatible. Extensiones soportadas: {', '.join(audio_exts)}")
            sys.exit(1)
    elif path.is_dir():
        logging.info(f"Directorio detectado: {path}. Escaneando archivos de audio...")
        for ext in audio_exts:
            files.extend(path.rglob(f"*{ext}"))
        if not files:
            logging.warning(f"No se encontraron archivos de audio compatibles en el directorio: {path} o sus subdirectorios.")
            sys.exit(0)
        logging.info(f"Se encontraron {len(files)} archivos de audio en el directorio.")
    else:
        logging.error(f"❌ La ruta proporcionada no es un archivo ni un directorio válido: {args.path}")
        sys.exit(1)

    logging.info(f"[🔍] Archivos detectados para procesar: {len(files)}")
    try:
        logging.info(f"Cargando el modelo Demucs 'htdemucs' en el dispositivo: {device}...")
        model = get_model(name="htdemucs")
        model.to(device)
        logging.info("Modelo Demucs cargado con éxito.")
    except Exception as e:
        logging.critical(f"Fallo CRÍTICO al cargar el modelo Demucs: {e}", exc_info=True)
        logging.critical("Esto puede ser debido a una instalación corrupta, problemas de red durante la descarga del modelo, o incompatibilidad de versiones (especialmente Python 3.12+).")
        logging.critical("Intenta 'rm -rf ~/.cache/demucs' y/o verifica la versión de Python/PyTorch en tu entorno virtual.")
        sys.exit(1)

    base_out_dir = "processed_audio_clarity"
    os.makedirs(base_out_dir, exist_ok=True)
    logging.info(f"Directorio de salida base establecido en: {base_out_dir}")

    # Desactivar el logging a la consola mientras tqdm está activo
    for handler in logging.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.CRITICAL)

    for f in tqdm(files, desc="🎵 Procesando audio", unit=" archivo"):
        process_file(model, f, Path(base_out_dir), args.denoise, args.normalize, args.save_stems, device)
    
    # Volver a habilitar el logging a la consola al finalizar
    for handler in logging.root.handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.setLevel(logging.INFO)

    logging.info("🏁 Procesamiento finalizado.")
    print("\n🏁 Procesamiento finalizado. Revisa el archivo 'logs/audio_processing.log' para más detalles.")