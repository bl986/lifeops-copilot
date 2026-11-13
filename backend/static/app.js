document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('userInput');
    const scroller = document.getElementById('messages');
    const thread = document.getElementById('thread');
    const welcome = document.getElementById('welcome');
    const sendBtn = document.getElementById('sendBtn');
    const newChatBtn = document.getElementById('newChatBtn');
    const connectorBtn = document.getElementById('connectorBtn');
    const connectorPanel = document.getElementById('connectorPanel');
    const connectorList = document.getElementById('connectorList');
    const connectorCount = document.getElementById('connectorCount');

    if (!input || !scroller || !thread || !sendBtn) return;

    let busy = false;
    let workflowList = [];
    let connectorState = {};
    let connectorsLoaded = false;
    const STORE_KEY = 'lifeops.connectors';

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

    // ---------- Connectors ----------
    function readSaved() {
        try { return JSON.parse(localStorage.getItem(STORE_KEY)) || {}; } catch (_) { return {}; }
    }

    function writeSaved() {
        try { localStorage.setItem(STORE_KEY, JSON.stringify(connectorState)); } catch (_) { /* storage unavailable */ }
    }

    function enabledConnectors() {
        return Object.keys(connectorState).filter((id) => connectorState[id]);
    }

    function updateConnectorCount() {
        if (connectorCount) connectorCount.textContent = String(enabledConnectors().length);
    }

    function renderConnectors(list) {
        connectorList.innerHTML = '';
        list.forEach((c) => {
            const row = document.createElement('label');
            row.className = 'connector-row';

            const text = document.createElement('span');
            text.className = 'connector-text';
            const name = document.createElement('span');
            name.className = 'connector-name';
            name.textContent = c.name;
            const desc = document.createElement('span');
            desc.className = 'connector-desc';
            desc.textContent = c.description;
            text.append(name, desc);

            const toggle = document.createElement('input');
            toggle.type = 'checkbox';
            toggle.className = 'switch';
            toggle.setAttribute('role', 'switch');
            toggle.checked = !!connectorState[c.id];
            toggle.addEventListener('change', () => {
                connectorState[c.id] = toggle.checked;
                writeSaved();
                updateConnectorCount();
            });

            row.append(text, toggle);
            connectorList.appendChild(row);
        });
    }

    async function loadConnectors() {
        if (!connectorBtn || !connectorPanel || !connectorList) return;
        try {
            const res = await fetch('/connectors');
            const data = await res.json();
            const list = Array.isArray(data.connectors) ? data.connectors : [];
            const saved = readSaved();
            list.forEach((c) => {
                connectorState[c.id] = typeof saved[c.id] === 'boolean' ? saved[c.id] : !!c.default;
            });
            connectorsLoaded = list.length > 0;
            renderConnectors(list);
            updateConnectorCount();
        } catch (_) {
            connectorBtn.hidden = true; // the server falls back to its defaults
        }
    }

    function setPanel(open) {
        connectorPanel.hidden = !open;
        connectorBtn.setAttribute('aria-expanded', String(open));
    }

    if (connectorBtn && connectorPanel) {
        connectorBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            setPanel(connectorPanel.hidden);
        });
        document.addEventListener('click', (e) => {
            if (!connectorPanel.hidden && !connectorPanel.contains(e.target)) setPanel(false);
        });
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') setPanel(false);
        });
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

    function addAssistantMessage(text, isNotice, suggestions, sources) {
        const { content } = createRow('assistant');
        content.innerHTML = renderMarkdown(text);
        if (isNotice) content.classList.add('notice');

        const links = (Array.isArray(sources) ? sources : []).filter(
            (s) => s && typeof s.url === 'string' && s.url.startsWith('https://')
        );
        if (links.length) {
            const src = document.createElement('div');
            src.className = 'sources';
            src.append('Sources: ');
            links.slice(0, 8).forEach((s, i) => {
                if (i > 0) src.append(' · ');
                const a = document.createElement('a');
                a.href = s.url;
                a.target = '_blank';
                a.rel = 'noopener noreferrer';
                a.textContent = typeof s.title === 'string' && s.title ? s.title : s.url;
                src.appendChild(a);
            });
            content.appendChild(src);
        }

        if (Array.isArray(suggestions) && suggestions.length) {
            const bar = document.createElement('div');
            bar.className = 'followups';
            const label = document.createElement('span');
            label.className = 'followups-label';
            label.textContent = 'Try asking:';
            bar.appendChild(label);
            suggestions.slice(0, 3).forEach((s) => {
                if (typeof s !== 'string') return;
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'followup';
                btn.textContent = s;
                btn.dataset.prompt = s;
                bar.appendChild(btn);
            });
            content.appendChild(bar);
        }
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
        thread.querySelectorAll('.followups').forEach((el) => el.remove());
        if (welcome) welcome.hidden = true;
        setPanel(false);
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
                body: JSON.stringify({
                    message: text,
                    connectors: connectorsLoaded ? enabledConnectors() : undefined
                })
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
            addAssistantMessage(
                reply,
                !res.ok,
                res.ok && data ? data.suggestions : null,
                res.ok && data ? data.sources : null
            );
        } catch (err) {
            typing.row.remove();
            addAssistantMessage('Could not reach the server. Please check your connection and try again.', true);
        } finally {
            clearTimeout(wakeTimer);
            setBusy(false);
            input.focus();
        }
    }

    async function loadWorkflows() {
        try {
            const res = await fetch('/workflows');
            const data = await res.json();
            workflowList = Array.isArray(data.workflows) ? data.workflows : [];
        } catch (_) {
            workflowList = [];
        }
    }

    function buildWorkflowFollowups(suggestions, currentId) {
        const bar = document.createElement('div');
        bar.className = 'followups';
        const label = document.createElement('span');
        label.className = 'followups-label';
        label.textContent = 'Try next:';
        bar.appendChild(label);
        workflowList.filter((w) => w.id !== currentId).forEach((w) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'followup workflow-chip';
            btn.textContent = 'Run workflow: ' + w.name;
            btn.dataset.workflow = w.id;
            btn.dataset.name = w.name;
            bar.appendChild(btn);
        });
        (Array.isArray(suggestions) ? suggestions : []).slice(0, 3).forEach((s) => {
            if (typeof s !== 'string') return;
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'followup';
            btn.textContent = s;
            btn.dataset.prompt = s;
            bar.appendChild(btn);
        });
        return bar.querySelector('button') ? bar : null;
    }

    // ---------- Workflows (fixed steps, live progress) ----------
    const STEP_ICON = { pending: '○', running: '◐', done: '✓', warning: '⚠', error: '✕' };

    async function runWorkflow(id, name) {
        if (busy) return;
        setBusy(true);
        thread.querySelectorAll('.followups').forEach((el) => el.remove());
        if (welcome) welcome.hidden = true;
        setPanel(false);
        addUserMessage('Run workflow: ' + name);

        const { content } = createRow('assistant');
        const title = document.createElement('div');
        title.className = 'wf-title';
        title.textContent = name + ' (fixed steps)';
        const list = document.createElement('ul');
        list.className = 'wf-steps';
        content.append(title, list);
        const items = {};
        let finished = false;

        function setStep(stepId, status, extra) {
            const li = items[stepId];
            if (!li) return;
            li.className = 'wf-step ' + status;
            li.querySelector('.wf-icon').textContent = STEP_ICON[status] || '○';
            li.querySelector('.wf-extra').textContent = extra || '';
        }

        function finish(event) {
            finished = true;
            const body = document.createElement('div');
            body.className = 'wf-result' + (event.status === 'success' ? '' : ' notice');
            body.innerHTML = renderMarkdown(event.response || '');
            content.appendChild(body);

            const links = (Array.isArray(event.sources) ? event.sources : []).filter(
                (s) => s && typeof s.url === 'string' && s.url.startsWith('https://')
            );
            if (links.length) {
                const src = document.createElement('div');
                src.className = 'sources';
                src.append('Sources: ');
                links.slice(0, 8).forEach((s, i) => {
                    if (i > 0) src.append(' · ');
                    const a = document.createElement('a');
                    a.href = s.url;
                    a.target = '_blank';
                    a.rel = 'noopener noreferrer';
                    a.textContent = typeof s.title === 'string' && s.title ? s.title : s.url;
                    src.appendChild(a);
                });
                content.appendChild(src);
            }
            const followups = buildWorkflowFollowups(event.suggestions, id);
            if (followups) content.appendChild(followups);
        }

        function handle(event) {
            if (event.event === 'start') {
                (event.steps || []).forEach((s) => {
                    const li = document.createElement('li');
                    li.className = 'wf-step pending';
                    li.innerHTML = '<span class="wf-icon">○</span><span class="wf-label"></span><span class="wf-extra"></span>';
                    li.querySelector('.wf-label').textContent = s.label;
                    list.appendChild(li);
                    items[s.id] = li;
                });
            } else if (event.event === 'step') {
                const extra = event.status === 'done' && event.seconds != null
                    ? event.seconds + 's' : (event.detail || '');
                setStep(event.id, event.status, extra);
            } else if (event.event === 'result') {
                finish(event);
            }
            scrollToBottom();
        }

        try {
            const res = await fetch('/workflow', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    workflow: id,
                    connectors: connectorsLoaded ? enabledConnectors() : undefined
                })
            });
            if (!res.ok || !res.body) {
                let data = null;
                try { data = JSON.parse(await res.text()); } catch (_) { /* not JSON */ }
                finish({ status: 'error', sources: [],
                         response: (data && data.response) || 'Sorry, something went wrong. Please try again.' });
            } else {
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    let newline;
                    while ((newline = buffer.indexOf('\n')) >= 0) {
                        const line = buffer.slice(0, newline).trim();
                        buffer = buffer.slice(newline + 1);
                        if (!line) continue;
                        try { handle(JSON.parse(line)); } catch (e) { console.error('workflow event error', e); }
                    }
                }
            }
        } catch (err) {
            console.error('workflow error', err);
        }
        if (!finished) {
            finish({ status: 'error', sources: [], response: 'The workflow did not finish. Please try again.' });
        }
        setBusy(false);
        scrollToBottom();
        input.focus();
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

    // Example and follow-up prompts: copy into the box for editing; do not send.
    function usePrompt(text) {
        input.value = text;
        autoResize();
        input.focus();
        input.setSelectionRange(input.value.length, input.value.length);
    }

    if (welcome) {
        welcome.addEventListener('click', (e) => {
            const btn = e.target.closest('.example');
            if (!btn) return;
            if (btn.dataset.workflow) {
                runWorkflow(btn.dataset.workflow, btn.dataset.name || 'workflow');
                return;
            }
            usePrompt(btn.dataset.prompt || '');
        });
    }

    thread.addEventListener('click', (e) => {
        const btn = e.target.closest('.followup');
        if (!btn) return;
        if (btn.dataset.workflow) {
            runWorkflow(btn.dataset.workflow, btn.dataset.name || 'workflow');
            return;
        }
        usePrompt(btn.dataset.prompt || '');
    });

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

    loadConnectors();
    loadWorkflows();
    input.focus();
});