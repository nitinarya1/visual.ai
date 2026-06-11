// Global State
let currentEngine = 'piper';
let currentMode = 'audio';
let currentAspect = 'portrait';
let systemStatus = {};
let activeTaskId = null;
let statusPollingInterval = null;
let startTime = null;

// DOM Elements
const btnEnginePiper = document.getElementById('btn-engine-piper');
const btnEngineKokoro = document.getElementById('btn-engine-kokoro');
const voiceSelect = document.getElementById('voice-select');
const voiceInfoHelp = document.getElementById('voice-info-help');

const btnModeAudio = document.getElementById('btn-mode-audio');
const btnModeVideo = document.getElementById('btn-mode-video');
const videoSettingsGroup = document.getElementById('video-settings-group');
const btnAspectPortrait = document.getElementById('btn-aspect-portrait');
const btnAspectLandscape = document.getElementById('btn-aspect-landscape');
const themeSelect = document.getElementById('theme-select');
const colorSelect = document.getElementById('color-select');
const aiBackgroundsToggle = document.getElementById('ai-backgrounds-toggle');

const mainTitle = document.getElementById('main-title');
const mainSubtitle = document.getElementById('main-subtitle');

const speedSlider = document.getElementById('speed-slider');
const speedValue = document.getElementById('speed-value');
const volumeSlider = document.getElementById('volume-slider');
const volumeValue = document.getElementById('volume-value');
const silenceSlider = document.getElementById('silence-slider');
const silenceValue = document.getElementById('silence-value');

const ramText = document.getElementById('ram-text');
const ramProgress = document.getElementById('ram-progress');
const diskText = document.getElementById('disk-text');
const diskProgress = document.getElementById('disk-progress');

const textInput = document.getElementById('text-input');
const charCount = document.getElementById('char-count');
const wordCount = document.getElementById('word-count');
const fileUploader = document.getElementById('file-uploader');
const dropZone = document.getElementById('drop-zone');
const btnClear = document.getElementById('btn-clear');
const btnGenerate = document.getElementById('btn-generate');

const outputCard = document.getElementById('output-card');
const statusContainer = document.getElementById('status-container');
const statusTitle = document.getElementById('status-title');
const statusMsg = document.getElementById('status-msg');
const statusSpinner = document.getElementById('status-spinner');
const statusSuccessIcon = document.getElementById('status-success-icon');
const statusErrorIcon = document.getElementById('status-error-icon');
const statusProgressFill = document.getElementById('status-progress-fill');
const statusPercentage = document.getElementById('status-percentage');
const chunkCounter = document.getElementById('chunk-counter');
const elapsedTime = document.getElementById('elapsed-time');
const waveVisual = document.getElementById('wave-visual');
const btnCancel = document.getElementById('btn-cancel');

const playerContainer = document.getElementById('player-container');
const playerTitle = document.getElementById('player-title');
const audioPlayerWrapper = document.getElementById('audio-player-wrapper');
const videoPlayerWrapper = document.getElementById('video-player-wrapper');
const audioPlayer = document.getElementById('audio-player');
const videoPlayer = document.getElementById('video-player');
const btnPlayCustom = document.getElementById('btn-play-custom');
const btnDownload = document.getElementById('btn-download');
const setupAlert = document.getElementById('setup-alert');
const setupAlertText = document.getElementById('setup-alert-text');

// Kokoro static voices (supported natively by Kokoro ONNX model)
const KOKORO_VOICES = [
    { value: 'af_bella', label: 'Bella (US Female)' },
    { value: 'af_sarah', label: 'Sarah (US Female)' },
    { value: 'am_adam', label: 'Adam (US Male)' },
    { value: 'am_michael', label: 'Michael (US Male)' },
    { value: 'bf_emma', label: 'Emma (UK Female)' },
    { value: 'bm_george', label: 'George (UK Male)' },
    { value: 'hf_alpha', label: 'Alpha (Hindi Female)' },
    { value: 'hf_beta', label: 'Beta (Hindi Female)' },
    { value: 'hm_omega', label: 'Omega (Hindi Male - Narrator)' },
    { value: 'hm_psi', label: 'Psi (Hindi Male)' }
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    bindEvents();
    updateTextCounter();
    fetchSystemStatus();
    // Periodically update system telemetry every 5 seconds
    setInterval(fetchSystemStatus, 5000);
});

