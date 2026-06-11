import os
import wave
import struct
import math
import sys

# Add project root to python path to import modules
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from tts.chunker import split_sentences, group_sentences_into_chunks, split_into_chunks
from tts.merger import merge_wavs_to_mp3, scale_volume
from tts.generator import PiperGenerator, KokoroGenerator

def test_chunker():
    print("Running Chunker Tests...")
    
    # 1. Test sentence segmentation with abbreviations
    sample_text = "Hello Dr. Watson. Let's meet at 5:00 p.m. to discuss the case, e.g. the footprints. Is that fine?"
    sentences = split_sentences(sample_text)
    
    print(f"  Sentences parsed ({len(sentences)}):")
    for s in sentences:
        print(f"    - \"{s}\"")
        
    # We expect 3 sentences:
    # 1. "Hello Dr. Watson."
    # 2. "Let's meet at 5:00 p.m. to discuss the case, e.g. the footprints."
    # 3. "Is that fine?"
    assert len(sentences) == 3, f"Expected 3 sentences, got {len(sentences)}"
    assert "Dr. Watson" in sentences[0], "Sentence split prematurely after Dr."
    assert "e.g. the footprints" in sentences[1], "Sentence split prematurely after e.g."
    
    # 2. Test chunk grouping by character count limits
    long_sentences = [
        "This is sentence one which is relatively short.",
        "This is sentence two which has more words and length.",
        "And this is sentence three which is also a complete thought."
    ]
    # Limit max characters to 70.
    # len(long_sentences[0]) = 46
    # len(long_sentences[1]) = 53
    # Combined = 46 + 1 (space) + 53 = 100 > 70.
    # So sentence 1 and sentence 2 should be in separate chunks.
    chunks = group_sentences_into_chunks(long_sentences, max_chars=70)
    print(f"  Chunks created under 70 chars limit ({len(chunks)}):")
    for idx, c in enumerate(chunks):
        print(f"    Chunk {idx+1} (len={len(c)}): \"{c}\"")
        assert len(c) <= 70, f"Chunk exceeded limit: {len(c)}"
    
    assert len(chunks) == 3, f"Expected 3 chunks, got {len(chunks)}"
    
    print("[OK] Chunker tests passed!")
    print("-" * 40)

def create_dummy_wav(path, duration_sec=1.0, freq=440.0, rate=22050):
    """Generates a mono 16-bit WAV file with a sine wave for testing."""
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with wave.open(path, 'wb') as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        
        num_frames = int(duration_sec * rate)
        for i in range(num_frames):
            # Sine wave formula, amplitude scaled to fit 16-bit range (max 32767)
            sample = int(12000.0 * math.sin(2.0 * math.pi * freq * i / rate))
            # Pack as a signed 16-bit little-endian short integer ('<h')
            data = struct.pack('<h', sample)
            wav.writeframesraw(data)

def test_merger():
    print("Running Audio Merger & MP3 Encoder Tests...")
    
    # Paths
    temp_dir = os.path.join(os.path.dirname(__file__), 'temp_test')
    wav1 = os.path.join(temp_dir, 'tone1.wav')
    wav2 = os.path.join(temp_dir, 'tone2.wav')
    output_mp3 = os.path.join(temp_dir, 'merged_output.mp3')
    
    try:
        # 1. Create two dummy audio chunks
        print("  Generating test WAV tones...")
        create_dummy_wav(wav1, duration_sec=0.8, freq=440.0) # 440 Hz (A4)
        create_dummy_wav(wav2, duration_sec=0.5, freq=660.0) # 660 Hz (E5)
        
        assert os.path.exists(wav1), "Failed to write WAV 1"
        assert os.path.exists(wav2), "Failed to write WAV 2"
        
        # 2. Merge and convert to MP3
        # Injects 500ms silence and reduces volume to 75%
        print("  Merging WAVs and converting to MP3 using lameenc...")
        merge_wavs_to_mp3([wav1, wav2], output_mp3, silence_duration_ms=500, volume_factor=0.75)
        
        assert os.path.exists(output_mp3), "MP3 output file was not created"
        mp3_size = os.path.getsize(output_mp3)
        print(f"  Successfully compiled MP3: {output_mp3} ({mp3_size} bytes)")
        
        assert mp3_size > 0, "Generated MP3 file is empty"
        assert not os.path.exists(wav1), "Temporary WAV 1 was not cleaned up"
        assert not os.path.exists(wav2), "Temporary WAV 2 was not cleaned up"
        
        print("[OK] Audio Merger & MP3 Encoder tests passed!")
    
    finally:
        # Clean up output MP3 and test directory
        if os.path.exists(output_mp3):
            os.remove(output_mp3)
        if os.path.exists(temp_dir):
            try:
                os.rmdir(temp_dir)
            except:
                pass
    print("-" * 40)

def test_generators():
    print("Checking TTS Engine Wrappers...")
    
    base_dir = os.path.dirname(__file__)
    bin_path = os.path.join(base_dir, 'bin', 'piper', 'piper.exe')
    models_dir = os.path.join(base_dir, 'models')
    
    piper = PiperGenerator(bin_path, models_dir)
    print(f"  Piper Engine Available: {piper.is_available()}")
    
    kokoro = KokoroGenerator(models_dir)
    print(f"  Kokoro Engine Available: {kokoro.is_available()}")
    
    print("[OK] Generator checks completed!")
    print("-" * 40)

if __name__ == '__main__':
    print("=" * 40)
    print("STARTING PROGRAMMATIC SYSTEM VERIFICATION")
    print("=" * 40)
    
    try:
        test_chunker()
        test_merger()
        test_generators()
        print("ALL TESTS PASSED SUCCESSFULLY! Setup is programmatically correct.")
    except Exception as e:
        print(f"[ERROR] TEST ERROR OCCURRED: {e}")
        sys.exit(1)
