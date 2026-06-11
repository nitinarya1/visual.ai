# Offline Personal Text-to-Speech Web Application

A lightweight, modern, and completely offline Text-to-Speech (TTS) web application. Designed to run smoothly on a Dell Latitude 7470 laptop with an **Intel CPU, 8 GB RAM, and Windows 10/11** using zero cloud APIs.

## Key Features
- **Punctuation-Aware Chunking:** Intelligently segment long-form content (up to 3,000 words, ~15-20 minutes of audio) into context-safe blocks, avoiding TTS engine buffer overflows.
- **Double Synthesis Engines:** Runs **Piper TTS** (CPU optimized, extremely fast C++) as the primary engine and supports **Kokoro TTS** (high-quality, ONNX CPU runtime) as a secondary engine.
- **FFmpeg-Free Architecture:** Processes WAV concatenation and scales PCM volumes directly in Python. Converts raw PCM to MP3 using LAME encoder bindings (`lameenc`), removing the need to install FFmpeg on Windows.
- **System Telemetry:** Live RAM and storage monitors embedded in the UI to ensure the app stays well below the 4 GB memory ceiling.

---

## Folder Structure

```text
personal-tts/
│
├── app.py                  # Flask Web Server & Background Queue
├── requirements.txt        # Local python dependencies
├── config.py               # Core application and engine paths
│
├── templates/
│   └── index.html          # Web UI layout
├── static/
│   ├── css/style.css       # Sleek Glassmorphic Dark UI styles
│   └── js/main.js          # Telemetry and async REST calls
│
├── bin/
│   └── piper/              # Directory for downloaded piper.exe
├── models/                 # Directory for downloading TTS models
├── uploads/                # Directory for user uploaded text files
├── output/                 # Directory containing completed MP3s
├── temp/                   # Directory containing transient wav chunks
│
├── tts/
│   ├── chunker.py          # Sentence-split and paragraph grouping
│   ├── generator.py        # Subprocess (Piper) and ONNX (Kokoro) synthesis
│   └── merger.py           # PCM stitching, volume control, MP3 writer
│
├── test_tts.py             # Diagnostic test script
└── README.md               # Setup and Optimization Guide
```

---

## Installation & Setup Guide

### Step 1: Install Python (Windows 10/11)
If you don't already have Python 3.10 or 3.11 installed:
1. Download Python 3.10.x or 3.11.x from the official page: [Python Releases for Windows](https://www.python.org/downloads/windows/).
2. Run the installer.
3. **CRITICAL:** Make sure to check the box that says **"Add Python to PATH"** before clicking *Install Now*.

### Step 2: Download the Piper Synthesizer Binary
Piper is compiled in C++ for maximum CPU speed.
1. Download the standalone Windows release package: **`piper_windows_amd64.zip`** from [Piper Releases on GitHub](https://github.com/rhasspy/piper/releases/latest).
2. Extract the ZIP file.
3. Copy the extracted files (including `piper.exe`, `libonnxruntime.dll`, etc.) and paste them directly into the project's **`bin/piper/`** folder.
4. Verify you have `personal-tts/bin/piper/piper.exe` in place.

### Step 3: Download TTS Voice Models
Place all downloaded model assets in the project's **`models/`** folder.

#### A. Piper Voice Models (Primary)
Each voice requires a `.onnx` model file and a `.onnx.json` configuration file:
- **Indian Male Narrator Default (`hi_IN-rohan-medium`):**
  - Download [hi_IN-rohan-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx)
  - Download [hi_IN-rohan-medium.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx.json)
- **English Default (`en_US-lessac-medium` - Optional):**
  - Download [en_US-lessac-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx)
  - Download [en_US-lessac-medium.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json)

#### B. Kokoro Model Assets (Secondary - Optional)
To enable the Kokoro ONNX engine with the Hindi Male narrator voice (`hm_beta`):
- Download the ONNX model: [kokoro-v1.0.int8.onnx (80 MB)](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx) and save it as `kokoro-v0_19.onnx`.
- Download the voices binary: [voices-v1.0.bin (21 MB)](https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin) and save it as `voices.bin`.

### Step 4: Install Dependencies & Run Tests
Open PowerShell or Command Prompt, navigate to the project directory, and run:

```powershell
# Navigate to project folder
cd C:\Users\aryar\.gemini\antigravity\scratch\personal-tts

# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# For PowerShell:
.\venv\Scripts\Activate.ps1
# For Command Prompt:
.\venv\Scripts\activate.bat

# Install python libraries
pip install -r requirements.txt

# Run automated tests to check config & imports
python test_tts.py
```

### Step 5: Start the Web App
With your virtual environment active, run:
```powershell
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 8 GB RAM Optimization Guide

This application is strictly engineered to maintain a light resource footprint, targetting **under 1.5 GB memory consumption** (well below the 4 GB limit):

1. **Incremental Processing:** Rather than rendering 3,000 words in one massive run, the app segments the text into small chunks (~800 characters) in `tts/chunker.py`.
2. **Subprocess Isolation (Piper):** Piper runs in a standalone `piper.exe` subprocess. It processes text fed from the Python parent via standard input, generates the WAV chunk, and exits. This immediately releases CPU RAM back to Windows after each chunk is finished.
3. **Model Caching (Kokoro):** When using Kokoro, loading the ONNX model can take a few seconds and consume 150MB of RAM. The app caches this session in memory (`tts/generator.py`), preventing the engine from leaking memory or causing load-latencies on consecutive text chunks.
4. **Pure Python Audio Stitching:** Chunks are merged by reading WAV frames directly using Python's core `wave` module. High-performance Python `array` instances scale the 16-bit PCM amplitude values. This handles audio combinations in-memory, bypassing expensive disk reads/writes and eliminating dependency on external converters.
5. **Memory-to-Disk MP3 Encoding:** Concatenated PCM samples are encoded into MP3 using the highly-optimized C-based LAME encoder `lameenc` python library. It takes raw PCM from memory, writes the final `.mp3` directly to disk, and deletes all intermediate WAV files.