// Event Listeners Binding
function bindEvents() {
    // Engine switching
    btnEnginePiper.addEventListener('click', () => setEngine('piper'));
    btnEngineKokoro.addEventListener('click', () => setEngine('kokoro'));

    // Mode switching
    btnModeAudio.addEventListener('click', () => setMode('audio'));
    btnModeVideo.addEventListener('click', () => setMode('video'));

    // Aspect switching
    btnAspectPortrait.addEventListener('click', () => setAspect('portrait'));
    btnAspectLandscape.addEventListener('click', () => setAspect('landscape'));

    // Range Sliders
    speedSlider.addEventListener('input', (e) => {
        speedValue.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
    });
    volumeSlider.addEventListener('input', (e) => {
        volumeValue.textContent = `${parseFloat(e.target.value).toFixed(1)}x`;
    });
    silenceSlider.addEventListener('input', (e) => {
        silenceValue.textContent = `${(parseInt(e.target.value) / 1000).toFixed(1)}s`;
    });

    // Textarea interaction
    textInput.addEventListener('input', updateTextCounter);

    // Clear Button
    btnClear.addEventListener('click', () => {
        textInput.value = '';
        updateTextCounter();
    });

    // File Drop Zone
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    ['dragleave', 'dragend', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropZone.classList.remove('dragover');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleTextFileUpload(files[0]);
        }
    });

    // File Input Uploader
    fileUploader.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleTextFileUpload(e.target.files[0]);
        }
    });

    // Generate Button
    btnGenerate.addEventListener('click', startSynthesis);

    // Cancel Button
    btnCancel.addEventListener('click', cancelSynthesis);

    // Custom Play Button
    btnPlayCustom.addEventListener('click', toggleAudioPlayback);
}

// Set active engine (Piper vs Kokoro)
function setEngine(engine) {
    currentEngine = engine;
    if (engine === 'piper') {
        btnEnginePiper.classList.add('active');
        btnEngineKokoro.classList.remove('active');
    } else {
        btnEnginePiper.classList.remove('active');
        btnEngineKokoro.classList.add('active');
    }
    populateVoices();
    checkEngineStatusAlert();
}

// Set active mode (Audio vs Video)
function setMode(mode) {
    currentMode = mode;
    if (mode === 'audio') {
        btnModeAudio.classList.add('active');
        btnModeVideo.classList.remove('active');
        videoSettingsGroup.classList.add('hidden');
        mainTitle.textContent = 'Offline Text-to-Speech Reader';
        mainSubtitle.textContent = 'Read long texts (up to 3,000 words) completely offline without cloud tracking.';
        btnGenerate.innerHTML = '<i class="fa-solid fa-circle-play"></i> Generate Speech';
    } else {
        btnModeAudio.classList.remove('active');
        btnModeVideo.classList.add('active');
        videoSettingsGroup.classList.remove('hidden');
        mainTitle.textContent = 'Offline Text-to-Video Slideshow Creator';
        mainSubtitle.textContent = 'Convert scripts to landscape/portrait styled fact videos completely offline.';
        btnGenerate.innerHTML = '<i class="fa-solid fa-video"></i> Generate Video';
    }
}

// Set active aspect ratio (Portrait vs Landscape)
function setAspect(aspect) {
    currentAspect = aspect;
    if (aspect === 'portrait') {
        btnAspectPortrait.classList.add('active');
        btnAspectLandscape.classList.remove('active');
    } else {
        btnAspectPortrait.classList.remove('active');
        btnAspectLandscape.classList.add('active');
    }
}

// Handle file loading
function handleTextFileUpload(file) {
    if (!file.name.endsWith('.txt')) {
        alert('Unsupported file format. Please upload a plain text file (.txt).');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        textInput.value = e.target.result;
        updateTextCounter();
    };
    reader.onerror = () => {
        alert('Error reading text file.');
    };
    reader.readAsText(file);
}

// Text word/char counter
function updateTextCounter() {
    const text = textInput.value;
    const charLen = text.length;
    // Simple word splitter
    const words = text.trim() === '' ? 0 : text.trim().split(/\s+/).length;
    
    charCount.textContent = charLen.toLocaleString();
    wordCount.textContent = words.toLocaleString();

    // Visual warning if words exceed 3,000 limit
    if (words > 3000) {
        wordCount.style.color = '#EF4444';
        wordCount.style.fontWeight = '700';
    } else {
        wordCount.style.color = '';
        wordCount.style.fontWeight = '';
    }
}

