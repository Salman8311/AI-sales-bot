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
let currentAudio = null;

// Audio context fix for browsers
const AudioContext = window.AudioContext || window.webkitAudioContext;

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

async function playAudioBase64(base64Str) {
    if (!base64Str) return;
    if (currentAudio) {
        currentAudio.pause();
    }
    const audioUrl = `data:audio/mp3;base64,${base64Str}`;
    currentAudio = new Audio(audioUrl);
    await currentAudio.play().catch(e => console.error("Audio playback error:", e));
}

async function sendChatRequest(userText) {
    messages.push({ role: "user", content: userText });
    
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
            messages.push({ role: "assistant", content: data.reply });
            appendMessage(data.reply, 'bot');
            if (data.audio_base64) {
                playAudioBase64(data.audio_base64);
            }
        }
        
        if (data.completed) {
            appendMessage("🎉 Lead Captured Successfully! We will contact you soon.", 'bot');
            textInput.disabled = true;
            micBtn.disabled = true;
            sendBtn.disabled = true;
        }

    } catch (error) {
        removeTyping();
        appendMessage("Sorry, an error occurred. Please try again.", 'bot');
        console.error(error);
    }
}

// Ensure the first message triggers audio play and handles state
sendBtn.addEventListener('click', () => {
    const text = textInput.value.trim();
    if (text) {
        appendMessage(text, 'user');
        textInput.value = '';
        sendChatRequest(text);
    }
});

textInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
        sendBtn.click();
    }
});

// Voice Recording Logic
async function setupAudio() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
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
            alert("Please allow microphone access to use voice chat.");
        }
    }
}

async function sendAudioForTranscription(audioBlob) {
    const formData = new FormData();
    formData.append("file", audioBlob, "voice.webm");
    formData.append("language", languageSelect.value);

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
            appendMessage("(Could not hear anything clear)", 'user');
        }
    } catch (e) {
        removeTyping();
        console.error("Transcription error:", e);
    }
}

micBtn.addEventListener('click', async () => {
    if (!mediaRecorder) {
        await setupAudio();
        if (!mediaRecorder) return;
    }

    if (isRecording) {
        // Stop recording
        mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.remove('recording');
        recordingIndicator.style.display = 'none';
    } else {
        // Start recording
        if (currentAudio) currentAudio.pause(); // stop bot if it was speaking
        audioChunks = [];
        mediaRecorder.start();
        isRecording = true;
        micBtn.classList.add('recording');
        recordingIndicator.style.display = 'flex';
    }
});
