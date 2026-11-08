document.addEventListener('DOMContentLoaded', () => {
    const input = document.getElementById('userInput');
    const messages = document.getElementById('messages');
    const sendBtn = document.getElementById('sendBtn');

    if (!input || !sendBtn || !messages) return;

    async function sendMessage() {
        const text = input.value.trim();
        if (!text) return;

        messages.innerHTML += 
            <div class="message-row user">
                <div class="avatar">U</div>
                <div class="message-content">\</div>
            </div>;
        input.value = '';
        messages.scrollTop = messages.scrollHeight;

        const typingId = 'typing-' + Date.now();
        messages.innerHTML += 
            <div class="message-row assistant" id="\">
                <div class="avatar">AI</div>
                <div class="message-content" style="display: flex; align-items: center; gap: 4px;">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            </div>;
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

            let displayText = "";
            if (rawText.trim().startsWith('<')) {
                displayText = "Server returned HTML error page instead of JSON. Check Render logs.";
            } else {
                try {
                    const data = JSON.parse(rawText);
                    displayText = data.response || JSON.stringify(data);
                } catch (err) {
                    displayText = "Parsing error: " + rawText.substring(0, 150);
                }
            }

            messages.innerHTML += 
                <div class="message-row assistant">
                    <div class="avatar">AI</div>
                    <div class="message-content">\</div>
                </div>;
        } catch (err) {
            const typingEl = document.getElementById(typingId);
            if (typingEl) typingEl.remove();
            messages.innerHTML += 
                <div class="message-row assistant">
                    <div class="avatar">AI</div>
                    <div class="message-content" style="color: #ef4444;">Network Error: \</div>
                </div>;
        }
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(str) {
        return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    }

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') sendMessage();
    });
});