// Fetch telemetry status from API
async function fetchSystemStatus() {
    try {
        const response = await fetch('/api/system-status');
        if (!response.ok) throw new Error('Failed to fetch telemetry');
        
        systemStatus = await response.json();
        
        // Update UI telemetries
        ramText.textContent = `${systemStatus.ram_used} / ${systemStatus.ram_total}`;
        ramProgress.style.width = `${systemStatus.ram_percent}%`;
        
        // Dynamic RAM alert color
        if (systemStatus.ram_percent > 85) {
            ramProgress.className = 'progress-bar-fill';
            ramProgress.style.backgroundColor = '#EF4444';
        } else if (systemStatus.ram_percent > 65) {
            ramProgress.className = 'progress-bar-fill';
            ramProgress.style.backgroundColor = '#F59E0B';
        } else {
            ramProgress.className = 'progress-bar-fill green-gradient';
            ramProgress.style.backgroundColor = '';
        }

        diskText.textContent = `${systemStatus.disk_free} free`;
        
        // Calculate disk percentage (assume total represents bounds)
        const freeGB = parseFloat(systemStatus.disk_free);
        const totalGB = parseFloat(systemStatus.disk_total);
        if (totalGB > 0) {
            const diskPercent = ((totalGB - freeGB) / totalGB) * 100;
            diskProgress.style.width = `${100 - diskPercent}%`; // inverse of used
        }

        // Update voice dropdown dynamically (only on first load or if engines change)
        if (voiceSelect.childElementCount === 0 || 
            (currentEngine === 'piper' && voiceSelect.getAttribute('data-loaded-engine') !== 'piper') ||
            (currentEngine === 'kokoro' && voiceSelect.getAttribute('data-loaded-engine') !== 'kokoro')) {
            populateVoices();
        }

        checkEngineStatusAlert();
    } catch (error) {
        console.error('System status query failed:', error);
    }
}

// Populate voice dropdown options
function populateVoices() {
    voiceSelect.innerHTML = '';
    voiceSelect.setAttribute('data-loaded-engine', currentEngine);

    if (currentEngine === 'piper') {
        const models = systemStatus.piper_models || [];
        if (models.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = '-- No Piper Models Found --';
            voiceSelect.appendChild(opt);
            voiceInfoHelp.textContent = 'Place .onnx and .onnx.json files into your models/ folder.';
            voiceInfoHelp.style.color = '#F59E0B';
        } else {
            models.forEach(model => {
                const opt = document.createElement('option');
                opt.value = model;
                opt.textContent = model;
                if (model === 'hi_IN-rohan-medium') {
                    opt.selected = true;
                }
                voiceSelect.appendChild(opt);
            });
            voiceInfoHelp.textContent = `Found ${models.length} model(s) in models/ directory.`;
            voiceInfoHelp.style.color = '';
        }
    } else {
        // Kokoro
        KOKORO_VOICES.forEach(voice => {
            const opt = document.createElement('option');
            opt.value = voice.value;
            opt.textContent = voice.label;
            if (voice.value === 'hm_omega') {
                opt.selected = true;
            }
            voiceSelect.appendChild(opt);
        });
        voiceInfoHelp.textContent = 'Kokoro requires kokoro-v0_19.onnx and voices.bin in models/';
        voiceInfoHelp.style.color = '';
    }
}

// Check warnings
function checkEngineStatusAlert() {
    if (currentEngine === 'piper') {
        if (!systemStatus.piper_available) {
            showSetupAlert("Piper binary ('piper.exe') is missing from the bin/piper directory. Please download it to use Piper.");
        } else if (!systemStatus.piper_models || systemStatus.piper_models.length === 0) {
            showSetupAlert("No Piper voice models (.onnx) detected in models/. Syntheses will fail until a model is downloaded.");
        } else {
            hideSetupAlert();
        }
    } else {
        // Kokoro
        if (!systemStatus.kokoro_available) {
            showSetupAlert("Kokoro model files are missing or python dependencies are not installed. Please download 'kokoro-v0_19.onnx' and 'voices.bin' to models/ and check setup.");
        } else {
            hideSetupAlert();
        }
    }
}

