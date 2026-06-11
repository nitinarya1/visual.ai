import os
import time
import uuid
import shutil
import threading
import traceback
from flask import Flask, render_template, request, jsonify, send_from_directory
import psutil

import config
from tts.chunker import split_into_chunks
from tts.generator import PiperGenerator, KokoroGenerator, TTSGenerationError
from tts.merger import merge_wavs_to_mp3
from tts.video_generator import generate_video_pipeline

app = Flask(__name__)

# Task tracking database (in-memory)
TASKS = {}
TASKS_LOCK = threading.Lock()

def cleanup_old_files():
    """
    Cleans up temp and output files older than 1 hour to prevent disk bloat.
    """
    now = time.time()
    one_hour_ago = now - 3600
    
    # Cleanup temp directory
    for f in os.listdir(config.TEMP_DIR):
        file_path = os.path.join(config.TEMP_DIR, f)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < one_hour_ago:
                os.remove(file_path)
        except Exception as e:
            app.logger.warning(f"Error cleaning temp file {file_path}: {e}")
            
    # Cleanup output directory
    for f in os.listdir(config.OUTPUT_DIR):
        file_path = os.path.join(config.OUTPUT_DIR, f)
        try:
            if os.path.isfile(file_path) and os.path.getmtime(file_path) < one_hour_ago:
                os.remove(file_path)
        except Exception as e:
            app.logger.warning(f"Error cleaning output file {file_path}: {e}")

def process_tts_task(task_id, text, engine, voice, speed, volume, silence_ms):
    """
    Background worker thread to execute text chunking, speech synthesis, 
    audio merging, and MP3 encoding.
    """
    temp_wavs = []
    try:
        # 1. Text Chunking
        with TASKS_LOCK:
            TASKS[task_id].update({
                'progress': 5,
                'message': 'Analyzing and chunking text...'
            })
            
        chunks = split_into_chunks(text, max_chars=config.DEFAULT_MAX_CHUNK_CHARS)
        total_chunks = len(chunks)
        
        if total_chunks == 0:
            raise ValueError("Input text is empty or contains no pronounceable characters.")
            
        with TASKS_LOCK:
            TASKS[task_id].update({
                'progress': 10,
                'total_chunks': total_chunks,
                'message': f"Split text into {total_chunks} chunk(s). Initializing engine..."
            })

        # 2. Engine Selection and Availability Check
        if engine == 'piper':
            generator = PiperGenerator(config.PIPER_BIN_PATH, config.MODELS_DIR)
            if not generator.is_available():
                raise TTSGenerationError(
                    "Piper engine is not ready. Please download the 'piper.exe' binary and place it in the "
                    "bin/piper/ directory, or ensure it is available in the system PATH."
                )
            voice_or_model = voice
        elif engine == 'kokoro':
            generator = KokoroGenerator(config.MODELS_DIR)
            if not generator.is_available():
                raise TTSGenerationError(
                    "Kokoro engine is not ready. Please install dependencies ('pip install kokoro-onnx soundfile') "
                    "and ensure 'kokoro-v0_19.onnx' and 'voices.bin' are in the models/ folder."
                )
            voice_or_model = voice
        else:
            raise ValueError(f"Unsupported TTS engine: {engine}")

        # 3. Process each chunk
        for idx, chunk_text in enumerate(chunks):
            # Check for cancellation
            with TASKS_LOCK:
                if TASKS[task_id]['status'] == 'cancelled':
                    raise TTSGenerationError("Generation was cancelled by the user.")
                
                # Update progress
                # Chunks cover progress range [10%, 80%]
                chunk_progress = 10 + int((idx / total_chunks) * 70)
                TASKS[task_id].update({
                    'progress': chunk_progress,
                    'current_chunk': idx + 1,
                    'message': f"Generating speech for chunk {idx + 1} of {total_chunks}..."
                })

            # Output path for intermediate WAV
            temp_wav_path = os.path.join(config.TEMP_DIR, f"{task_id}_chunk_{idx:03d}.wav")
            temp_wavs.append(temp_wav_path)
            
            # Generate chunk
            generator.generate(chunk_text, temp_wav_path, voice_or_model, speed=speed)

        # 4. Merge Chunks and Encode to MP3
        with TASKS_LOCK:
            if TASKS[task_id]['status'] == 'cancelled':
                raise TTSGenerationError("Generation was cancelled by the user.")
            TASKS[task_id].update({
                'progress': 85,
                'message': 'Merging chunks and encoding to MP3...'
            })

        output_mp3_filename = f"{task_id}.mp3"
        output_mp3_path = os.path.join(config.OUTPUT_DIR, output_mp3_filename)
        
        merge_wavs_to_mp3(temp_wavs, output_mp3_path, silence_duration_ms=silence_ms, volume_factor=volume)
        
        # 5. Completed
        with TASKS_LOCK:
            TASKS[task_id].update({
                'status': 'completed',
                'progress': 100,
                'message': 'Audio generated successfully!',
                'mp3_filename': output_mp3_filename,
                'end_time': time.time()
            })
            
    except Exception as e:
        # Set error state
        tb = traceback.format_exc()
        app.logger.error(f"Error in task {task_id}: {str(e)}\nTraceback: {tb}")
        
        # Clean up temp WAV files on error
        for path in temp_wavs:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
                    
        with TASKS_LOCK:
            if TASKS[task_id]['status'] != 'cancelled':
                TASKS[task_id].update({
                    'status': 'error',
                    'message': f"Error: {str(e)}",
                    'error': str(e)
                })

