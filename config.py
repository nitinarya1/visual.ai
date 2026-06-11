import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# Directories
UPLOADS_DIR = os.path.join(BASE_DIR, 'uploads')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
TEMP_DIR = os.path.join(BASE_DIR, 'temp')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
BIN_DIR = os.path.join(BASE_DIR, 'bin')

# Ensure directories exist
for directory in [UPLOADS_DIR, OUTPUT_DIR, TEMP_DIR, MODELS_DIR, BIN_DIR]:
    os.makedirs(directory, exist_ok=True)

# Piper Settings
PIPER_BIN_PATH = os.path.join(BIN_DIR, 'piper', 'piper.exe')
DEFAULT_PIPER_MODEL = "hi_IN-rohan-medium"

# Kokoro Settings
DEFAULT_KOKORO_MODEL = "kokoro-v0_19.onnx"
DEFAULT_KOKORO_VOICES = "voices.bin"

# Chunking Settings
DEFAULT_MAX_CHUNK_CHARS = 800  # Split chunks around this character count

# Audio synthesis defaults
DEFAULT_SPEED = 1.0
DEFAULT_VOLUME = 1.0
DEFAULT_SILENCE_MS = 500  # Silence (ms) between chunks
