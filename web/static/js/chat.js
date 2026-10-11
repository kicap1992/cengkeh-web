/**
 * chat.js — Cengkeh chatbot UI interactions.
 *
 * Flow so far:
 *   1. User types a question and submits.
 *   2. We POST/GET to the backend.
 *   3. We render the response (suggestions or messages).
 */

(function () {
    "use strict";

    console.log("🍀 chat.js loaded");

    // ---------------------------------------------------------------
    // DOM elements
    // ---------------------------------------------------------------
    const form = document.getElementById("chat-form");
    const input = document.getElementById("chat-input");
    const send = document.getElementById("chat-send");
    const messages = document.getElementById("chat-messages");

    if (!form || !input || !send || !messages) {
        console.error("❌ Chat elements not found:", {
            form: !!form, input: !!input, send: !!send, messages: !!messages,
        });
        return;
    }

    console.log("✅ Chat elements found");

    // ---------------------------------------------------------------
    // Session ID
    // ---------------------------------------------------------------
    function generateSessionId() {
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        if (window.crypto && typeof window.crypto.getRandomValues === "function") {
            const b = new Uint8Array(16);
            window.crypto.getRandomValues(b);
            b[6] = (b[6] & 0x0f) | 0x40;
            b[8] = (b[8] & 0x3f) | 0x80;
            const hex = [...b].map(x => x.toString(16).padStart(2, "0")).join("");
            return [hex.slice(0, 8), hex.slice(8, 12), hex.slice(12, 16), hex.slice(16, 20), hex.slice(20)].join("-");
        }
        return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    }

    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
        sessionId = generateSessionId();
        sessionStorage.setItem("session_id", sessionId);
    }
    console.log("🆔 Session ID:", sessionId);

    // ---------------------------------------------------------------
    // Rendering helpers
    // ---------------------------------------------------------------
    function appendMessage(text, who = "bot") {
        const div = document.createElement("div");
        div.className = `msg msg-${who}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    function renderMatches(data) {
        const wrapper = document.createElement("div");
        wrapper.className = "msg msg-bot";

        const intro = document.createElement("div");
        intro.textContent = "Apakah maksud Anda salah satu dari pertanyaan berikut?";
        wrapper.appendChild(intro);

        const list = document.createElement("div");
        list.className = "suggestions";

        data.matches.forEach(m => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "suggestion-btn";
            btn.textContent = m.question;
            btn.dataset.qaId = m.id;
            btn.addEventListener("click", () => handleSuggestionClick(m.id, m.question));
            list.appendChild(btn);
        });

        wrapper.appendChild(list);
        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    function renderQA(qa) {
        // --- The answer ---
        const wrapper = document.createElement("div");
        wrapper.className = "msg msg-bot";

        // Question (bold)
        const q = document.createElement("div");
        q.style.fontWeight = "600";
        q.style.marginBottom = "6px";
        q.textContent = qa.question;
        wrapper.appendChild(q);

        // Answer text
        if (qa.answer) {
            const a = document.createElement("div");
            a.textContent = qa.answer;
            wrapper.appendChild(a);
        }

        // Sources
        if (qa.sources && qa.sources.length > 0) {
            const srcs = document.createElement("div");
            srcs.className = "sources";
            srcs.innerHTML = "<strong>📚 Sumber:</strong>";
            qa.sources.forEach(s => {
                const line = document.createElement("div");
                line.textContent = `• ${s.kode} — ${s.judul}`;
                srcs.appendChild(line);
            });
            wrapper.appendChild(srcs);
        }

        messages.appendChild(wrapper);

        // --- Follow-up (if diagnostic) ---
        if (qa.follow_up) {
            renderFollowUp(qa.follow_up);
        } else {
            // Terminal: prompt the user to ask again
            appendMessage("Ada pertanyaan lain? Silakan ketik di bawah.", "system");
        }

        messages.scrollTop = messages.scrollHeight;
    }

    function renderFollowUp(followUp) {
        const wrapper = document.createElement("div");
        wrapper.className = "msg msg-bot";

        const intro = document.createElement("div");
        intro.textContent = followUp.question;
        intro.style.marginBottom = "6px";
        wrapper.appendChild(intro);

        const list = document.createElement("div");
        list.className = "suggestions";

        followUp.options.forEach(opt => {
            const btn = document.createElement("button");
            btn.type = "button";
            btn.className = "suggestion-btn";
            btn.textContent = opt.label;
            btn.dataset.optionId = opt.id;
            btn.addEventListener("click", () => handleFollowUpClick(opt.id, opt.label));
            list.appendChild(btn);
        });

        wrapper.appendChild(list);
        messages.appendChild(wrapper);
        messages.scrollTop = messages.scrollHeight;
    }

    async function handleFollowUpClick(optionId, label) {
        console.log("👆 Follow-up option clicked:", optionId, label);
        appendMessage(label, "user");

        try {
            const res = await fetch(`/api/next/${optionId}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            console.log("✅ Next step:", data);

            if (data.type === "follow_up") {
                renderFollowUp(data.follow_up);
            } else if (data.type === "matches") {
                // Reuse the same renderer as search results
                renderMatches({ matches: data.matches });
            } else {
                appendMessage("Maaf, terjadi kesalahan.", "bot");
            }
        } catch (err) {
            console.error("❌ Fetch failed:", err);
            appendMessage("Maaf, terjadi kesalahan teknis.", "bot");
        }
    }

    // ---------------------------------------------------------------
    // Interaction handlers
    // ---------------------------------------------------------------
    async function handleSuggestionClick(qaId, question) {
        console.log("👆 Suggestion clicked, QA id:", qaId);

        // 1. Echo the user's choice as their "message"
        appendMessage(question, "user");

        // 2. Fetch the QA detail
        try {
            const res = await fetch(`/api/qa/${qaId}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const qa = await res.json();
            console.log("✅ QA detail:", qa);

            // 3. Render it
            renderQA(qa);
        } catch (err) {
            console.error("❌ Fetch failed:", err);
            appendMessage("Maaf, terjadi kesalahan saat mengambil detail pertanyaan.", "bot");
        }
    }

    async function handleSubmit(event) {
        if (event) event.preventDefault();

        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, "user");
        input.value = "";
        input.focus();

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(text)}`);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            console.log("✅ Search response:", data);

            if (data.matches && data.matches.length > 0) {
                renderMatches(data);
            } else if (data.message) {
                appendMessage(data.message, "bot");
            } else {
                appendMessage("Maaf, terjadi kesalahan. Coba lagi.", "bot");
            }
        } catch (err) {
            console.error("❌ Fetch failed:", err);
            appendMessage("Maaf, terjadi kesalahan teknis. Coba lagi.", "bot");
        }
    }

    form.addEventListener("submit", handleSubmit);
})();