# Routes
@app.route('/')
def index():
    """Serves the main application page."""
    # Perform cleanup of old files in the background on visit
    threading.Thread(target=cleanup_old_files).start()
    return render_template('index.html')

@app.route('/api/system-status', methods=['GET'])
def system_status():
    """Returns dynamic system parameters and status of TTS engines/models."""
    # Memory metrics
    virtual_mem = psutil.virtual_memory()
    ram_used_gb = virtual_mem.used / (1024**3)
    ram_total_gb = virtual_mem.total / (1024**3)
    ram_percent = virtual_mem.percent
    
    # Disk metrics
    disk = psutil.disk_usage(config.OUTPUT_DIR)
    disk_free_gb = disk.free / (1024**3)
    disk_total_gb = disk.total / (1024**3)

    # Scan downloaded Piper models
    piper_models = []
    if os.path.exists(config.MODELS_DIR):
        for file in os.listdir(config.MODELS_DIR):
            if file.endswith('.onnx') and not file.startswith('kokoro'):
                # Strip extension to get voice name
                piper_models.append(file.replace('.onnx', ''))

    # Check Piper binary availability
    piper_gen = PiperGenerator(config.PIPER_BIN_PATH, config.MODELS_DIR)
    piper_available = piper_gen.is_available()

    # Check Kokoro ONNX model files availability
    kokoro_gen = KokoroGenerator(config.MODELS_DIR)
    kokoro_available = kokoro_gen.is_available()

    return jsonify({
        'ram_used': f"{ram_used_gb:.2f} GB",
        'ram_total': f"{ram_total_gb:.2f} GB",
        'ram_percent': ram_percent,
        'disk_free': f"{disk_free_gb:.2f} GB",
        'disk_total': f"{disk_total_gb:.2f} GB",
        'piper_available': piper_available,
        'piper_models': piper_models,
        'kokoro_available': kokoro_available
    })

