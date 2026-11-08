document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('userInput');
    const scroller = document.getElementById('messages');
    const thread = document.getElementById('thread');
    const welcome = document.getElementById('welcome');
    const sendBtn = document.getElementById('sendBtn');
    const newChatBtn = document.getElementById('newChatBtn');

    if (!input || !scroller || !thread || !sendBtn) return;

    let busy = false;

    // ---------- Safe markdown rendering ----------
    // All text is HTML-escaped first; only the tags generated below can appear in the page.
    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
    }

    function inline(text) {
        return text
            .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(\S(?:[^*\n]*\S)?)\*/g, '<em>$1</em>')
            .replace(/`([^`]+)`/g, '<code>$1</code>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
                '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');
    }

    function renderMarkdown(text) {
        const lines = escapeHtml(text).replace(/\r/g, '').split('\n');
        const out = [];
        let list = null;
        let para = [];

        const flushPara = () => {
            if (para.length) {
                out.push('<p>' + para.map(inline).join('<br>') + '</p>');
                para = [];
            }
        };
        const closeList = () => {
            if (list) {
                out.push('</' + list + '>');
                list = null;
            }
        };

        for (const line of lines) {
            const ul = line.match(/^\s*[*-]\s+(.*)$/);
            const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
            if (ul || ol) {
                flushPara();
                const type = ul ? 'ul' : 'ol';
                if (list !== type) {
                    closeList();
                    out.push('<' + type + '>');
                    list = type;
                }
                out.push('<li>' + inline((ul || ol)[1]) + '</li>');
            } else if (line.trim() === '') {
                flushPara();
                closeList();
            } else {
                closeList();
                para.push(line);
            }
        }
        flushPara();
        closeList();
        return out.join('');
    }

    // ---------- Chat helpers ----------
    function scrollToBottom() {
        scroller.scrollTop = scroller.scrollHeight;
    }

    function createRow(role) {
        const row = document.createElement('div');
        row.className = 'message-row ' + role;
        const avatar = document.createElement('div');
        avatar.className = 'avatar';
        avatar.textContent = role === 'user' ? 'U' : 'AI';
        const content = document.createElement('div');
        content.className = 'message-content';
        row.append(avatar, content);
        thread.appendChild(row);
        return { row, content };
    }

    function addUserMessage(text) {
        createRow('user').content.textContent = text;
        scrollToBottom();
    }

    function addAssistantMessage(text, isNotice) {
        const { content } = createRow('assistant');
        content.innerHTML = renderMarkdown(text);
        if (isNotice) content.classList.add('notice');
        scrollToBottom();
    }

    function addTyping() {
        const { row, content } = createRow('assistant');
        content.innerHTML = '<div class="typing"><span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span></div><div class="typing-note"></div>';
        scrollToBottom();
        return { row, note: content.querySelector('.typing-note') };
    }

    function setBusy(value) {
        busy = value;
        sendBtn.disabled = value;
        if (newChatBtn) newChatBtn.disabled = value;
    }

    function autoResize() {
        input.style.height = 'auto';
        input.style.height = Math.min(input.scrollHeight, 200) + 'px';
    }

    // ---------- Sending ----------
    async function sendMessage() {
        const text = input.value.trim();
        if (!text || busy) return;

        setBusy(true);
        if (welcome) welcome.hidden = true;
        addUserMessage(text);
        input.value = '';
        autoResize();

        const typing = addTyping();
        const wakeTimer = setTimeout(() => {
            typing.note.textContent = 'Waking up the server (free hosting can take up to a minute)...';
        }, 6000);

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });
            const raw = await res.text();
            let data = null;
            try { data = JSON.parse(raw); } catch (_) { /* not JSON */ }

            let reply;
            if (data && typeof data.response === 'string') {
                reply = data.response;
            } else if (res.status === 422) {
                reply = 'Please keep your message between 1 and 500 characters.';
            } else {
                reply = 'Sorry, something went wrong. Please try again.';
            }
            typing.row.remove();
            addAssistantMessage(reply, !res.ok);
        } catch (err) {
            typing.row.remove();
            addAssistantMessage('Could not reach the server. Please check your connection and try again.', true);
        } finally {
            clearTimeout(wakeTimer);
            setBusy(false);
            input.focus();
        }
    }

    // ---------- Events ----------
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keydown', (e) => {
        // Enter sends; Shift+Enter inserts a new line. Skip while an IME is composing text.
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
            e.preventDefault();
            sendMessage();
        }
    });
    input.addEventListener('input', autoResize);

    // Example prompts: copy into the box for editing; do not send.
    if (welcome) {
        welcome.addEventListener('click', (e) => {
            const btn = e.target.closest('.example');
            if (!btn) return;
            input.value = btn.dataset.prompt || '';
            autoResize();
            input.focus();
            input.setSelectionRange(input.value.length, input.value.length);
        });
    }

    if (newChatBtn) {
        newChatBtn.addEventListener('click', () => {
            if (busy) return;
            thread.innerHTML = '';
            if (welcome) welcome.hidden = false;
            input.value = '';
            autoResize();
            scroller.scrollTop = 0;
            input.focus();
        });
    }

    input.focus();
});