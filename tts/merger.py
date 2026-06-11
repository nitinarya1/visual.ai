import os
import wave
import array
import lameenc

def scale_volume(data, sampwidth, volume_factor):
    """
    Adjusts the volume of raw PCM bytes by scaling individual samples.
    Supports 8-bit (unsigned), 16-bit (signed), and 32-bit (signed) audio.
    """
    if volume_factor == 1.0:
        return data
        
    if sampwidth == 2:
        # 16-bit signed PCM (standard for Piper and Kokoro)
        samples = array.array('h', data)
        for idx in range(len(samples)):
            val = int(samples[idx] * volume_factor)
            if val > 32767:
                samples[idx] = 32767
            elif val < -32768:
                samples[idx] = -32768
            else:
                samples[idx] = val
        return samples.tobytes()
        
    elif sampwidth == 1:
        # 8-bit unsigned PCM (centered around 128)
        samples = array.array('B', data)
        for idx in range(len(samples)):
            val = int((samples[idx] - 128) * volume_factor) + 128
            if val > 255:
                samples[idx] = 255
            elif val < 0:
                samples[idx] = 0
            else:
                samples[idx] = val
        return samples.tobytes()
        
    elif sampwidth == 4:
        # 32-bit signed PCM
        samples = array.array('i', data)
        for idx in range(len(samples)):
            val = int(samples[idx] * volume_factor)
            if val > 2147483647:
                samples[idx] = 2147483647
            elif val < -2147483648:
                samples[idx] = -2147483648
            else:
                samples[idx] = val
        return samples.tobytes()
        
    return data

def merge_wavs_to_mp3(wav_paths, output_mp3_path, silence_duration_ms=500, volume_factor=1.0):
    """
    Merges multiple WAV files into a single MP3 file.
    Inserts silent gaps between chunks and applies volume scaling.
    Cleans up the intermediate WAV files after successful conversion.
    """
    if not wav_paths:
        raise ValueError("No WAV files provided for merging.")

    # Open the first WAV file to extract parameters
    with wave.open(wav_paths[0], 'rb') as first_wav:
        params = first_wav.getparams()
        channels = params.nchannels
        sampwidth = params.sampwidth
        sample_rate = params.framerate

    pcm_data_list = []
    
    # Generate silence bytes
    num_silence_frames = int(sample_rate * (silence_duration_ms / 1000.0))
    # Silence is just zero bytes for signed PCM
    # (Note: For 8-bit unsigned, silence should be 128, but Piper/Kokoro use 16-bit signed where silence is 0)
    silence_byte_value = 128 if sampwidth == 1 else 0
    silence_bytes = bytes([silence_byte_value]) * (num_silence_frames * sampwidth * channels)

    for i, path in enumerate(wav_paths):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Temporary audio chunk not found: {path}")
            
        with wave.open(path, 'rb') as wav:
            # Ensure formats are identical
            if (wav.getnchannels() != channels or 
                wav.getsampwidth() != sampwidth or 
                wav.getframerate() != sample_rate):
                raise ValueError(f"Audio format mismatch in chunk: {path}")
                
            nframes = wav.getnframes()
            data = wav.readframes(nframes)
            
            # Apply volume adjustments if necessary
            if volume_factor != 1.0:
                data = scale_volume(data, sampwidth, volume_factor)
                
            pcm_data_list.append(data)
            
            # Append silence between sequential chunks (not after the final chunk)
            if i < len(wav_paths) - 1 and silence_duration_ms > 0:
                pcm_data_list.append(silence_bytes)

    # Combine all audio chunks in memory
    merged_pcm = b''.join(pcm_data_list)

    # Encode raw PCM to MP3
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(channels)
    encoder.set_quality(2)  # Quality level (2 is very high, 0 is highest, 9 is lowest)
    
    mp3_data = encoder.encode(merged_pcm)
    mp3_data += encoder.flush()

    # Save to disk
    os.makedirs(os.path.dirname(output_mp3_path), exist_ok=True)
    with open(output_mp3_path, 'wb') as f:
        f.write(mp3_data)

    # Clean up intermediate files
    for path in wav_paths:
        try:
            os.remove(path)
        except Exception as e:
            # Non-blocking error logging
            print(f"Warning: Failed to clean up temp file {path}: {e}")