@app.route('/api/generate', methods=['POST'])
def generate_audio():
    """Endpoint to trigger text-to-speech background generation."""
    data = request.json or {}
    text = data.get('text', '').strip()
    engine = data.get('engine', 'piper').lower()
    voice = data.get('voice', '').strip()
    speed = float(data.get('speed', config.DEFAULT_SPEED))
    volume = float(data.get('volume', config.DEFAULT_VOLUME))
    silence_ms = int(data.get('silence_ms', config.DEFAULT_SILENCE_MS))

    # Basic validations
    if not text:
        return jsonify({'error': 'Input text is empty.'}), 400
        
    if engine == 'piper' and not voice:
        voice = config.DEFAULT_PIPER_MODEL
    elif engine == 'kokoro' and not voice:
        voice = 'af_bella'

    task_id = str(uuid.uuid4())
    
    with TASKS_LOCK:
        TASKS[task_id] = {
            'status': 'processing',
            'progress': 0,
            'current_chunk': 0,
            'total_chunks': 0,
            'message': 'Queuing task...',
            'mp3_filename': None,
            'error': None,
            'start_time': time.time(),
            'end_time': None
        }

    # Spawn processing thread
    thread = threading.Thread(
        target=process_tts_task, 
        args=(task_id, text, engine, voice, speed, volume, silence_ms)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/generate-video', methods=['POST'])
def generate_video():
    """Endpoint to trigger text-to-video background generation."""
    data = request.json or {}
    text = data.get('text', '').strip()
    engine = data.get('engine', 'piper').lower()
    voice = data.get('voice', '').strip()
    speed = float(data.get('speed', config.DEFAULT_SPEED))
    volume = float(data.get('volume', config.DEFAULT_VOLUME))
    silence_ms = int(data.get('silence_ms', config.DEFAULT_SILENCE_MS))
    resolution = data.get('resolution', 'portrait').lower()
    theme = data.get('theme', 'cyberpunk').lower()
    text_color = data.get('color', 'white').lower()
    ai_backgrounds = bool(data.get('ai_backgrounds', True))

    if not text:
        return jsonify({'error': 'Input text is empty.'}), 400
        
    if engine == 'piper' and not voice:
        voice = config.DEFAULT_PIPER_MODEL
    elif engine == 'kokoro' and not voice:
        voice = 'hm_omega'

    task_id = str(uuid.uuid4())
    
    with TASKS_LOCK:
        TASKS[task_id] = {
            'status': 'processing',
            'progress': 0,
            'current_chunk': 0,
            'total_chunks': 0,
            'message': 'Queuing video generation task...',
            'mp3_filename': None,
            'mp4_filename': None,
            'error': None,
            'start_time': time.time(),
            'end_time': None
        }

    def status_callback(progress, message, status='processing', mp4_filename=None, error=None):
        with TASKS_LOCK:
            if TASKS[task_id]['status'] != 'cancelled':
                TASKS[task_id].update({
                    'progress': progress,
                    'message': message,
                    'status': status
                })
                if mp4_filename:
                    TASKS[task_id]['mp4_filename'] = mp4_filename
                if error:
                    TASKS[task_id]['error'] = error
                if status in ['completed', 'error']:
                    TASKS[task_id]['end_time'] = time.time()

    # Spawn video generation thread
    thread = threading.Thread(
        target=generate_video_pipeline, 
        args=(task_id, text, engine, voice, speed, volume, silence_ms, resolution, theme, text_color, ai_backgrounds, status_callback)
    )
    thread.daemon = True
    thread.start()

    return jsonify({'task_id': task_id})

@app.route('/api/status/<task_id>', methods=['GET'])
def get_status(task_id):
    """Endpoint to retrieve synthesis task details."""
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        
    if not task:
        return jsonify({'error': 'Task not found.'}), 404
        
    # Calculate duration if completed
    duration = None
    if task['end_time']:
        duration = round(task['end_time'] - task['start_time'], 1)
    elif task['status'] == 'processing':
        duration = round(time.time() - task['start_time'], 1)

    return jsonify({
        'status': task['status'],
        'progress': task['progress'],
        'current_chunk': task['current_chunk'],
        'total_chunks': task['total_chunks'],
        'message': task['message'],
        'mp3_filename': task['mp3_filename'],
        'mp4_filename': task.get('mp4_filename'),
        'error': task['error'],
        'elapsed_time': duration
    })

@app.route('/api/cancel/<task_id>', methods=['POST'])
def cancel_task(task_id):
    """Endpoint to cancel an active synthesis task."""
    with TASKS_LOCK:
        task = TASKS.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found.'}), 404
            
        if task['status'] == 'processing':
            task['status'] = 'cancelled'
            task['message'] = 'Generation cancelled by user.'
            return jsonify({'message': 'Task cancellation requested.'})
            
    return jsonify({'message': 'Task is not in a cancellable state.'})

@app.route('/api/download/<filename>', methods=['GET'])
def download_file(filename):
    """Endpoint to stream or download the final generated file."""
    # Ensure filename is safe (prevents directory traversal)
    safe_filename = os.path.basename(filename)
    as_attachment = request.args.get('download', 'false').lower() == 'true'
    return send_from_directory(config.OUTPUT_DIR, safe_filename, as_attachment=as_attachment)

if __name__ == '__main__':
    # Flask local startup
    print(f"==================================================")
    print(f"Starting Offline Text-to-Speech server on localhost")
    print(f"Please open: http://127.0.0.1:5000 in your browser")
    print(f"==================================================")
    app.run(host='127.0.0.1', port=5000, debug=True)
