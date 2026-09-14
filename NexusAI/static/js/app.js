/* ==========================================================================
   NEXUSAI MASTER JAVASCRIPT CONTROLLER
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
    initSidebarToggle();
    initVoiceRecognition();
    initThemeToggle();
    initGlobalListeners();
});

// ==========================================
// 1. SIDEBAR TOGGLE ENGINE (3-LINE HAMBURGER)
// ==========================================
function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebarToggleBtn');
    if (!toggleBtn) return;

    const savedState = localStorage.getItem('nexusai_sidebar_collapsed');
    if (savedState === 'true') {
        document.body.classList.add('sidebar-collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        document.body.classList.toggle('sidebar-collapsed');
        const isCollapsed = document.body.classList.contains('sidebar-collapsed');
        localStorage.setItem('nexusai_sidebar_collapsed', isCollapsed);
    });
}

// ==========================================
// 1. VOICE COMMANDS ENGINE (Web Speech API)
// ==========================================
// ==========================================
// 1. CHATGPT-STYLE VOICE ASSISTANT CONTROLLER
// ==========================================
let activeSpeechRecognition = null;
let networkRetryCount = 0;
const MAX_NETWORK_RETRIES = 2;
let isVoiceListening = false;
let isProcessingVoiceQuery = false;
let currentSpeechUtterance = null;
let speechSilenceTimer = null;
let voiceInitialized = false;

function initVoiceRecognition() {
    if (voiceInitialized) return;
    voiceInitialized = true;

    document.querySelectorAll('#voiceMicBtn, .btn-mic-icon').forEach(btn => {
        btn.onclick = (e) => {
            e.preventDefault();
            e.stopPropagation();
            openVoiceAssistant();
        };
    });

    const modalInput = document.getElementById('voiceModalTextInput');
    if (modalInput) {
        modalInput.onkeypress = (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitVoiceModalQuery();
            }
        };
    }
}

async function requestMicrophonePermission() {
    if (navigator.permissions && navigator.permissions.query) {
        try {
            const status = await navigator.permissions.query({ name: 'microphone' });
            if (status.state === 'granted') {
                return true;
            }
        } catch (e) {
            // Fallthrough to getUserMedia if query not supported for microphone
        }
    }

    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            stream.getTracks().forEach(track => track.stop());
            // Allow audio device hardware driver to stabilize after track release
            await new Promise(r => setTimeout(r, 250));
            return true;
        } catch (err) {
            console.warn('Microphone permission error:', err);
            return false;
        }
    }
    return true;
}

async function openVoiceAssistant() {
    const modal = document.getElementById('voiceAssistantModal');
    if (!modal) return;

    modal.style.display = 'flex';
    document.getElementById('voiceTranscriptText').innerHTML = '<i>"Listening... Speak your query to NexusAI Voice Bot"</i>';
    
    const resBox = document.getElementById('voiceAiResponseText');
    if (resBox) {
        resBox.style.display = 'none';
        resBox.innerText = '';
    }

    const fallback = document.getElementById('voiceFallbackContainer');
    if (fallback) fallback.style.display = 'none';

    updateVoiceStatusBadge('Checking Microphone Access...', 'var(--accent-cyan)', 'bi-mic-fill');

    const hasMicPermission = await requestMicrophonePermission();
    if (!hasMicPermission) {
        updateVoiceStatusBadge('Mic Access Blocked', 'var(--accent-rose)', 'bi-mic-mute-fill');
        document.getElementById('voiceTranscriptText').innerHTML = '<span style="color:var(--accent-rose);">Microphone access blocked. Click the lock icon in the browser URL bar to enable microphone, or type below:</span>';
        showVoiceFallbackInput();
        return;
    }

    startVoiceRecognitionEngine();
}

function closeVoiceAssistant() {
    const modal = document.getElementById('voiceAssistantModal');
    if (modal) modal.style.display = 'none';

    if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
    stopVoiceRecognitionEngine();
    if (window.speechSynthesis) {
        window.speechSynthesis.cancel();
    }
}

function updateVoiceStatusBadge(statusText, colorStr, iconClass) {
    const badge = document.getElementById('voiceStatusBadge');
    if (badge) {
        badge.style.color = colorStr;
        badge.innerHTML = `<i class="bi ${iconClass}" style="margin-right:6px;"></i> ${statusText}`;
    }
}

function showVoiceFallbackInput() {
    const container = document.getElementById('voiceFallbackContainer');
    if (container) container.style.display = 'flex';
}

function startVoiceRecognitionEngine() {
    if (window.isSecureContext === false) {
        updateVoiceStatusBadge('Insecure Connection', 'var(--accent-rose)', 'bi-shield-slash-fill');
        document.getElementById('voiceTranscriptText').innerHTML = '<span style="color:var(--accent-rose);">Voice input requires a secure connection (localhost or HTTPS). Please type below:</span>';
        showVoiceFallbackInput();
        return;
    }

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        updateVoiceStatusBadge('Browser Not Supported', 'var(--accent-rose)', 'bi-exclamation-triangle-fill');
        document.getElementById('voiceTranscriptText').innerText = '"Web Speech API is not supported by your browser. Type your query below:"';
        showVoiceFallbackInput();
        return;
    }

    stopVoiceRecognitionEngine();

    try {
        isProcessingVoiceQuery = false;
        activeSpeechRecognition = new SpeechRecognition();
        activeSpeechRecognition.continuous = false;
        activeSpeechRecognition.interimResults = true;
        activeSpeechRecognition.lang = 'en-US';

        let capturedText = '';

        activeSpeechRecognition.onstart = () => {
            isVoiceListening = true;
            networkRetryCount = 0;
            capturedText = '';
            updateVoiceStatusBadge('Listening... Speak Now', 'var(--accent-cyan)', 'bi-mic-fill');
            const orb = document.getElementById('voiceOrb');
            if (orb) orb.style.background = 'radial-gradient(circle, #06b6d4 0%, #3b82f6 70%, #000 100%)';

            // Safety silence timeout: stop after 10s if no speech is detected
            if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
            speechSilenceTimer = setTimeout(() => {
                if (isVoiceListening && !capturedText) {
                    stopVoiceRecognitionEngine();
                    updateVoiceStatusBadge('No speech detected. Tap Orb to try again', 'var(--accent-amber)', 'bi-mic-fill');
                    showVoiceFallbackInput();
                }
            }, 10000);
        };

        activeSpeechRecognition.onresult = (event) => {
            if (speechSilenceTimer) clearTimeout(speechSilenceTimer);

            let interimTranscript = '';
            let finalTranscript = '';

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const text = event.results[i][0].transcript;
                if (event.results[i].isFinal) {
                    finalTranscript += text;
                } else {
                    interimTranscript += text;
                }
            }

            const currentText = (finalTranscript || interimTranscript).trim();
            if (currentText) {
                capturedText = currentText;
                document.getElementById('voiceTranscriptText').innerHTML = `<b>🗣️ You:</b> "${escapeHtml(currentText)}"`;
            }

            if (finalTranscript && finalTranscript.trim() && !isProcessingVoiceQuery) {
                isProcessingVoiceQuery = true;
                const queryToSubmit = finalTranscript.trim();
                capturedText = '';
                stopVoiceRecognitionEngine();
                processVoiceQuery(queryToSubmit);
            }
        };

        activeSpeechRecognition.onerror = (event) => {
            console.warn('Speech recognition error event:', event);
            if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
            isVoiceListening = false;

            if (event.error === 'network') {
                if (networkRetryCount < MAX_NETWORK_RETRIES) {
                    networkRetryCount++;
                    updateVoiceStatusBadge(`Connecting... (${networkRetryCount}/${MAX_NETWORK_RETRIES})`, 'var(--accent-amber)', 'bi-arrow-repeat spin');
                    setTimeout(() => {
                        if (!isVoiceListening && !isProcessingVoiceQuery) {
                            startVoiceRecognitionEngine();
                        }
                    }, 1200);
                    return;
                } else {
                    updateVoiceStatusBadge('Voice Input Ready - Type or Tap Orb', 'var(--accent-cyan)', 'bi-keyboard-fill');
                    document.getElementById('voiceTranscriptText').innerHTML = '<span>Type your voice query below or tap Orb to speak:</span>';
                    showVoiceFallbackInput();
                    return;
                }
            }

            if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
                updateVoiceStatusBadge('Mic Access Blocked', 'var(--accent-rose)', 'bi-mic-mute-fill');
                document.getElementById('voiceTranscriptText').innerHTML = '<span style="color:var(--accent-rose);">Microphone permission denied. Please allow mic access.</span>';
                showVoiceFallbackInput();
            } else if (event.error === 'no-speech') {
                updateVoiceStatusBadge('Didn\'t catch that. Try again.', 'var(--accent-amber)', 'bi-mic-fill');
                showVoiceFallbackInput();
            } else if (event.error === 'audio-capture') {
                updateVoiceStatusBadge('No microphone found.', 'var(--accent-rose)', 'bi-mic-mute-fill');
                showVoiceFallbackInput();
            } else if (event.error === 'aborted') {
                updateVoiceStatusBadge('Voice Input Paused', 'var(--text-muted)', 'bi-mic-mute-fill');
                showVoiceFallbackInput();
            } else {
                updateVoiceStatusBadge(`Speech Ready`, 'var(--accent-cyan)', 'bi-mic-fill');
                showVoiceFallbackInput();
            }
        };

        activeSpeechRecognition.onend = () => {
            if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
            isVoiceListening = false;
            const orb = document.getElementById('voiceOrb');
            if (orb) orb.style.background = 'radial-gradient(circle, #3b82f6 0%, #1d4ed8 70%, #000 100%)';

            // If captured text exists but query hasn't been submitted yet, submit now
            if (capturedText && capturedText.trim() && !isProcessingVoiceQuery) {
                isProcessingVoiceQuery = true;
                const queryToSubmit = capturedText.trim();
                capturedText = '';
                processVoiceQuery(queryToSubmit);
            }
        };

        activeSpeechRecognition.start();
    } catch (e) {
        console.warn('Speech recognition exception:', e);
        showVoiceFallbackInput();
    }
}

function stopVoiceRecognitionEngine() {
    if (speechSilenceTimer) clearTimeout(speechSilenceTimer);
    if (activeSpeechRecognition) {
        try {
            activeSpeechRecognition.onstart = null;
            activeSpeechRecognition.onresult = null;
            activeSpeechRecognition.onerror = null;
            activeSpeechRecognition.onend = null;
            activeSpeechRecognition.stop();
        } catch(e){}
        activeSpeechRecognition = null;
    }
    isVoiceListening = false;
}

function toggleVoiceListeningState() {
    if (isVoiceListening) {
        stopVoiceRecognitionEngine();
        updateVoiceStatusBadge('Voice Paused. Click Orb to Resume', 'var(--text-muted)', 'bi-mic-mute-fill');
    } else {
        if (window.speechSynthesis) window.speechSynthesis.cancel();
        startVoiceRecognitionEngine();
    }
}

async function submitVoiceModalQuery() {
    const input = document.getElementById('voiceModalTextInput');
    if (!input || !input.value.trim()) return;
    const text = input.value.trim();
    input.value = '';
    document.getElementById('voiceTranscriptText').innerHTML = `<b>🗣️ You:</b> "${escapeHtml(text)}"`;
    await processVoiceQuery(text);
}

async function processVoiceQuery(queryText) {
    stopVoiceRecognitionEngine();
    updateVoiceStatusBadge('NexusAI Thinking...', 'var(--accent-amber)', 'bi-cpu spin');

    try {
        const res = await fetch('/api/ai/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: queryText, is_voice: true })
        });
        const data = await res.json();

        const answerText = data.insight || data.reply || "I have analyzed your request.";

        const responseBox = document.getElementById('voiceAiResponseText');
        if (responseBox) {
            responseBox.style.display = 'block';
            responseBox.innerText = answerText;
        }

        updateVoiceStatusBadge('NexusAI Speaking...', 'var(--accent-emerald)', 'bi-volume-up-fill');
        speakResponseOutLoud(answerText);
    } catch (e) {
        console.error(e);
        updateVoiceStatusBadge('Error Processing Voice Query', 'var(--accent-rose)', 'bi-exclamation-triangle-fill');
    }
}

function speakResponseOutLoud(text) {
    if (!('speechSynthesis' in window)) return;

    window.speechSynthesis.cancel();
    const cleanText = text.replace(/[*#_`]/g, '').slice(0, 350);
    currentSpeechUtterance = new SpeechSynthesisUtterance(cleanText);
    currentSpeechUtterance.rate = 1.0;
    currentSpeechUtterance.pitch = 1.0;

    currentSpeechUtterance.onend = () => {
        updateVoiceStatusBadge('NexusAI Finished Speaking', 'var(--accent-cyan)', 'bi-check-circle-fill');
    };

    window.speechSynthesis.speak(currentSpeechUtterance);
}

// ==========================================
// 2. THEME TOGGLE (DARK / LIGHT)
// ==========================================
function initThemeToggle() {
    const themeBtn = document.getElementById('themeToggleBtn');
    const savedTheme = localStorage.getItem('nexusai_theme');

    // Default to dark theme unless user explicitly chose light
    if (savedTheme === 'light') {
        document.body.classList.add('light-theme');
        if (themeBtn && themeBtn.querySelector('i')) themeBtn.querySelector('i').className = 'bi bi-moon-fill';
    } else {
        document.body.classList.remove('light-theme');
        if (themeBtn && themeBtn.querySelector('i')) themeBtn.querySelector('i').className = 'bi bi-sun-fill';
    }

    if (themeBtn) {
        themeBtn.addEventListener('click', () => {
            document.body.classList.toggle('light-theme');
            const isLight = document.body.classList.contains('light-theme');
            localStorage.setItem('nexusai_theme', isLight ? 'light' : 'dark');
            if (themeBtn.querySelector('i')) {
                themeBtn.querySelector('i').className = isLight ? 'bi bi-moon-fill' : 'bi bi-sun-fill';
            }
        });
    }
}

// ==========================================
// 3. AI ADVISOR HYBRID WORKSPACE & CHAT ENGINE
// ==========================================
let currentAdvisorChatId = null;

document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('advisorHistoryList')) {
        loadAdvisorChatHistory();

        const urlParams = new URLSearchParams(window.location.search);
        const chatId = urlParams.get('chat_id');
        if (chatId) {
            openAdvisorChat(chatId);
        }
    }
});

function renderMarkdownContent(rawText) {
    if (!rawText) return '';

    if (typeof marked !== 'undefined') {
        try {
            let parsed = marked.parse(rawText);
            const div = document.createElement('div');
            div.innerHTML = parsed;

            div.querySelectorAll('pre').forEach(pre => {
                const code = pre.querySelector('code');
                const langMatch = code ? code.className.match(/language-(\w+)/) : null;
                const lang = langMatch ? langMatch[1] : 'code';

                const wrapper = document.createElement('div');
                wrapper.className = 'code-block-wrapper';
                wrapper.innerHTML = `
                    <div class="code-block-header">
                        <span><i class="bi bi-code-slash"></i> ${lang}</span>
                        <button type="button" class="copy-code-btn" onclick="copyCodeBlock(this)">
                            <i class="bi bi-clipboard"></i> Copy
                        </button>
                    </div>
                `;
                pre.parentNode.insertBefore(wrapper, pre);
                wrapper.appendChild(pre);
            });

            return div.innerHTML;
        } catch (e) {
            console.warn("Marked parse error:", e);
        }
    }

    return escapeHtml(rawText).replace(/\n/g, '<br>');
}

function copyCodeBlock(button) {
    const wrapper = button.closest('.code-block-wrapper');
    if (!wrapper) return;
    const code = wrapper.querySelector('code') || wrapper.querySelector('pre');
    if (!code) return;

    const text = code.innerText || code.textContent;
    navigator.clipboard.writeText(text).then(() => {
        button.innerHTML = `<i class="bi bi-check2" style="color:var(--accent-emerald);"></i> Copied!`;
        setTimeout(() => {
            button.innerHTML = `<i class="bi bi-clipboard"></i> Copy`;
        }, 2000);
    }).catch(err => {
        console.error("Failed to copy code:", err);
    });
}

function toggleAdvisorHeaderMenu(e) {
    if (e) e.stopPropagation();
    const menu = document.getElementById('advisorHeaderMenu');
    if (!menu) return;
    menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';
}

document.addEventListener('click', (e) => {
    const menu = document.getElementById('advisorHeaderMenu');
    if (menu && !menu.contains(e.target) && !e.target.closest('.btn-icon')) {
        menu.style.display = 'none';
    }
});

async function renameCurrentActiveChat() {
    if (!currentAdvisorChatId) return;
    const newTitle = prompt("Enter a new title for this conversation:");
    if (!newTitle || !newTitle.trim()) return;

    try {
        const res = await fetch(`/api/ai/chats/${currentAdvisorChatId}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle.trim() })
        });
        const data = await res.json();
        if (data.status === 'success') {
            const titleHeader = document.getElementById('currentChatTitle');
            if (titleHeader) titleHeader.innerText = data.title;
            loadAdvisorChatHistory();
        }
    } catch (e) {
        console.error("Error renaming chat:", e);
    }
}

const NEXUS_LOGO_SVG = (size = 18) => `
<svg viewBox="0 0 44 44" fill="none" xmlns="http://www.w3.org/2000/svg" style="width: ${size}px; height: ${size}px; vertical-align: middle; flex-shrink: 0;">
    <circle cx="22" cy="22" r="18" stroke="url(#nx_grad_${size}_1)" stroke-width="2" stroke-dasharray="8 4"/>
    <circle cx="22" cy="22" r="10" fill="url(#nx_grad_${size}_2)"/>
    <path d="M17 22L21 26L27 18" stroke="#ffffff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
    <defs>
        <linearGradient id="nx_grad_${size}_1" x1="0" y1="0" x2="44" y2="44" gradientUnits="userSpaceOnUse">
            <stop stop-color="#2563eb"/>
            <stop offset="0.5" stop-color="#3b82f6"/>
            <stop offset="1" stop-color="#4f46e5"/>
        </linearGradient>
        <linearGradient id="nx_grad_${size}_2" x1="12" y1="12" x2="32" y2="32" gradientUnits="userSpaceOnUse">
            <stop stop-color="#2563eb"/>
            <stop offset="1" stop-color="#4f46e5"/>
        </linearGradient>
    </defs>
</svg>
`;

let currentSelectedFile = null;

function triggerAdvisorFileUpload() {
    const fileInput = document.getElementById('advisorFileInput');
    if (fileInput) fileInput.click();
}

function handleAdvisorFileSelect(input) {
    if (!input.files || !input.files[0]) return;
    const file = input.files[0];

    const fname = file.name;
    const ext = fname.slice((fname.lastIndexOf(".") - 1 >>> 0) + 2).toLowerCase();
    const blacklisted = ['exe', 'bat', 'cmd', 'ps1', 'sh', 'py', 'js', 'vbs', 'msi', 'jar', 'dll', 'scr', 'php', 'rb', 'pl'];

    if (blacklisted.includes(ext)) {
        alert("Security Warning: Executable and script files (.exe, .bat, .ps1, .sh, .py, etc.) are strictly prohibited.");
        input.value = '';
        return;
    }

    if (file.size > 10 * 1024 * 1024) {
        alert("File size exceeds the maximum 10MB limit.");
        input.value = '';
        return;
    }

    const isImg = file.type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp', 'gif'].includes(ext);

    const reader = new FileReader();
    reader.onload = (e) => {
        if (isImg) {
            const img = new Image();
            img.onload = () => {
                let width = img.width;
                let height = img.height;
                const maxDim = 1200;
                if (width > maxDim || height > maxDim) {
                    if (width > height) {
                        height = Math.round((height * maxDim) / width);
                        width = maxDim;
                    } else {
                        width = Math.round((width * maxDim) / height);
                        height = maxDim;
                    }
                }
                const canvas = document.createElement('canvas');
                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, width, height);
                const dataUrl = canvas.toDataURL('image/jpeg', 0.85);
                const b64Data = dataUrl.split(',')[1];
                currentSelectedFile = {
                    name: fname,
                    mime_type: 'image/jpeg',
                    data: b64Data,
                    dataUrl: dataUrl,
                    isImage: true
                };
                showAdvisorFilePreview();
            };
            img.onerror = () => {
                const b64Data = e.target.result.split(',')[1];
                currentSelectedFile = {
                    name: fname,
                    mime_type: file.type || 'image/png',
                    data: b64Data,
                    dataUrl: e.target.result,
                    isImage: true
                };
                showAdvisorFilePreview();
            };
            img.src = e.target.result;
        } else {
            const b64Data = e.target.result.split(',')[1];
            currentSelectedFile = {
                name: fname,
                mime_type: file.type || 'application/octet-stream',
                data: b64Data,
                dataUrl: e.target.result,
                isImage: false
            };
            showAdvisorFilePreview();
        }
    };
    reader.readAsDataURL(file);
}

function showAdvisorFilePreview() {
    const bar = document.getElementById('advisorFilePreviewBar');
    if (!bar || !currentSelectedFile) return;

    let mediaHtml = '';
    if (currentSelectedFile.isImage) {
        mediaHtml = `<img src="${currentSelectedFile.dataUrl}" class="file-preview-thumb" alt="Preview">`;
    } else {
        mediaHtml = `<i class="bi bi-file-earmark-text" style="font-size:18px; color:var(--accent-cyan);"></i>`;
    }

    bar.innerHTML = `
        <div class="file-preview-chip">
            ${mediaHtml}
            <span>${escapeHtml(currentSelectedFile.name)}</span>
            <button type="button" class="file-preview-remove" onclick="removeAdvisorFilePreview()" title="Remove attachment">
                <i class="bi bi-x"></i>
            </button>
        </div>
    `;
    bar.style.display = 'block';
}

function removeAdvisorFilePreview() {
    currentSelectedFile = null;
    const input = document.getElementById('advisorFileInput');
    if (input) input.value = '';
    const bar = document.getElementById('advisorFilePreviewBar');
    if (bar) {
        bar.innerHTML = '';
        bar.style.display = 'none';
    }
}

async function loadAdvisorChatHistory() {
    const listContainer = document.getElementById('advisorHistoryList');
    if (!listContainer) return;

    try {
        const res = await fetch('/api/ai/chats');
        const data = await res.json();
        if (data.status !== 'success') return;

        const chatsGrouped = data.chats;
        let html = '';

        const categories = ['Today', 'Yesterday', 'Older'];
        let totalChats = 0;

        categories.forEach(cat => {
            const group = chatsGrouped[cat] || [];
            if (group.length > 0) {
                totalChats += group.length;
                const catLabel = (cat === 'Today') ? 'RECENTS' : cat.toUpperCase();
                html += `<div class="history-category-title">${catLabel}</div>`;
                group.forEach(chat => {
                    const isCurrent = (currentAdvisorChatId == chat.id);
                    html += `
                        <div class="history-chat-item ${isCurrent ? 'active' : ''}" onclick="openAdvisorChat(${chat.id})">
                            <div style="display:flex; align-items:center; gap:8px; overflow:hidden; flex:1;">
                                ${NEXUS_LOGO_SVG(15)}
                                <span class="item-title" title="${escapeHtml(chat.title)}">${escapeHtml(chat.title)}</span>
                            </div>
                            <button class="item-menu-btn" onclick="deleteAdvisorChat(${chat.id}, event)" title="Delete Chat">
                                <i class="bi bi-trash3"></i>
                            </button>
                        </div>
                    `;
                });
            }
        });

        if (totalChats === 0) {
            html = `<div style="font-size:12px; color:var(--text-muted); text-align:center; margin-top:20px;">No saved chats yet.</div>`;
        }

        listContainer.innerHTML = html;
    } catch (e) {
        console.error("Error loading chat history:", e);
    }
}

function renderEmptyState() {
    return `
        <div class="advisor-empty-state" id="advisorEmptyState">
            <div class="advisor-empty-icon" style="background: rgba(37, 99, 235, 0.08); border-color: rgba(37, 99, 235, 0.25);">
                ${NEXUS_LOGO_SVG(36)}
            </div>
            <div class="advisor-empty-title">How can I help you today?</div>
            <div class="advisor-empty-subtitle">
                I'm your NexusAI Business Employee. Ask me about your business metrics, or upload images and documents for analysis.
            </div>
            <div class="pill-chip-container">
                <button onclick="submitAiQuery('Why did sales decrease in North India?')" class="pill-chip-btn">
                    <i class="bi bi-graph-down-arrow" style="color: var(--accent-rose);"></i> Why did sales decrease?
                </button>
                <button onclick="submitAiQuery('What should I focus on today?')" class="pill-chip-btn">
                    <i class="bi bi-lightning-charge" style="color: var(--accent-amber);"></i> What should I focus on today?
                </button>
                <button onclick="submitAiQuery('Create invoice for ABC Technologies for ₹25,000 for website development.')" class="pill-chip-btn">
                    <i class="bi bi-file-earmark-plus" style="color: var(--accent-cyan);"></i> Create Invoice ₹25,000
                </button>
                <button onclick="submitAiQuery('Write a payment reminder for ABC Technologies')" class="pill-chip-btn">
                    <i class="bi bi-envelope" style="color: var(--accent-purple);"></i> Write Payment Reminder
                </button>
                <button onclick="submitAiQuery('Show low stock products')" class="pill-chip-btn">
                    <i class="bi bi-box-seam" style="color: var(--accent-emerald);"></i> Check Low Stock
                </button>
            </div>
        </div>
    `;
}

async function createNewChat() {
    try {
        const res = await fetch('/api/ai/chats/new', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            currentAdvisorChatId = data.chat.id;
            const titleHeader = document.getElementById('currentChatTitle');
            if (titleHeader) {
                titleHeader.innerText = data.chat.title;
            }

            const historyContainer = document.getElementById('chatHistory');
            if (historyContainer) {
                historyContainer.innerHTML = renderEmptyState();
            }

            loadAdvisorChatHistory();
        }
    } catch (e) {
        console.error("Error creating new chat:", e);
    }
}

async function openAdvisorChat(chatId) {
    if (!chatId) return;

    try {
        const res = await fetch(`/api/ai/chats/${chatId}`);
        const data = await res.json();
        if (data.status !== 'success') return;

        const chat = data.chat;
        currentAdvisorChatId = chat.id;

        const titleHeader = document.getElementById('currentChatTitle');
        if (titleHeader) {
            titleHeader.innerText = chat.title;
        }

        const historyContainer = document.getElementById('chatHistory');
        if (!historyContainer) return;

        if (chat.messages.length === 0) {
            historyContainer.innerHTML = renderEmptyState();
        } else {
            historyContainer.innerHTML = '';
            chat.messages.forEach(msg => {
                const isUser = msg.sender === 'user';
                const bubble = document.createElement('div');
                bubble.className = isUser ? 'chat-bubble-user' : 'chat-bubble-ai';

                let extra = msg.extra_data || {};

                if (isUser) {
                    let attachBadge = '';
                    if (extra.attachment) {
                        attachBadge = `<div class="attachment-badge"><i class="bi bi-paperclip"></i> ${escapeHtml(extra.attachment.name)}</div>`;
                    }
                    bubble.innerHTML = `${attachBadge}<div>${escapeHtml(msg.content)}</div>`;
                } else {
                    let actionHtml = '';
                    if (extra.action_url) {
                        actionHtml = `<div style="margin-top:12px;"><a href="${extra.action_url}" class="btn btn-primary btn-sm"><i class="bi bi-download"></i> ${extra.action_label || 'Execute Action'}</a></div>`;
                    }
                    let emailHtml = '';
                    if (extra.email_data) {
                        emailHtml = `
                            <div style="margin-top:12px; padding:12px; background:var(--bg-card-hover); border-radius:var(--radius-sm); border:1px solid var(--border-glass);">
                                <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">Subject: ${escapeHtml(extra.email_data.subject)}</div>
                                <div style="font-size:12px; color:var(--text-secondary); white-space:pre-line; max-height:150px; overflow-y:auto; font-family:var(--font-mono);">${escapeHtml(extra.email_data.body)}</div>
                            </div>
                        `;
                    }

                    bubble.innerHTML = `
                        <div class="ai-message-header">
                            <span class="ai-message-author" style="display:flex; align-items:center; gap:6px;">
                                ${NEXUS_LOGO_SVG(18)} NexusAI Advisor
                            </span>
                            <span class="ai-message-tool">${extra.tool_used || 'Nexus AI Engine'}</span>
                        </div>
                        <div class="ai-markdown-content">${renderMarkdownContent(msg.content)}</div>
                        ${emailHtml}
                        ${actionHtml}
                    `;
                }
                historyContainer.appendChild(bubble);
            });
            historyContainer.scrollTop = historyContainer.scrollHeight;
        }

        loadAdvisorChatHistory();
    } catch (e) {
        console.error("Error opening chat:", e);
    }
}

async function deleteAdvisorChat(chatId, event) {
    if (event) event.stopPropagation();
    if (!confirm("Are you sure you want to delete this chat conversation?")) return;

    try {
        const res = await fetch(`/api/ai/chats/${chatId}`, { method: 'DELETE' });
        const data = await res.json();
        if (data.status === 'success') {
            if (currentAdvisorChatId == chatId) {
                createNewChat();
            } else {
                loadAdvisorChatHistory();
            }
        }
    } catch (e) {
        console.error("Error deleting chat:", e);
    }
}

function deleteCurrentActiveChat() {
    if (currentAdvisorChatId) {
        deleteAdvisorChat(currentAdvisorChatId, null);
    } else {
        createNewChat();
    }
}

async function submitAiQuery(queryText) {
    const fileToSend = currentSelectedFile;
    const promptText = queryText || (document.getElementById('aiQueryInput') ? document.getElementById('aiQueryInput').value : '');

    if (!promptText.trim() && !fileToSend) return;

    const historyContainer = document.getElementById('chatHistory');
    if (!historyContainer) {
        window.location.href = `/ai?q=${encodeURIComponent(promptText)}`;
        return;
    }

    // Hide empty state if present
    const emptyState = document.getElementById('advisorEmptyState');
    if (emptyState) emptyState.remove();

    // Clear input field and file preview
    if (document.getElementById('aiQueryInput')) {
        document.getElementById('aiQueryInput').value = '';
    }
    removeAdvisorFilePreview();

    // 1. Append User Message
    const userBubble = document.createElement('div');
    userBubble.className = 'chat-bubble-user';
    let attachBadge = '';
    if (fileToSend) {
        attachBadge = `<div class="attachment-badge"><i class="bi bi-paperclip"></i> ${escapeHtml(fileToSend.name)}</div>`;
    }
    userBubble.innerHTML = `${attachBadge}<div>${escapeHtml(promptText || 'Describe and analyze the attached file.')}</div>`;
    historyContainer.appendChild(userBubble);
    historyContainer.scrollTop = historyContainer.scrollHeight;

    // 2. Append Loading Indicator
    const loadingBubble = document.createElement('div');
    loadingBubble.className = 'chat-bubble-ai';
    loadingBubble.id = 'aiThinkingBubble';
    loadingBubble.innerHTML = `<div style="font-size:13px; color:var(--accent-cyan); display:flex; align-items:center; gap:8px;"><i class="bi bi-cpu spin"></i> AI Agent analyzing input & processing request...</div>`;
    historyContainer.appendChild(loadingBubble);
    historyContainer.scrollTop = historyContainer.scrollHeight;

    try {
        const payload = {
            query: promptText,
            chat_id: currentAdvisorChatId
        };
        if (fileToSend) {
            payload.file = {
                name: fileToSend.name,
                mime_type: fileToSend.mime_type,
                data: fileToSend.data
            };
        }

        const response = await fetch('/api/ai/query', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();

        // Handle error responses cleanly
        if (!response.ok || data.error) {
            const loader = document.getElementById('aiThinkingBubble');
            if (loader) {
                loader.innerHTML = `<div style="color:var(--accent-rose); padding:8px 0;"><i class="bi bi-exclamation-triangle-fill"></i> ${escapeHtml(data.error || 'An error occurred while processing your request.')}</div>`;
            }
            return;
        }

        if (data.chat_id) {
            currentAdvisorChatId = data.chat_id;
        }
        if (data.chat_title) {
            const titleHeader = document.getElementById('currentChatTitle');
            if (titleHeader) {
                titleHeader.innerText = data.chat_title;
            }
        }
        loadAdvisorChatHistory();

        // Remove loading
        const loader = document.getElementById('aiThinkingBubble');
        if (loader) loader.remove();

        // 3. Append Structured AI Response
        const aiBubble = document.createElement('div');
        aiBubble.className = 'chat-bubble-ai';

        let actionHtml = '';
        if (data.action_url) {
            actionHtml = `<div style="margin-top:12px;"><a href="${data.action_url}" class="btn btn-primary btn-sm"><i class="bi bi-download"></i> ${data.action_label || 'Execute Action'}</a></div>`;
        }

        let emailHtml = '';
        if (data.email_data) {
            emailHtml = `
                <div style="margin-top:12px; padding:12px; background:var(--bg-card-hover); border-radius:var(--radius-sm); border:1px solid var(--border-glass);">
                    <div style="font-weight:700; font-size:13px; color:var(--text-primary); margin-bottom:4px;">Subject: ${escapeHtml(data.email_data.subject)}</div>
                    <div style="font-size:12px; color:var(--text-secondary); white-space:pre-line; max-height:150px; overflow-y:auto; font-family:var(--font-mono);">${escapeHtml(data.email_data.body)}</div>
                </div>
            `;
        }

        let fullResponseText = '';
        if (data.reply) {
            fullResponseText = data.reply;
        } else {
            let parts = [];
            if (data.insight) parts.push(data.insight);
            if (data.evidence) parts.push(`\n📊 Data & Evidence:\n${data.evidence}`);
            if (data.recommendation) parts.push(`\n🎯 Recommendations:\n${data.recommendation}`);
            if (data.action && !data.action.includes('How else can I help') && !data.action.includes('Optimized')) parts.push(`\n⚡ Action:\n${data.action}`);
            fullResponseText = parts.join('\n');
        }

        aiBubble.innerHTML = `
            <div class="ai-message-header">
                <span class="ai-message-author" style="display:flex; align-items:center; gap:6px;">
                    ${NEXUS_LOGO_SVG(18)} NexusAI Advisor
                </span>
                <span class="ai-message-tool">${data.tool_used || 'Nexus AI Engine'}</span>
            </div>
            <div class="ai-markdown-content">${renderMarkdownContent(fullResponseText)}</div>
            ${emailHtml}
            ${actionHtml}
        `;
        historyContainer.appendChild(aiBubble);
        historyContainer.scrollTop = historyContainer.scrollHeight;
    } catch (err) {
        console.error(err);
        const loader = document.getElementById('aiThinkingBubble');
        if (loader) loader.innerHTML = `<div style="color:var(--accent-rose);"><i class="bi bi-exclamation-triangle"></i> AI Service temporarily unavailable. Please try again.</div>`;
    }
}

// ==========================================
// 4. DEMO LOGIN TRIGGER
// ==========================================
async function triggerDemoLogin() {
    try {
        const res = await fetch('/api/auth/demo-login', { method: 'POST' });
        const data = await res.json();
        if (data.status === 'success') {
            window.location.href = data.redirect;
        } else {
            alert(data.message || 'Demo login failed.');
        }
    } catch (e) {
        console.error(e);
    }
}

// ==========================================
// 5. GLOBAL LISTENERS & MODALS
// ==========================================
function initGlobalListeners() {
    const aiForm = document.getElementById('aiQueryForm');
    if (aiForm) {
        aiForm.addEventListener('submit', (e) => {
            e.preventDefault();
            const input = document.getElementById('aiQueryInput');
            if (input && input.value.trim()) {
                const query = input.value.trim();
                input.value = '';
                submitAiQuery(query);
            }
        });
    }

    const globalSearchInput = document.getElementById('globalSearchInput');
    if (globalSearchInput) {
        globalSearchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                submitAiQuery(globalSearchInput.value);
            }
        });
    }

    // Auto-fill query parameter if present in URL (?q=...)
    const urlParams = new URLSearchParams(window.location.search);
    const q = urlParams.get('q');
    if (q && document.getElementById('chatHistory')) {
        submitAiQuery(q);
    }
}

// Utility escape HTML
function escapeHtml(text) {
    if (!text) return '';
    return text.toString()
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// ==========================================
// 6. TOPBAR FLOATING MENU TOGGLES
// ==========================================
function toggleMenuById(e, menuId, menuWidth) {
    if (e) e.stopPropagation();

    const threeDotsMenu = document.getElementById('threeDotsDropdownMenu');
    const profileMenu = document.getElementById('profileDropdownMenu');

    if (menuId !== 'threeDotsDropdownMenu' && threeDotsMenu) threeDotsMenu.style.display = 'none';
    if (menuId !== 'profileDropdownMenu' && profileMenu) profileMenu.style.display = 'none';

    const menu = document.getElementById(menuId);
    if (!menu) return;

    if (menu.style.display === 'block') {
        menu.style.display = 'none';
        return;
    }

    const button = e.currentTarget || e.target;
    const rect = button.getBoundingClientRect();

    let top = rect.bottom + 8;
    let left = rect.right - menuWidth;

    if (left < 10) left = rect.left;
    if (top + 200 > window.innerHeight) top = rect.top - 200;

    menu.style.top = top + 'px';
    menu.style.left = left + 'px';
    menu.style.display = 'block';
}

function toggleThreeDotsMenu(e) {
    toggleMenuById(e, 'threeDotsDropdownMenu', 180);
}

function toggleProfileMenu(e) {
    toggleMenuById(e, 'profileDropdownMenu', 200);
}

document.addEventListener('click', (e) => {
    const threeDotsMenu = document.getElementById('threeDotsDropdownMenu');
    const profileMenu = document.getElementById('profileDropdownMenu');

    if (threeDotsMenu && !threeDotsMenu.contains(e.target) && !e.target.closest('.btn-icon-circle-3dots')) {
        threeDotsMenu.style.display = 'none';
    }
    if (profileMenu && !profileMenu.contains(e.target) && !e.target.closest('.topbar-user-avatar')) {
        profileMenu.style.display = 'none';
    }
});
