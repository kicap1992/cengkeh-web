/**
 * chat.js — Cengkeh chatbot UI interactions.
 *
 * Step 3: generate session id (with fallback), send message to /api/chat.
 */

(function () {
    "use strict";

    console.log("🍀 chat.js loaded");

    // ---------------------------------------------------------------
    // DOM elements
    // ---------------------------------------------------------------
    const form     = document.getElementById("chat-form");
    const input    = document.getElementById("chat-input");
    const send     = document.getElementById("chat-send");
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
        // Prefer crypto.randomUUID when available (secure contexts)
        if (window.crypto && typeof window.crypto.randomUUID === "function") {
            return window.crypto.randomUUID();
        }
        // Fallback: build a v4-style UUID from getRandomValues
        if (window.crypto && typeof window.crypto.getRandomValues === "function") {
            const b = new Uint8Array(16);
            window.crypto.getRandomValues(b);
            b[6] = (b[6] & 0x0f) | 0x40;
            b[8] = (b[8] & 0x3f) | 0x80;
            const hex = [...b].map(x => x.toString(16).padStart(2, "0")).join("");
            return [
                hex.slice(0, 8),
                hex.slice(8, 12),
                hex.slice(12, 16),
                hex.slice(16, 20),
                hex.slice(20),
            ].join("-");
        }
        // Last resort
        return `sess-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    }

    let sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
        sessionId = generateSessionId();
        sessionStorage.setItem("session_id", sessionId);
    }
    console.log("🆔 Session ID:", sessionId);

    // ---------------------------------------------------------------
    // Append a message bubble to the chat history
    // ---------------------------------------------------------------
    function appendMessage(text, who = "bot") {
        const div = document.createElement("div");
        div.className = `msg msg-${who}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
        return div;
    }

    // ---------------------------------------------------------------
    // Handle the submit event
    // ---------------------------------------------------------------
    async function handleSubmit(event) {
        if (event) event.preventDefault();

        const text = input.value.trim();
        if (!text) return;

        appendMessage(text, "user");
        input.value = "";
        input.focus();

        try {
            const res = await fetch("/api/chat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    message: text,
                    session_id: sessionId,
                }),
            });
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();
            console.log("✅ Response:", data);
        } catch (err) {
            console.error("❌ Fetch failed:", err);
        }
    }

    form.addEventListener("submit", handleSubmit);
})();