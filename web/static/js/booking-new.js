/**
 * booking-new.js — Booking form: dates + selected pemetik + submit.
 */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        console.log("🍀 booking-new.js loaded");

        // State
        let pemetikList = [];   // full details of selected pemetik
        let pricePerDay = 0;
        let minLeadDays = 1;
        let minDays = 1;
        let maxDays = 30;

        // DOM refs
        const startDateInput = document.getElementById("start-date");
        const endDateInput = document.getElementById("end-date");
        const notesInput = document.getElementById("notes");
        const pemetikCount = document.getElementById("pemetik-count");
        const pemetikSummary = document.getElementById("pemetik-summary");
        const summaryDays = document.getElementById("summary-days");
        const summaryPrice = document.getElementById("summary-price");
        const summaryCount = document.getElementById("summary-count");
        const summaryTotal = document.getElementById("summary-total");
        const errorBox = document.getElementById("form-error");
        const btnSubmit = document.getElementById("btn-submit");
        const btnCancel = document.getElementById("btn-cancel");

        function earliestBookableISO() {
            // Today + minLeadDays, in local time
            const d = new Date();
            d.setDate(d.getDate() + minLeadDays);
            const y = d.getFullYear();
            const m = String(d.getMonth() + 1).padStart(2, "0");
            const dd = String(d.getDate()).padStart(2, "0");
            return `${y}-${m}-${dd}`;
        }

        // ---------------------------------------------------------------------
        // Date constraints
        // ---------------------------------------------------------------------
        function todayISO() {
            // "2026-10-17" for today, in local time
            const now = new Date();
            const y = now.getFullYear();
            const m = String(now.getMonth() + 1).padStart(2, "0");
            const d = String(now.getDate()).padStart(2, "0");
            return `${y}-${m}-${d}`;
        }


        function applyDateConstraints() {
            const earliest = earliestBookableISO();

            // --- Start date: min = today + minLeadDays ---
            startDateInput.min = earliest;

            // If start is currently before the earliest allowed date, reset
            if (startDateInput.value && startDateInput.value < earliest) {
                startDateInput.value = "";
            }

            // --- End date: min = max(earliest, start_date) ---
            if (startDateInput.value) {
                endDateInput.min = startDateInput.value;

                if (endDateInput.value && endDateInput.value < startDateInput.value) {
                    endDateInput.value = "";
                }
            } else {
                endDateInput.min = earliest;
            }
        }

        startDateInput.addEventListener("change", () => {
            applyDateConstraints();

            // If start is set and end is empty, pre-fill end with the same day (1-day booking)
            if (startDateInput.value && !endDateInput.value) {
                endDateInput.value = startDateInput.value;
            }

            updateSummary();
        });

        endDateInput.addEventListener("change", updateSummary);

        // ---------------------------------------------------------------------
        // Helpers
        // ---------------------------------------------------------------------
        function formatRupiah(n) {
            return "Rp " + Number(n).toLocaleString("id-ID");
        }

        function fotoThumb(path) {
            if (!path) return "<span>👤</span>";
            return `<img src="/static/${path}" alt=""
                    onerror="this.style.display='none';this.parentNode.innerHTML='👤';">`;
        }

        function daysBetween(start, end) {
            const ms = end.getTime() - start.getTime();
            return Math.floor(ms / 86400000) + 1;   // inclusive
        }

        // ---------------------------------------------------------------------
        // Load page data
        // ---------------------------------------------------------------------
        async function loadData() {
            // 1. Read selected pemetik IDs from sessionStorage
            const idsRaw = sessionStorage.getItem("booking_pemetik_ids");
            if (!idsRaw) {
                // No selection — redirect back
                window.location.href = "/user/sewa-pemetik";
                return;
            }

            let ids;
            try {
                ids = JSON.parse(idsRaw);
            } catch {
                window.location.href = "/user/sewa-pemetik";
                return;
            }
            if (!Array.isArray(ids) || ids.length === 0) {
                window.location.href = "/user/sewa-pemetik";
                return;
            }

            // 2. Fetch all active pemetik to get the full details
            const res = await fetch("/api/user/pemetik");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            const data = await res.json();

            pricePerDay = data.price_per_day || 0;
            minLeadDays = data.min_lead_days != null ? data.min_lead_days : 1;

            // Filter to only the selected IDs
            const allPemetik = data.pemetik || [];
            pemetikList = allPemetik.filter(p => ids.includes(p.id));

            if (pemetikList.length !== ids.length) {
                // Some IDs weren't found (deactivated?) — send back
                alert("Beberapa pemetik yang dipilih tidak tersedia lagi. Silakan pilih ulang.");
                window.location.href = "/user/sewa-pemetik";
                return;
            }

            applyDateConstraints();
            renderPemetikSummary();
            updateSummary();
        }

        function renderPemetikSummary() {
            pemetikCount.textContent = pemetikList.length;
            pemetikSummary.innerHTML = pemetikList.map(p => `
                <div style="display: flex; align-items: center; gap: 10px;
                            background: #f0fdf4; padding: 8px 12px; border-radius: 8px;">
                    <div style="width: 40px; height: 40px; border-radius: 50%;
                                background: #e8f5e9; display: flex; align-items: center;
                                justify-content: center; font-size: 1.2rem;
                                color: #2d6a4f; overflow: hidden;">
                        ${fotoThumb(p.foto_path)}
                    </div>
                    <div style="font-size: 0.9rem; font-weight: 600; color: #2d6a4f;">
                        ${escapeHtml(p.nama)}
                    </div>
                </div>
            `).join("");
        }

        function escapeHtml(s) {
            return String(s)
                .replace(/&/g, "&amp;")
                .replace(/</g, "&lt;")
                .replace(/>/g, "&gt;")
                .replace(/"/g, "&quot;")
                .replace(/'/g, "&#39;");
        }

        // ---------------------------------------------------------------------
        // Live summary update
        // ---------------------------------------------------------------------
        function updateSummary() {
            summaryPrice.textContent = formatRupiah(pricePerDay);
            summaryCount.textContent = pemetikList.length;

            const startVal = startDateInput.value;
            const endVal = endDateInput.value;

            if (!startVal || !endVal) {
                summaryDays.textContent = "—";
                summaryTotal.textContent = "—";
                return;
            }

            const start = new Date(startVal);
            const end = new Date(endVal);

            if (end < start) {
                summaryDays.textContent = "⚠️";
                summaryTotal.textContent = "Tanggal tidak valid";
                return;
            }

            const days = daysBetween(start, end);
            const total = days * pricePerDay * pemetikList.length;

            summaryDays.textContent = days;
            summaryTotal.textContent = formatRupiah(total);
        }

        startDateInput.addEventListener("change", updateSummary);
        endDateInput.addEventListener("change", updateSummary);

        // ---------------------------------------------------------------------
        // Submit
        // ---------------------------------------------------------------------
        btnSubmit.addEventListener("click", async () => {
            errorBox.style.display = "none";

            const startVal = startDateInput.value;
            const endVal = endDateInput.value;

            if (!startVal || !endVal) {
                showError("Pilih tanggal mulai dan tanggal selesai.");
                return;
            }

            btnSubmit.disabled = true;
            btnSubmit.textContent = "Memproses...";

            try {
                const res = await fetch("/api/user/order", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        pemetik_ids: pemetikList.map(p => p.id),
                        start_date: startVal,
                        end_date: endVal,
                        notes: notesInput.value.trim(),
                    }),
                });
                const data = await res.json();

                if (res.ok) {
                    // Clear the selection from sessionStorage
                    sessionStorage.removeItem("booking_pemetik_ids");

                    // Show success message and redirect
                    alert(
                        `✅ Pesanan berhasil dibuat!\n\n` +
                        `Kode Pesanan: ${data.order_code}\n` +
                        `Total: ${formatRupiah(data.total_amount)}\n\n` +
                        `Silakan lanjutkan ke pembayaran.`
                    );
                    window.location.href = "/user/sewa-pemetik";
                } else {
                    showError(data.error || "Gagal membuat pesanan.");
                    btnSubmit.disabled = false;
                    btnSubmit.textContent = "Buat Pesanan";
                }
            } catch (err) {
                console.error("Order creation failed:", err);
                showError("Terjadi kesalahan teknis. Coba lagi.");
                btnSubmit.disabled = false;
                btnSubmit.textContent = "Buat Pesanan";
            }
        });

        function showError(msg) {
            errorBox.textContent = msg;
            errorBox.style.display = "block";
        }

        btnCancel.addEventListener("click", () => {
            window.location.href = "/user/sewa-pemetik";
        });

        // ---------------------------------------------------------------------
        // On load
        // ---------------------------------------------------------------------
        loadData().catch(err => {
            console.error("Failed to load booking page:", err);
            showError("Gagal memuat data. Silakan kembali dan coba lagi.");
        });
    });
})();