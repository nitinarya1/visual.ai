import os
import subprocess
import shutil

class TTSGenerationError(Exception):
    """Custom exception class for TTS generation failures."""
    pass

class PiperGenerator:
    """
    Wrapper for the Piper TTS engine.
    Invokes the standalone precompiled 'piper.exe' CLI binary.
    """
    def __init__(self, piper_bin_path, models_dir):
        self.piper_bin_path = os.path.abspath(piper_bin_path)
        self.models_dir = os.path.abspath(models_dir)

    def is_available(self, model_name=None):
        """Checks if the Piper binary and optionally a specific model exist."""
        bin_exists = os.path.exists(self.piper_bin_path) or shutil.which("piper") is not None
        if not bin_exists:
            return False
            
        if model_name:
            model_path = os.path.join(self.models_dir, f"{model_name}.onnx")
            model_json = os.path.join(self.models_dir, f"{model_name}.onnx.json")
            return os.path.exists(model_path) and os.path.exists(model_json)
            
        return True

    def generate(self, text, output_path, model_name, speed=1.0):
        """
        Synthesizes text into a WAV file using Piper CLI.
        Maps 'speed' (e.g. 1.2x) to length_scale (length_scale = 1.0 / speed).
        """
        # 1. Verify model files exist
        model_path = os.path.join(self.models_dir, f"{model_name}.onnx")
        model_json = os.path.join(self.models_dir, f"{model_name}.onnx.json")
        
        if not os.path.exists(model_path) or not os.path.exists(model_json):
            raise TTSGenerationError(
                f"Piper model or config not found in '{self.models_dir}'.\n"
                f"Missing: '{model_name}.onnx' and/or '{model_name}.onnx.json'.\n"
                f"Please download them and place them in the models folder."
            )

        # 2. Determine binary path
        cmd_path = self.piper_bin_path
        if not os.path.exists(cmd_path):
            if shutil.which("piper") is not None:
                cmd_path = "piper"
            else:
                raise TTSGenerationError(
                    f"Piper executable not found at '{self.piper_bin_path}' and is not in the system PATH.\n"
                    f"Please download the precompiled piper binary for Windows, unzip it, and place it at "
                    f"'{self.piper_bin_path}'."
                )

        # 3. Calculate length scale (inverse of speed)
        # 1.0 -> length_scale 1.0 (default)
        # 1.5 -> length_scale 0.67 (faster)
        # 0.75 -> length_scale 1.33 (slower)
        length_scale = 1.0 / float(speed) if speed > 0 else 1.0

        cmd = [
            cmd_path,
            "--model", model_path,
            "--output_file", os.path.abspath(output_path),
            "--length_scale", f"{length_scale:.2f}"
        ]

        try:
            # Run Piper CLI in a subprocess. Text is fed through standard input.
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8'
            )
            stdout, stderr = process.communicate(input=text)
            
            if process.returncode != 0:
                raise TTSGenerationError(
                    f"Piper process failed with exit code {process.returncode}.\n"
                    f"Stderr: {stderr.strip()}"
                )
                
            if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
                raise TTSGenerationError(f"Piper failed to produce a valid WAV output at: {output_path}")
                
        except Exception as e:
            if not isinstance(e, TTSGenerationError):
                raise TTSGenerationError(f"Subprocess launch error: {str(e)}")
            raise e


# Caching Kokoro instance to avoid ONNX load overhead on consecutive chunks
_KOKORO_CACHE = {}

def _patch_kokoro_languages():
    try:
        import kokoro_onnx
        if hasattr(kokoro_onnx, 'SUPPORTED_LANGUAGES'):
            supported = kokoro_onnx.SUPPORTED_LANGUAGES
            for lang in ['hi', 'es', 'it', 'pt-br']:
                if lang not in supported:
                    if isinstance(supported, list):
                        supported.append(lang)
                    else:
                        kokoro_onnx.SUPPORTED_LANGUAGES = list(supported) + [lang]
    except ImportError:
        pass

# Apply the patch on load
_patch_kokoro_languages()

class KokoroGenerator:
    """
    Wrapper for Kokoro TTS using the kokoro-onnx library.
    Performs speech synthesis directly in Python using ONNX Runtime CPU.
    """
    def __init__(self, models_dir):
        self.models_dir = os.path.abspath(models_dir)

    def is_available(self, model_name="kokoro-v0_19.onnx", voice_name="voices.bin"):
        """Checks if kokoro-onnx is installed and model files are present."""
        try:
            import kokoro_onnx
            model_path = os.path.join(self.models_dir, model_name)
            voices_path = os.path.join(self.models_dir, voice_name)
            return os.path.exists(model_path) and os.path.exists(voices_path)
        except ImportError:
            return False

    def generate(self, text, output_path, voice_name="af_bella", speed=1.0):
        """
        Synthesizes text into a WAV file using Kokoro ONNX Runtime.
        """
        try:
            import kokoro_onnx
            import soundfile as sf
        except ImportError:
            raise TTSGenerationError(
                "Kokoro python packages are not installed.\n"
                "Please run 'pip install kokoro-onnx soundfile' to enable the Kokoro engine."
            )

        model_path = os.path.join(self.models_dir, "kokoro-v0_19.onnx")
        voices_path = os.path.join(self.models_dir, "voices.bin")

        if not os.path.exists(model_path) or not os.path.exists(voices_path):
            raise TTSGenerationError(
                f"Kokoro model assets not found in '{self.models_dir}'.\n"
                f"Missing: 'kokoro-v0_19.onnx' and/or 'voices.bin'.\n"
                f"Please download them and place them in the models folder."
            )

        # Retrieve model from cache or initialize (takes ~1-2s on CPU)
        cache_key = (model_path, voices_path)
        if cache_key not in _KOKORO_CACHE:
            try:
                # Disable GPU providers, force CPU provider
                kokoro = kokoro_onnx.Kokoro(model_path, voices_path)
                _KOKORO_CACHE[cache_key] = kokoro
            except Exception as e:
                raise TTSGenerationError(f"Failed to load Kokoro ONNX model: {str(e)}")
        else:
            kokoro = _KOKORO_CACHE[cache_key]

        # Determine target language code based on voice name prefix
        lang = "en-us"
        if voice_name:
            prefix = voice_name.lower()[0]
            if prefix == 'h':
                lang = 'hi'
            elif prefix == 'e':
                lang = 'es'
            elif prefix == 'i':
                lang = 'it'
            elif prefix == 'p':
                lang = 'pt-br'
            elif prefix == 'j':
                lang = 'ja'
            elif prefix == 'z':
                lang = 'cmn'
            elif prefix == 'f':
                lang = 'fr-fr'
            elif prefix == 'b':
                lang = 'en-gb'

        try:
            # Kokoro supports direct floating point speed scale natively
            samples, sample_rate = kokoro.create(
                text, 
                voice=voice_name, 
                speed=float(speed),
                lang=lang
            )
            
            # Save audio samples as WAV
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            sf.write(output_path, samples, sample_rate)
            
        except Exception as e:
            raise TTSGenerationError(f"Kokoro generation failed: {str(e)}")

