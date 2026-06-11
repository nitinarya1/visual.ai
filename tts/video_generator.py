import os
import re
import subprocess
import time
import shutil
import traceback
import wave
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

import config
from tts.chunker import split_into_chunks
from tts.generator import PiperGenerator, KokoroGenerator, TTSGenerationError
from tts.merger import scale_volume

# Color gradient themes mapping
THEMES = {
    'cyberpunk': {'color1': (11, 0, 26), 'color2': (76, 0, 128)},      # Deep purple to violet
    'midnight': {'color1': (15, 23, 42), 'color2': (30, 41, 59)},     # Dark slate
    'oceanic': {'color1': (13, 27, 42), 'color2': (27, 73, 101)},     # Navy to steel blue
    'forest': {'color1': (10, 28, 21), 'color2': (18, 76, 56)},       # Dark green to teal
    'crimson': {'color1': (28, 13, 13), 'color2': (101, 27, 27)},     # Deep charcoal to blood red
}

# Subtitle Colors
COLORS = {
    'white': (241, 245, 249),
    'yellow': (250, 204, 21),
    'cyan': (34, 211, 238),
    'green': (52, 211, 153),
}

def draw_gradient(width, height, color1, color2):
    """Generates a vertical linear gradient image."""
    base = Image.new('RGB', (width, height), color1)
    top = Image.new('RGB', (width, height), color2)
    mask = Image.new('L', (width, height))
    
    # Create mask mapping opacity linearly from top to bottom
    mask_data = []
    for y in range(height):
        # Extend row data
        mask_data.extend([int(255 * (y / height))] * width)
    mask.putdata(mask_data)
    
    return Image.composite(top, base, mask)

