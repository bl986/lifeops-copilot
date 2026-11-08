document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('userInput');
    const messages = document.getElementById('messages');
    const sendBtn = document.getElementById('sendBtn');

    if (!input || !sendBtn || !messages) return;

    // Built-in markdown parser fallback in case CDN fails
    function parseMarkdown(text) {
        if (typeof marked !== 'undefined' && typeof marked.parse === 'function') {
            return marked.parse(text);
        }
        // Fallback markdown converter
        let html = escapeHtml(text);
        // Convert links: [text](url) -> <a href="url" target="_blank">text</a>
        html = html.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        // Convert bold: **text** -> <strong>text</strong>
        html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        // Convert newlines to breaks
        html = html.replace(/\n/g, '<br>');
        return `<p>${html}</p>`;
    }

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        messages.innerHTML += `
            <div class="message-row user">
                <div class="avatar">U</div>
                <div class="message-content">${escapeHtml(text)}</div>
            </div>`;
        input.value = '';
        messages.scrollTop = messages.scrollHeight;

        const typingId = 'typing-' + Date.now();
        messages.innerHTML += `
            <div class="message-row assistant" id="${typingId}">
                <div class="avatar">AI</div>
                <div class="message-content" style="display: flex; align-items: center; gap: 4px;">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>`;
        messages.scrollTop = messages.scrollHeight;

        try {
            const res = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const rawText = await res.text();
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();

            let htmlOutput = "";
            if (rawText.trim().startsWith('<')) {
                htmlOutput = "<p style='color: #ef4444;'>Server returned HTML error page instead of JSON. Check Render logs.</p>";
            } else {
                try {
                    const data = JSON.parse(rawText);
                    const markdownText = data.response || JSON.stringify(data);
                    htmlOutput = parseMarkdown(markdownText);
                } catch (err) {
                    htmlOutput = parseMarkdown(rawText);
                }
            }

            messages.innerHTML += `
                <div class="message-row assistant">
                    <div class="avatar">AI</div>
                    <div class="message-content markdown-body">${htmlOutput}</div>
                </div>`;
        } catch (err) {
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();
            messages.innerHTML += `
                <div class="message-row assistant">
                    <div class="avatar">AI</div>
                    <div class="message-content" style="color: #ef4444;">Network Error: ${escapeHtml(err.message)}</div>
                </div>`;
        }
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(str) {
        return String(str)
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
});
