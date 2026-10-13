/**
 * logout.js — Shared logout handler.
 *
 * Attaches to ALL elements with class="logout-link".
 * Works on any page — pages with zero logout buttons do nothing.
 *
 * Flow:
 *   1. POST /api/logout (server deletes session + clears cookie)
 *   2. Redirect to /login
 */

(function () {
    "use strict";

    const links = document.querySelectorAll(".logout-link");
    if (links.length === 0) return;   // no logout buttons — skip

    console.log(`🍀 logout.js loaded — attached to ${links.length} button(s)`);

    async function doLogout(e) {
        e.preventDefault();

        // Optional: confirm
        if (!confirm("Keluar dari akun Anda?")) return;

        // Visual feedback — disable all logout buttons
        links.forEach((el) => {
            el.style.opacity = "0.5";
            el.style.pointerEvents = "none";
        });

        try {
            const res = await fetch("/api/logout", {
                method: "POST",
                credentials: "same-origin",
            });
            if (!res.ok) {
                console.error("Logout returned non-OK:", res.status);
            }
        } catch (err) {
            console.error("Logout request failed:", err);
            // continue anyway — user wants out
        }

        // Redirect to index regardless
        window.location.href = "/";
    }

    // Attach to every logout element
    links.forEach((el) => el.addEventListener("click", doLogout));
})();