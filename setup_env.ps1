# setup_env.ps1
# Automated Setup Script for Vocalis (Offline Text-to-Speech)

$ErrorActionPreference = "Stop"

Write-Host "==============================================" -ForegroundColor Cyan
Write-Host "Starting Automated Environment Setup & Download" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan

# 1. Install Python if not present
$pythonExe = ""
try {
    # Check if python works
    $version = & python --version 2>$null
    Write-Host "Python already available globally." -ForegroundColor Green
    $pythonExe = "python"
} catch {
    Write-Host "Python not found globally. Checking standard installations..." -ForegroundColor Yellow
}

if ($pythonExe -eq "") {
    # Check common user appdata folders
    $userPath = "$env:USERPROFILE\AppData\Local\Programs\Python\Python311\python.exe"
    $systemPath = "C:\Program Files\Python311\python.exe"
    
    if (Test-Path $userPath) {
        Write-Host "Found Python 3.11 in user folder: $userPath" -ForegroundColor Green
        $pythonExe = $userPath
    } elseif (Test-Path $systemPath) {
        Write-Host "Found Python 3.11 in system folder: $systemPath" -ForegroundColor Green
        $pythonExe = $systemPath
    } else {
        Write-Host "Python 3.11 not found on system. Installing via winget..." -ForegroundColor Yellow
        # Run winget installation
        & winget install --id Python.Python.3.11 --exact --silent --accept-source-agreements --accept-package-agreements
        
        Write-Host "Python installation triggered. Waiting for registry update (10 seconds)..." -ForegroundColor Yellow
        Start-Sleep -Seconds 10
        
        # Verify installation paths
        if (Test-Path $userPath) {
            $pythonExe = $userPath
        } elseif (Test-Path $systemPath) {
            $pythonExe = $systemPath
        } else {
            # Last ditch attempt: reload env or search
            Write-Host "Searching for installed python.exe..." -ForegroundColor Yellow
            $search = Get-ChildItem -Path "$env:USERPROFILE\AppData\Local\Programs\Python" -Filter "python.exe" -Recurse -ErrorAction SilentlyContinue
            if ($search) {
                $pythonExe = $search[0].FullName
            } else {
                throw "Python installation failed or could not be located. Please install Python 3.11 manually from python.org and rerun this script."
            }
        }
        Write-Host "Python installed and located at: $pythonExe" -ForegroundColor Green
    }
}

# 2. Create Virtual Environment
Write-Host "Creating python virtual environment (venv)..." -ForegroundColor Cyan
if (Test-Path "venv") {
    Write-Host "Virtual environment (venv) already exists. Skipping creation." -ForegroundColor Green
} else {
    & $pythonExe -m venv venv
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
}

# Determine venv pip and python executable paths
$venvPip = "venv\Scripts\pip.exe"
$venvPython = "venv\Scripts\python.exe"

# 3. Install packages
Write-Host "Installing requirements from requirements.txt..." -ForegroundColor Cyan
& $venvPip install -r requirements.txt
Write-Host "Dependencies installed successfully." -ForegroundColor Green

# 4. Download and configure Piper binary
Write-Host "Checking Piper C++ binary..." -ForegroundColor Cyan
$piperBin = "bin\piper\piper.exe"
if (Test-Path $piperBin) {
    Write-Host "Piper binary found." -ForegroundColor Green
} else {
    Write-Host "Downloading Piper CLI binary (v1.2.0) from GitHub..." -ForegroundColor Yellow
    $zipPath = "piper.zip"
    $url = "https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_windows_amd64.zip"
    
    # Download zip file
    Invoke-WebRequest -Uri $url -OutFile $zipPath
    Write-Host "Download complete. Extracting..." -ForegroundColor Yellow
    
    # Create temporary extraction dir
    New-Item -ItemType Directory -Path "bin\piper\temp" -Force | Out-Null
    Expand-Archive -Path $zipPath -DestinationPath "bin\piper\temp" -Force
    
    # Move files out of double directory
    Move-Item -Path "bin\piper\temp\piper\*" -Destination "bin\piper\" -Force
    
    # Cleanup temp
    Remove-Item -Path "bin\piper\temp" -Recurse -Force | Out-Null
    Remove-Item -Path $zipPath -Force | Out-Null
    
    Write-Host "Piper CLI binary successfully set up at $piperBin." -ForegroundColor Green
}

