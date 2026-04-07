const chatContainer = document.getElementById('chat-container');
const textInput = document.getElementById('text-input');
const sendBtn = document.getElementById('send-btn');
const micBtn = document.getElementById('mic-btn');
const languageSelect = document.getElementById('language-select');
const recordingIndicator = document.getElementById('recording-indicator');

let messages = [];
let isRecording = false;
let mediaRecorder = null;
let audioChunks = [];

// ── Audio Engine ─────────────────────────────────────────────────────────────
// We use Web Audio API (AudioContext) to decode and play the bot's TTS audio.
// This is immune to browser autoplay restrictions because the AudioContext is
// created (and resumed) synchronously inside a user-gesture handler.

let audioCtx = null;
let currentSource = null;  // currently playing AudioBufferSourceNode

/**
 * Create (or resume) the AudioContext.
 * Must be called from inside a user-gesture event handler.
 */
function unlockAudio() {
    if (!audioCtx) {
        audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    }
    if (audioCtx.state === 'suspended') {
        audioCtx.resume();
    }
}

/**
 * Decode a base64 MP3 string and play it via AudioContext.
 * Stops any currently playing audio first.
 */
async function playAudioBase64(base64Str) {
    if (!base64Str || !audioCtx) return;

    // Stop previous playback
    if (currentSource) {
        try { currentSource.stop(); } catch (_) {}
        currentSource = null;
    }

    try {
        // base64 → ArrayBuffer
        const binary = atob(base64Str);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);

        // Decode MP3 → AudioBuffer → play
        const audioBuffer = await audioCtx.decodeAudioData(bytes.buffer);
        const source = audioCtx.createBufferSource();
        source.buffer = audioBuffer;
        source.connect(audioCtx.destination);
        source.start(0);
        currentSource = source;
    } catch (e) {
        console.error('Audio playback error:', e);
    }
}

// ── UI Helpers ────────────────────────────────────────────────────────────────

function appendMessage(text, sender) {
    const msgDiv = document.createElement('div');
    msgDiv.className = `message ${sender}-msg`;
    msgDiv.innerText = text;
    chatContainer.appendChild(msgDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTyping() {
    const typingDiv = document.createElement('div');
    typingDiv.className = 'message bot-msg typing-msg';
    typingDiv.id = 'typing-indicator';
    typingDiv.innerHTML = `
        <div class="typing-indicator">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    `;
    chatContainer.appendChild(typingDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function removeTyping() {
    const indicator = document.getElementById('typing-indicator');
    if (indicator) indicator.remove();
}

// ── Chat ──────────────────────────────────────────────────────────────────────

async function sendChatRequest(userText) {
    messages.push({ role: 'user', content: userText });
    showTyping();

    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                messages: messages,
                language: languageSelect.value
            })
        });
        const data = await response.json();
        removeTyping();

        if (data.reply) {
            messages.push({ role: 'assistant', content: data.reply });
            appendMessage(data.reply, 'bot');
            if (data.audio_base64) {
                playAudioBase64(data.audio_base64);
            }
        }

        if (data.completed) {
            appendMessage('🎉 Lead Captured Successfully! We will contact you soon.', 'bot');
            textInput.disabled = true;
            micBtn.disabled = true;
            sendBtn.disabled = true;
        }

    } catch (error) {
        removeTyping();
        appendMessage('Sorry, an error occurred. Please try again.', 'bot');
        console.error(error);
    }
}

// ── Send button / Enter key ───────────────────────────────────────────────────

sendBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (!text) return;

    // Unlock AudioContext synchronously inside user gesture
    unlockAudio();

    appendMessage(text, 'user');
    textInput.value = '';
    sendChatRequest(text);
});

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});

// ── Voice Recording ───────────────────────────────────────────────────────────

async function setupAudio() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        alert('Your browser does not support microphone access.');
        return;
    }
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);

        mediaRecorder.ondataavailable = e => {
            if (e.data.size > 0) audioChunks.push(e.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
            audioChunks = [];
            await sendAudioForTranscription(audioBlob);
        };
    } catch (err) {
        console.error('Microphone access denied', err);
        alert('Please allow microphone access to use voice chat.');
    }
}

async function sendAudioForTranscription(audioBlob) {
    const formData = new FormData();
    formData.append('file', audioBlob, 'voice.webm');
    formData.append('language', languageSelect.value);

    showTyping();
    try {
        const response = await fetch('/api/transcribe', {
            method: 'POST',
            body: formData
        });
        const data = await response.json();
        removeTyping();

        if (data.text && data.text.trim()) {
            appendMessage(data.text, 'user');
            sendChatRequest(data.text);
        } else {
            appendMessage('(Could not hear anything clearly)', 'user');
        }
    } catch (e) {
        removeTyping();
        console.error('Transcription error:', e);
    }
}

micBtn.addEventListener('click', async () => {
    // Unlock AudioContext synchronously inside user gesture
    unlockAudio();

    if (!mediaRecorder) {
        await setupAudio();
        if (!mediaRecorder) return;
    }

    if (isRecording) {
        // Stop recording — onstop handler will transcribe and reply
        if (currentSource) {
            try { currentSource.stop(); } catch (_) {} // stop bot speaking
            currentSource = null;
        }
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        recordingIndicator.style.display = 'none';
    } else {
        // Start recording
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('recording');
        recordingIndicator.style.display = 'flex';
    }
});