def wrap_text(text, font, max_width):
    """Wraps text into lines that fit within max_width."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = " ".join(current_line + [word])
        # Calculate bounding box width of test line
        bbox = font.getbbox(test_line)
        w = bbox[2] - bbox[0]
        if w <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(" ".join(current_line))
            current_line = [word]
            
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines

def create_slide_image(text, theme_name, text_color_name, resolution, output_path):
    """
    Renders a captioned image frame representing a single video scene.
    """
    # Resolution parsing (e.g. 1080x1920 or 1920x1080)
    width, height = resolution
    
    # Load Theme and Colors
    theme = THEMES.get(theme_name, THEMES['cyberpunk'])
    text_color = COLORS.get(text_color_name, COLORS['white'])
    
    # Generate background gradient
    img = draw_gradient(width, height, theme['color1'], theme['color2'])
    draw = ImageDraw.Draw(img)
    
    # Load Windows standard font path
    font_paths = [
        "C:/Windows/Fonts/segoeuib.ttf",  # Segoe UI Bold
        "C:/Windows/Fonts/arialbd.ttf",   # Arial Bold
        "C:/Windows/Fonts/SegoeUI.ttf",   # Segoe UI Standard
        "C:/Windows/Fonts/arial.ttf"       # Arial Standard
    ]
    
    font = None
    # Dynamic font sizing based on target resolution height
    font_size = int(height * 0.04) # e.g. ~76px for 1920 height
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, font_size)
                break
            except:
                pass
                
    if font is None:
        font = ImageFont.load_default()
        
    # Text layout limits (80% of width)
    max_text_width = int(width * 0.8)
    wrapped_lines = wrap_text(text, font, max_text_width)
    
    # Calculate spacing parameters
    line_spacing = int(font_size * 0.3)
    total_height = 0
    line_heights = []
    
    for line in wrapped_lines:
        bbox = font.getbbox(line)
        h = bbox[3] - bbox[1]
        line_heights.append(h)
        total_height += h + line_spacing
        
    if line_heights:
        total_height -= line_spacing # remove trailing spacing

    # Render lines vertically centered
    y_start = (height - total_height) // 2
    
    for idx, line in enumerate(wrapped_lines):
        bbox = font.getbbox(line)
        w = bbox[2] - bbox[0]
        h = line_heights[idx]
        x = (width - w) // 2
        
        # Draw text drop-shadow for high legibility
        draw.text((x + 3, y_start + 3), line, font=font, fill=(0, 0, 0, 180))
        # Draw main subtitle text
        draw.text((x, y_start), line, font=font, fill=text_color)
        
        y_start += h + line_spacing
        
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    img.save(output_path, "PNG")

def get_audio_duration(wav_path):
    """Utility to query duration (seconds) of a WAV file."""
    with wave.open(wav_path, 'rb') as wav:
        frames = wav.getnframes()
        rate = wav.getframerate()
        return float(frames) / rate

def render_scene_clip(image_path, audio_path, duration, output_mp4_path):
    """
    Spawns FFmpeg to loop a single captioned image over the WAV duration.
    Optimized for high-speed CPU stitching.
    """
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    
    # FFmpeg command inputs:
    # -loop 1: loop the image
    # -t duration: enforce video length
    # -tune stillimage: optimized macroblocks for stationary imagery
    # -preset ultrafast: minimize encoding CPU overhead for high speed
    cmd = [
        ffmpeg_bin,
        '-y',
        '-loop', '1',
        '-i', os.path.abspath(image_path),
        '-i', os.path.abspath(audio_path),
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'stillimage',
        '-c:a', 'aac',
        '-b:a', '128k',
        '-pix_fmt', 'yuv420p',
        '-t', f"{duration:.3f}",
        os.path.abspath(output_mp4_path)
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    if process.returncode != 0:
        raise Exception(f"FFmpeg scene compilation failed: {stderr.decode('utf-8', errors='ignore')}")

def concatenate_clips(clip_paths, output_video_path):
    """
    Uses FFmpeg stream copier to concatenate multiple MP4 files.
    This process runs instantly because it performs zero re-encoding.
    """
    ffmpeg_bin = imageio_ffmpeg.get_ffmpeg_exe()
    
    # Write concat list manifest file
    list_path = output_video_path + ".concat.txt"
    with open(list_path, 'w', encoding='utf-8') as f:
        for clip in clip_paths:
            # Escape single quotes in filenames for FFmpeg safety
            safe_clip = os.path.abspath(clip).replace("'", "'\\''")
            f.write(f"file '{safe_clip}'\n")
            
    cmd = [
        ffmpeg_bin,
        '-y',
        '-f', 'concat',
        '-safe', '0',
        '-i', os.path.abspath(list_path),
        '-c', 'copy', # Copy audio/video streams instantly without re-encoding
        os.path.abspath(output_video_path)
    ]
    
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    
    # Clean up concat list file
    try:
        os.remove(list_path)
    except:
        pass
        
    if process.returncode != 0:
        raise Exception(f"FFmpeg concatenation failed: {stderr.decode('utf-8', errors='ignore')}")

def generate_video_pipeline(task_id, text, engine, voice, speed, volume, silence_ms, resolution_type, theme_name, text_color, update_status_callback):
    """
    High-level background pipeline coordinating TTS audio synthesis,
    slide render compilation, scene clip exports, and final MP4 stitching.
    """
    temp_files = []
    scene_clips = []
    
    try:
        # 1. Segment Text
        update_status_callback(5, "Segmenting text script...")
        chunks = split_into_chunks(text, max_chars=config.DEFAULT_MAX_CHUNK_CHARS)
        total_scenes = len(chunks)
        
        if total_scenes == 0:
            raise ValueError("Text script contains no segments to compile.")
            
        update_status_callback(10, f"Split script into {total_scenes} scenes. Loading speech engine...")

        # 2. Select TTS Engine
        if engine == 'piper':
            generator = PiperGenerator(config.PIPER_BIN_PATH, config.MODELS_DIR)
            if not generator.is_available():
                raise TTSGenerationError("Piper engine not ready. Check model configurations.")
            voice_model = voice
        elif engine == 'kokoro':
            generator = KokoroGenerator(config.MODELS_DIR)
            if not generator.is_available():
                raise TTSGenerationError("Kokoro engine not ready. Check package setup.")
            voice_model = voice
        else:
            raise ValueError(f"Unsupported engine: {engine}")

        # Determine target resolution: portrait (9:16) for Shorts/Reels, landscape (16:9) for Youtube
        resolution = (1080, 1920) if resolution_type == 'portrait' else (1920, 1080)

        # 3. Compile individual scenes (audio + images -> video clip)
        for idx, chunk_text in enumerate(chunks):
            # Check for cancellation
            update_status_callback(
                10 + int((idx / total_scenes) * 70), 
                f"Compiling scene {idx + 1} of {total_scenes}..."
            )
            
            # Paths
            wav_path = os.path.join(config.TEMP_DIR, f"{task_id}_scene_{idx:03d}.wav")
            png_path = os.path.join(config.TEMP_DIR, f"{task_id}_scene_{idx:03d}.png")
            mp4_path = os.path.join(config.TEMP_DIR, f"{task_id}_scene_{idx:03d}.mp4")
            
            temp_files.extend([wav_path, png_path, mp4_path])
            
            # A. Generate Speech Chunk
            generator.generate(chunk_text, wav_path, voice_model, speed=speed)
            
            # Apply volume adjustments on PCM wav file if volume != 1.0
            if volume != 1.0:
                # Open, scale, save
                with wave.open(wav_path, 'rb') as r_wav:
                    params = r_wav.getparams()
                    nframes = r_wav.getnframes()
                    pcm_data = r_wav.readframes(nframes)
                
                scaled_pcm = scale_volume(pcm_data, params.sampwidth, volume)
                
                with wave.open(wav_path, 'wb') as w_wav:
                    w_wav.setparams(params)
                    w_wav.writeframes(scaled_pcm)
                    
            # Get duration of synthesized chunk
            duration = get_audio_duration(wav_path)
            
            # Pad with custom pause spacing
            clip_duration = duration + (silence_ms / 1000.0)
            
            # B. Render Pillow Captioned Slide Image
            create_slide_image(chunk_text, theme_name, text_color, resolution, png_path)
            
            # C. Compile Image + Audio into temporary scene MP4 clip
            render_scene_clip(png_path, wav_path, clip_duration, mp4_path)
            scene_clips.append(mp4_path)

        # 4. Concatenate clips into final output MP4
        update_status_callback(85, "Stitching scene clips into final MP4 video...")
        
        output_mp4_filename = f"{task_id}.mp4"
        output_mp4_path = os.path.join(config.OUTPUT_DIR, output_mp4_filename)
        
        concatenate_clips(scene_clips, output_mp4_path)
        
        # 5. Finished
        update_status_callback(100, "Video generated successfully!", status='completed', mp4_filename=output_mp4_filename)
        
    except Exception as e:
        tb = traceback.format_exc()
        print(f"Error in video generation task {task_id}: {str(e)}\n{tb}")
        update_status_callback(0, f"Error: {str(e)}", status='error', error=str(e))
        
    finally:
        # Cleanup all transient WAV, PNG, and temporary MP4 scene clips
        for path in temp_files:
            if os.path.exists(path):
                try:
                    os.remove(path)
                except:
                    pass
