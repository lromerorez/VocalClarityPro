# **🎤✨ VocalClarityPro: Tu Herramienta Definitiva para la Claridad Vocal en Audio ✨🎤**

VocalClarityPro es un script de Python diseñado para procesar archivos de audio, permitiéndote separar pistas vocales, aplicar reducción de ruido y normalizar el volumen para una claridad impecable. Ideal para mejorar grabaciones, pistas de voz o preparar audio para mezclas.

## **🚀 Características Principales**

* **🎙️ Separación de Voz Precisa:** Utiliza el potente modelo Demucs (htdemucs) para aislar la pista vocal de otros instrumentos (batería, bajo, otros).  
* **🔇 Reducción de Ruido Inteligente:** Aplica algoritmos avanzados para limpiar el audio de ruidos de fondo no deseados.  
* **🔊 Normalización de Volumen:** Ajusta automáticamente el volumen de la(s) pista(s) procesada(s) para asegurar que el audio sea audible y esté a un nivel óptimo, evitando picos.  
* **📂 Gestión de Archivos Flexible:** Guarda solo la pista vocal procesada o todos los "stems" separados (voces, batería, bajo, otros) en una estructura de carpetas organizada.  
* **🎵 Barra de Progreso Interactiva:** Monitoriza el avance del procesamiento de tus archivos con una elegante barra de progreso en la terminal.  
* **⚙️ Compatibilidad Amplia:** Soporta múltiples formatos de audio de entrada (.wav, .mp3, .flac, .aac, .m4a, .ogg).

## **💻 Instalación**

Sigue estos pasos para configurar tu entorno y tener VocalClarityPro listo para funcionar.

### **1\. 🐍 Verificar la Versión de Python**

Es **altamente recomendado** usar **Python 3.10 o Python 3.11**. Versiones más recientes (como 3.12+) pueden tener problemas de compatibilidad con algunas dependencias de PyTorch/Demucs.

Para verificar tu versión de Python, abre una terminal y escribe:

python \--version

### **2\. 🧰 Instalar Sox (Indispensable)**

Sox es una herramienta de procesamiento de audio en línea de comandos que tu script utiliza para convertir formatos de audio si torchaudio no puede cargarlos directamente.

* **En sistemas basados en Debian/Ubuntu:**  
  sudo apt update  
  sudo apt install sox libsox-fmt-all

* **En sistemas basados en Arch Linux:**  
  sudo pacman \-S sox

* **En macOS (usando Homebrew):**  
  brew install sox

* En Windows:  
  Descarga el instalador desde la página oficial de Sox: https://sourceforge.net/projects/sox/files/. Asegúrate de añadir Sox a la variable de entorno PATH durante la instalación o manualmente.

Para verificar que Sox está instalado correctamente, abre una terminal y escribe:

sox \--version

### **3\. 📦 Crear y Activar un Entorno Virtual de Python**

Es una buena práctica crear un entorno virtual para cada proyecto de Python. Esto aísla las dependencias y evita conflictos.

1. **Navega a la carpeta de tu proyecto** (donde tienes VocalClarityPro.py):  
   cd /ruta/a/tu/carpeta/VocalClarityPro

2. **Crea el entorno virtual:**  
   python3.11 \-m venv .venv   
   \# O usa 'python3.10 \-m venv .venv' si esa es tu versión específica

   Esto creará una carpeta oculta llamada .venv dentro de tu directorio de proyecto.  
3. **Activa el entorno virtual:**  
   * **En Linux/macOS:**  
     source .venv/bin/activate

   * **En Windows (Command Prompt):**  
     .venv\\Scripts\\activate.bat

   * **En Windows (PowerShell):**  
     .venv\\Scripts\\Activate.ps1

Verás (.venv) o un prefijo similar en tu línea de comandos, indicando que el entorno está activo.

### **4\. ⬇️ Instalar las Dependencias de Python**

Con el entorno virtual activado, instala todas las librerías necesarias.

pip install torch torchaudio noisereduce demucs tqdm

**🚨 ¡Atención\!** La instalación de torch y torchaudio puede tardar un poco y requerir una buena conexión a internet debido a su tamaño. Demucs también descargará modelos preentrenados (aproximadamente 130MB) la primera vez que se ejecute el script.

## **🚀 Uso**

Asegúrate de estar en el directorio donde tienes VocalClarityPro.py y con tu entorno virtual activado.

### **📜 Sintaxis Básica**

python VocalClarityPro.py \--path \<ruta\_a\_audio\_o\_carpeta\> \[--denoise\] \[--normalize\] \[--save-stems\]

### **🎯 Opciones Disponibles**