function showSetupAlert(message) {
    setupAlertText.textContent = message;
    setupAlert.classList.remove('hidden');
}

function hideSetupAlert() {
    setupAlert.classList.add('hidden');
}

// Begin synthesis workflow
async function startSynthesis() {
    const text = textInput.value.trim();
    if (!text) {
        alert('Please enter some text to synthesize.');
        return;
    }

    const voice = voiceSelect.value;
    if (currentEngine === 'piper' && !voice) {
        alert('Please download and select a valid Piper voice model.');
        return;
    }

    // Reset players
    audioPlayer.pause();
    audioPlayer.removeAttribute('src');
    audioPlayer.load();
    videoPlayer.pause();
    videoPlayer.removeAttribute('src');
    videoPlayer.load();

    // Reset and show status card
    outputCard.classList.remove('hidden');
    statusContainer.classList.remove('hidden');
    playerContainer.classList.add('hidden');
    
    // Status visual elements reset
    statusSpinner.classList.remove('hidden');
    statusSuccessIcon.classList.add('hidden');
    statusErrorIcon.classList.add('hidden');
    btnCancel.classList.remove('hidden');
    waveVisual.classList.remove('hidden');
    chunkCounter.classList.add('hidden');

    statusTitle.textContent = 'Initializing Task';
    statusMsg.textContent = 'Connecting to backend...';
    statusProgressFill.style.width = '0%';
    statusPercentage.textContent = '0%';
    
    startTime = Date.now();
    updateElapsedTimeDisplay();

    // Retrieve values
    const speed = parseFloat(speedSlider.value);
    const volume = parseFloat(volumeSlider.value);
    const silence_ms = parseInt(silenceSlider.value);

    // Disable generate button during process
    btnGenerate.disabled = true;
    btnGenerate.style.opacity = '0.5';

    try {
        const endpoint = currentMode === 'video' ? '/api/generate-video' : '/api/generate';
        const payload = {
            text: text,
            engine: currentEngine,
            voice: voice,
            speed: speed,
            volume: volume,
            silence_ms: silence_ms
        };

        if (currentMode === 'video') {
            payload.resolution = currentAspect;
            payload.theme = themeSelect.value;
            payload.color = colorSelect.value;
            payload.ai_backgrounds = aiBackgroundsToggle.checked;
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || 'Failed to start synthesis.');
        }

        activeTaskId = data.task_id;
        
        // Start polling status
        statusPollingInterval = setInterval(pollTaskStatus, 1000);
        
    } catch (error) {
        handleSynthesisError(error.message);
    }
}

// Polling worker status
async function pollTaskStatus() {
    if (!activeTaskId) return;

    try {
        const response = await fetch(`/api/status/${activeTaskId}`);
        if (!response.ok) throw new Error('Failed to query task status.');

        const task = await response.json();
        
        // Update elapsed time
        updateElapsedTimeDisplay();

        // Update progress bar & label
        statusProgressFill.style.width = `${task.progress}%`;
        statusPercentage.textContent = `${task.progress}%`;
        statusMsg.textContent = task.message;

        // Update chunk counts
        if (task.total_chunks > 0) {
            chunkCounter.textContent = `Chunk ${task.current_chunk} / ${task.total_chunks}`;
            chunkCounter.classList.remove('hidden');
        }

        if (task.status === 'completed') {
            if (task.mp4_filename) {
                handleVideoSynthesisSuccess(task.mp4_filename);
            } else {
                handleSynthesisSuccess(task.mp3_filename);
            }
        } else if (task.status === 'error') {
            handleSynthesisError(task.error || 'Unknown error occurred.');
        } else if (task.status === 'cancelled') {
            handleSynthesisCancelled();
        }
    } catch (error) {
        console.error(error);
        // Continue polling unless network is completely down
    }
}

// Cancellation workflow
async function cancelSynthesis() {
    if (!activeTaskId) return;

    statusMsg.textContent = 'Requesting cancellation...';
    btnCancel.disabled = true;

    try {
        await fetch(`/api/cancel/${activeTaskId}`, { method: 'POST' });
    } catch (error) {
        console.error('Cancellation failed:', error);
    }
}

