/**
 * register.js — Client-side handling for the register form.
 *
 * Validates input, submits to /api/register, and shows feedback.
 */

(function () {
    "use strict";

    console.log("🍀 register.js loaded");

    const form = document.getElementById("register-form");
    const phoneInput = document.getElementById("phone");
    const nameInput = document.getElementById("name");
    const passwordInput = document.getElementById("password");
    const confirmInput = document.getElementById("confirm_password");
    const submitBtn = document.getElementById("register-submit");
    const messageBox = document.getElementById("form-message");

    if (!form || !phoneInput || !nameInput || !passwordInput || !confirmInput) {
        console.error("❌ Register form elements not found");
        return;
    }

    // ---------------------------------------------------------------------
    // Helpers
    // ---------------------------------------------------------------------
    function showMessage(text, kind) {
        // kind: "error" | "success" | "info"
        const colors = {
            error: { bg: "#fdecea", fg: "#b71c1c", border: "#f5c6cb" },
            success: { bg: "#e8f5e9", fg: "#1b5e20", border: "#c8e6c9" },
            info: { bg: "#e3f2fd", fg: "#0d47a1", border: "#bbdefb" },
        };
        const c = colors[kind] || colors.info;
        messageBox.textContent = text;
        messageBox.style.background = c.bg;
        messageBox.style.color = c.fg;
        messageBox.style.border = `1px solid ${c.border}`;
        messageBox.style.display = "block";
    }

    function clearMessage() {
        messageBox.style.display = "none";
        messageBox.textContent = "";
    }

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        submitBtn.textContent = isLoading ? "Memproses..." : "Register";
        if (isLoading) {
            $.blockUI({
                message: "Sedang Diproses",
                css: {
                    border: 'none',
                    padding: '15px',
                    backgroundColor: '#000',
                    '-webkit-border-radius': '10px',
                    '-moz-border-radius': '10px',
                    opacity: .5,
                    color: '#fff'
                }
            });
        }else {
            $.unblockUI();
        }
    }

    // ---------------------------------------------------------------------
    // Phone input: force numeric, auto-add leading 0
    // ---------------------------------------------------------------------
    phoneInput.addEventListener("input", (e) => {
        // Strip anything that isn't a digit
        let v = e.target.value.replace(/\D/g, "");
        // Cap at 15 digits
        v = v.slice(0, 15);
        e.target.value = v;
    });

    // ---------------------------------------------------------------------
    // Validation
    // ---------------------------------------------------------------------
    function validateForm() {
        const phone = phoneInput.value.trim();
        const name = nameInput.value.trim();
        const password = passwordInput.value;
        const confirm = confirmInput.value;

        if (!/^08\d{8,13}$/.test(phone)) {
            return "Nomor telepon harus dimulai dengan 08 dan 10–15 digit.";
        }
        if (name.length < 2) {
            return "Nama minimal 2 karakter.";
        }
        if (password.length < 8) {
            return "Password minimal 8 karakter.";
        }
        if (password !== confirm) {
            return "Konfirmasi password tidak cocok.";
        }
        return null;  // valid
    }

    // ---------------------------------------------------------------------
    // Submit handler
    // ---------------------------------------------------------------------
    async function handleSubmit(e) {
        if (e) e.preventDefault();
        clearMessage();

        const error = validateForm();
        if (error) {
            showMessage(error, "error");
            return;
        }

        setLoading(true);

        console.log("📤 Submitting registration:", {
            nomor_telepon: phoneInput.value.trim(),
            nama: nameInput.value.trim(),
            password: passwordInput.value,
        });

        // // sleep 3 seconds to simulate network delay
        // await new Promise((resolve) => setTimeout(resolve, 10000));

        // showMessage("Registrasi berhasil. Menunggu persetujuan admin.", "success");
        // form.reset();
        // setLoading(false);

        try {
            const res = await fetch("/api/register", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    nomor_telepon: phoneInput.value.trim(),
                    nama: nameInput.value.trim(),
                    password: passwordInput.value,
                }),
            });

            const data = await res.json();

            if (res.ok) {
                // Success — status 201
                showMessage(
                    data.message || "Registrasi berhasil. Menunggu persetujuan admin.",
                    "success"
                );
                form.reset();
                // Optional: disable form after success
                // submitBtn.disabled = true;
            } else {
                // Error — 400 or 409
                showMessage(data.error || "Registrasi gagal. Coba lagi.", "error");
            }
        } catch (err) {
            console.error("❌ Register failed:", err);
            showMessage("Terjadi kesalahan teknis. Coba lagi.", "error");
        } finally {
            setLoading(false);
        }
    }

    form.addEventListener("submit", handleSubmit);
})();