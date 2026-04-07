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

// ── Browser TTS (Web Speech API) ─────────────────────────────────────────────
// Runs 100% client-side — no gTTS, no server round-trip, works on all HTTPS
// deployments (Render, Vercel, etc.) with zero external API calls.

const LANG_TTS_MAP = {
    'Hindi':   'hi-IN',
    'Telugu':  'te-IN',
    'Urdu':    'ur-PK',
    'English': 'en-US'
};

function speakText(text, language) {
    if (!window.speechSynthesis) return;

    // Strip any leftover LEAD_CAPTURE JSON before speaking
    const cleanText = text.split('LEAD_CAPTURE:')[0].trim();
    if (!cleanText) return;

    window.speechSynthesis.cancel(); // stop any ongoing speech

    const utterance = new SpeechSynthesisUtterance(cleanText);
    utterance.lang  = LANG_TTS_MAP[language] || 'hi-IN';
    utterance.rate  = 1.05;
    utterance.pitch = 1.0;

    // Some browsers need voices to load first
    const voices = window.speechSynthesis.getVoices();
    if (voices.length > 0) {
        // Try to find a matching voice; fall back to default
        const match = voices.find(v => v.lang.startsWith(utterance.lang.split('-')[0]));
        if (match) utterance.voice = match;
    }

    window.speechSynthesis.speak(utterance);
}

// Ensure voice list is loaded (Chrome requires this)
window.speechSynthesis.onvoiceschanged = () => window.speechSynthesis.getVoices();

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
            // Speak the reply using browser TTS
            speakText(data.reply, languageSelect.value);
        }

        if (data.completed) {
            window.speechSynthesis.cancel();
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

// ── Send Button / Enter Key ───────────────────────────────────────────────────

sendBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (!text) return;
    appendMessage(text, 'user');
    textInput.value = '';
    sendChatRequest(text);
});

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') sendBtn.click();
});

// ── Microphone / Voice Input ──────────────────────────────────────────────────

async function setupMic() {
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
    // Stop bot from speaking when user wants to talk
    window.speechSynthesis.cancel();

    if (!mediaRecorder) {
        await setupMic();
        if (!mediaRecorder) return;
    }

    if (isRecording) {
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        recordingIndicator.style.display = 'none';
    } else {
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('recording');
        recordingIndicator.style.display = 'flex';
    }
});