// Handle completion
function handleSynthesisSuccess(mp3Filename) {
    clearInterval(statusPollingInterval);
    activeTaskId = null;

    statusTitle.textContent = 'Completed';
    statusMsg.textContent = 'MP3 file ready for playback and download.';
    statusSpinner.classList.add('hidden');
    statusSuccessIcon.classList.remove('hidden');
    btnCancel.classList.add('hidden');
    waveVisual.classList.add('hidden');

    // Setup player view
    playerTitle.innerHTML = '<i class="fa-solid fa-waveform-lines"></i> Synthesized Audio Output';
    audioPlayerWrapper.classList.remove('hidden');
    videoPlayerWrapper.classList.add('hidden');

    const downloadUrl = `/api/download/${mp3Filename}`;
    audioPlayer.src = downloadUrl;
    btnDownload.href = downloadUrl;

    playerContainer.classList.remove('hidden');
    btnGenerate.disabled = false;
    btnGenerate.style.opacity = '';
    btnCancel.disabled = false;
}

// Handle video completion
function handleVideoSynthesisSuccess(mp4Filename) {
    clearInterval(statusPollingInterval);
    activeTaskId = null;

    statusTitle.textContent = 'Completed';
    statusMsg.textContent = 'MP4 video file ready for playback and download.';
    statusSpinner.classList.add('hidden');
    statusSuccessIcon.classList.remove('hidden');
    btnCancel.classList.add('hidden');
    waveVisual.classList.add('hidden');

    // Setup player view
    playerTitle.innerHTML = '<i class="fa-solid fa-file-video"></i> Synthesized Video Output';
    audioPlayerWrapper.classList.add('hidden');
    videoPlayerWrapper.classList.remove('hidden');

    const downloadUrl = `/api/download/${mp4Filename}`;
    videoPlayer.src = downloadUrl;
    btnDownload.href = `${downloadUrl}?download=true`;

    playerContainer.classList.remove('hidden');
    btnGenerate.disabled = false;
    btnGenerate.style.opacity = '';
    btnCancel.disabled = false;
}

// Handle error
function handleSynthesisError(errorMessage) {
    clearInterval(statusPollingInterval);
    activeTaskId = null;

    statusTitle.textContent = 'Failed';
    statusMsg.textContent = errorMessage;
    statusSpinner.classList.add('hidden');
    statusErrorIcon.classList.remove('hidden');
    btnCancel.classList.add('hidden');
    waveVisual.classList.add('hidden');

    btnGenerate.disabled = false;
    btnGenerate.style.opacity = '';
    btnCancel.disabled = false;
}

// Handle cancel
function handleSynthesisCancelled() {
    clearInterval(statusPollingInterval);
    activeTaskId = null;

    statusTitle.textContent = 'Cancelled';
    statusMsg.textContent = 'Audio synthesis cancelled by user.';
    statusSpinner.classList.add('hidden');
    statusErrorIcon.classList.remove('hidden');
    btnCancel.classList.add('hidden');
    waveVisual.classList.add('hidden');

    btnGenerate.disabled = false;
    btnGenerate.style.opacity = '';
    btnCancel.disabled = false;
}

// Time elapsed updates
function updateElapsedTimeDisplay() {
    if (!startTime) return;
    const diff = (Date.now() - startTime) / 1000;
    elapsedTime.textContent = `${diff.toFixed(1)}s`;
}

// Playback hook
function toggleAudioPlayback() {
    if (currentMode === 'video') {
        if (videoPlayer.paused) {
            videoPlayer.play();
            btnPlayCustom.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
        } else {
            videoPlayer.pause();
            btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
        }
    } else {
        if (audioPlayer.paused) {
            audioPlayer.play();
            btnPlayCustom.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
        } else {
            audioPlayer.pause();
            btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
        }
    }
}

// Listen to native audio player state to sync the play button
audioPlayer.addEventListener('play', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
});
audioPlayer.addEventListener('pause', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
});
audioPlayer.addEventListener('ended', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
});

// Listen to native video player state to sync the play button
videoPlayer.addEventListener('play', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
});
videoPlayer.addEventListener('pause', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
});
videoPlayer.addEventListener('ended', () => {
    btnPlayCustom.innerHTML = '<i class="fa-solid fa-play"></i> Play';
});