* \--path \<ruta\_a\_audio\_o\_carpeta\>: **(Obligatorio)** Ruta a un archivo de audio único o a una carpeta que contenga archivos de audio. Si es una carpeta, procesará todos los archivos compatibles recursivamente.  
* \--denoise: **(Opcional)** Aplica reducción de ruido a las pistas separadas.  
* \--normalize: **(Opcional)** Normaliza el volumen de las pistas procesadas a un pico de \-1 dBFS. Ideal para "alzar" voces casi imperceptibles.  
* \--save-stems: **(Opcional)** Guarda todos los stems (voces, batería, bajo, otros) separados por Demucs.

### **📝 Ejemplos de Uso**

#### **1\. 🎤 Solo Claridad Vocal (Separación \+ Ruido \+ Normalización)**

Este es el uso más común para obtener una pista vocal limpia y con volumen ajustado. El resultado \_vocalclarity.wav se guardará directamente en la carpeta processed\_audio\_clarity/.

python VocalClarityPro.py \--path "/home/lr/Música/grabaciones/entrevista.wav" \--denoise \--normalize

#### **2\. 🎶 Claridad Vocal Y Todos los Stems Procesados**

Esto generará la pista \_vocalclarity.wav en la carpeta principal processed\_audio\_clarity/. Adicionalmente, creará una subcarpeta con el nombre del archivo original (ej. processed\_audio\_clarity/entrevista/) donde se guardarán todos los stems separados (vocals.wav, drums.wav, bass.wav, other.wav). **Todos estos stems pasarán por los procesos de reducción de ruido y normalización si se especifican.**

python VocalClarityPro.py \--path "/home/lr/Música/grabaciones/podcast.mp3" \--denoise \--normalize \--save-stems

#### **3\. 🔊 Solo Separación de Voz (sin reducción de ruido ni normalización)**

Útil si solo quieres las voces separadas, sin ningún procesamiento adicional. El resultado \_vocalclarity.wav se guardará directamente en processed\_audio\_clarity/.

python VocalClarityPro.py \--path "/home/lr/Música/audios/demostracion.flac"

#### **4\. 🎚️ Combinaciones de Opciones Individuales**

Puedes combinar las opciones \--denoise y \--normalize según tus necesidades.

* **Solo separación y reducción de ruido:**  
  python VocalClarityPro.py \--path "/home/lr/Audios/cancion\_ruido.m4a" \--denoise

* **Solo separación y normalización de volumen:**  
  python VocalClarityPro.py \--path "/home/lr/Mensajes/voz\_baja.ogg" \--normalize

## **📂 Estructura de Salida**

El script creará una carpeta processed\_audio\_clarity/ en el mismo directorio donde se ejecuta el script.

* **Sin \--save-stems:**  
  processed\_audio\_clarity/  
  └── nombre\_del\_archivo\_original\_vocalclarity.wav

* **Con \--save-stems:**  
  processed\_audio\_clarity/  
  ├── nombre\_del\_archivo\_original\_vocalclarity.wav  (La pista vocal procesada)  
  └── nombre\_del\_archivo\_original/                 (Carpeta con todos los stems procesados)  
      ├── nombre\_del\_archivo\_original\_vocals.wav  
      ├── nombre\_del\_archivo\_original\_drums.wav  
      ├── nombre\_del\_archivo\_original\_bass.wav  
      └── nombre\_del\_archivo\_original\_other.wav

Además, se generará un archivo de log detallado en logs/audio\_processing.log para que puedas revisar el proceso paso a paso.

## **⁉️ Solución de Problemas Comunes**

* **Fallo CRÍTICO al cargar el modelo Demucs:**: Esto suele ocurrir por problemas de red durante la descarga del modelo la primera vez, una instalación corrupta de Demucs/PyTorch, o incompatibilidad de versiones de Python (especialmente Python 3.12+ con versiones antiguas de Demucs/PyTorch).  
  * **Solución:** Intenta eliminar el caché de Demucs (rm \-rf \~/.cache/demucs en Linux/macOS o del %USERPROFILE%\\.cache\\demucs en Windows) y ejecuta el script de nuevo para forzar la redescarga del modelo. Asegúrate de estar usando Python 3.10 o 3.11.  
* **Sox no está instalado o no está en el PATH del sistema.**: Asegúrate de haber seguido las instrucciones de instalación de Sox para tu sistema operativo y que esté accesible desde tu terminal.

## **🤝 Contribución**

¡Las contribuciones son bienvenidas\! Si tienes ideas para mejorar VocalClarityPro, encuentra un bug o quieres añadir nuevas funcionalidades, por favor, abre un "Issue" o envía un "Pull Request".

## **📄 Licencia**

Este proyecto está bajo la Licencia MIT. Consulta el archivo LICENSE para más detalles.

## **🙏 Agradecimientos**

* **Demucs:** Por su increíble modelo de separación de fuentes musicales.  
* **Noisereduce:** Por la eficaz implementación de algoritmos de reducción de ruido.  
* **tqdm:** Por la elegante barra de progreso.  
* **Torchaudio & PyTorch:** Por la base de procesamiento de audio en Python.