# 5. Download default English Piper Voice model
Write-Host "Checking Piper Voice Model..." -ForegroundColor Cyan
$voiceOnnx = "models\en_US-lessac-medium.onnx"
$voiceJson = "models\en_US-lessac-medium.onnx.json"

if ((Test-Path $voiceOnnx) -and (Test-Path $voiceJson)) {
    Write-Host "Piper default model found." -ForegroundColor Green
} else {
    Write-Host "Downloading Piper model (en_US-lessac-medium.onnx)..." -ForegroundColor Yellow
    $onnxUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx"
    $jsonUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json"
    
    New-Item -ItemType Directory -Path "models" -Force | Out-Null
    Invoke-WebRequest -Uri $onnxUrl -OutFile $voiceOnnx
    Invoke-WebRequest -Uri $jsonUrl -OutFile $voiceJson
    Write-Host "Piper voice model downloaded successfully." -ForegroundColor Green
}

# 5.1 Download Piper Indian Male Narrator Model (hi_IN-rohan-medium)
Write-Host "Checking Piper Indian Male Narrator Model..." -ForegroundColor Cyan
$inVoiceOnnx = "models\hi_IN-rohan-medium.onnx"
$inVoiceJson = "models\hi_IN-rohan-medium.onnx.json"

if ((Test-Path $inVoiceOnnx) -and (Test-Path $inVoiceJson)) {
    Write-Host "Piper Indian Male model found." -ForegroundColor Green
} else {
    Write-Host "Downloading Piper Indian Male model (hi_IN-rohan-medium.onnx)..." -ForegroundColor Yellow
    $inOnnxUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx"
    $inJsonUrl = "https://huggingface.co/rhasspy/piper-voices/resolve/main/hi/hi_IN/rohan/medium/hi_IN-rohan-medium.onnx.json"
    
    Invoke-WebRequest -Uri $inOnnxUrl -OutFile $inVoiceOnnx
    Invoke-WebRequest -Uri $inJsonUrl -OutFile $inVoiceJson
    Write-Host "Piper Indian Male voice model downloaded successfully." -ForegroundColor Green
}

# 6. Download Kokoro ONNX model fallback (Optional but good)
Write-Host "Checking Kokoro Model Assets..." -ForegroundColor Cyan
$kokoroOnnx = "models\kokoro-v0_19.onnx"
$kokoroVoices = "models\voices.bin"

if ((Test-Path $kokoroOnnx) -and (Test-Path $kokoroVoices)) {
    Write-Host "Kokoro model assets found." -ForegroundColor Green
} else {
    Write-Host "Downloading Kokoro model assets (~100MB)..." -ForegroundColor Yellow
    $kokoroUrl = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx"
    $voicesUrl = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"
    
    Invoke-WebRequest -Uri $kokoroUrl -OutFile $kokoroOnnx
    Invoke-WebRequest -Uri $voicesUrl -OutFile $kokoroVoices
    Write-Host "Kokoro model assets downloaded successfully." -ForegroundColor Green
}

# 7. Run diagnostic tests
Write-Host "Running project diagnostic verification script..." -ForegroundColor Cyan
& $venvPython test_tts.py

Write-Host "==============================================" -ForegroundColor Green
Write-Host "ENVIRONMENT SETUP COMPLETED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "To run the application, execute:" -ForegroundColor Green
Write-Host "  venv\Scripts\python.exe app.py" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
