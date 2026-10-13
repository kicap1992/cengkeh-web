/**
 * login.js — Client-side handling for the login form.
 */

(function () {
    "use strict";

    console.log("🍀 login.js loaded");

    const form = document.getElementById("login-form");
    const phoneInput = document.getElementById("phone");
    const passwordInput = document.getElementById("password");
    const submitBtn = document.getElementById("login-submit");
    const messageBox = document.getElementById("form-message");

    if (!form || !phoneInput || !passwordInput) {
        console.error("❌ Login form elements not found");
        return;
    }

    function showMessage(text, kind) {
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
        submitBtn.innerHTML = isLoading
            ? "Memproses..."
            : 'Login <i class="fa fa-arrow-circle-right"></i>';
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
        } else {
            $.unblockUI();
        }
    }

    // Force numeric on phone input
    phoneInput.addEventListener("input", (e) => {
        let v = e.target.value.replace(/\D/g, "").slice(0, 15);
        e.target.value = v;
    });

    function validate() {
        const phone = phoneInput.value.trim();
        const password = passwordInput.value;

        if (!/^08\d{8,13}$/.test(phone)) {
            return "Nomor telepon harus dimulai dengan 08 dan 10–15 digit.";
        }
        if (!password) {
            return "Password tidak boleh kosong.";
        }
        return null;
    }

    async function handleSubmit(e) {
        if (e) e.preventDefault();
        clearMessage();

        const err = validate();
        if (err) {
            showMessage(err, "error");
            return;
        }

        setLoading(true);

        try {
            const res = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    nomor_telepon: phoneInput.value.trim(),
                    password: passwordInput.value,
                }),
            });

            const data = await res.json();

            if (res.ok) {
                const level = data.user && data.user.level;
                const destination = level === "admin" ? "/admin" : "/user";

                showMessage("Login berhasil. Mengalihkan...", "success");
                setTimeout(() => { window.location.href = destination; }, 600);
            } else {
                showMessage(data.error || "Login gagal.", "error");
            }
        } catch (err) {
            console.error("❌ Login failed:", err);
            showMessage("Terjadi kesalahan teknis. Coba lagi.", "error");
        } finally {
            setLoading(false);
        }
    }

    form.addEventListener("submit", handleSubmit);
})();