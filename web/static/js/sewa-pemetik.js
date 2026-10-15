/**
 * sewa-pemetik.js — User-facing browse pemetik + select multiple.
 */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        console.log("🍀 sewa-pemetik.js loaded");

        // State
        let pricePerDay = 0;
        const selectedIds = new Set();   // Set of pemetik IDs

        // DOM refs
        const grid         = document.getElementById("pemetik-grid");
        const emptyState   = document.getElementById("pemetik-empty");
        const priceDisplay = document.getElementById("price-display");
        const selectedCount= document.getElementById("selected-count");
        const actionBar    = document.getElementById("action-bar");
        const actionCount  = document.getElementById("action-count");
        const btnLanjut    = document.getElementById("btn-lanjut");
        const orderBanner  = document.getElementById("order-banner");

        // ---------------------------------------------------------------------
        // Helpers
        // ---------------------------------------------------------------------
        function formatRupiah(n) {
            return "Rp " + Number(n).toLocaleString("id-ID");
        }

        function formatDate(iso) {
            if (!iso) return "—";
            return new Date(iso + "T00:00:00").toLocaleDateString("id-ID", {
                day: "2-digit", month: "long", year: "numeric",
            });
        }

        function fotoThumb(path) {
            if (!path) return "<span>👤</span>";
            return `<img src="/static/${path}" alt=""
                    onerror="this.style.display='none';this.parentNode.innerHTML='👤';">`;
        }

        // ---------------------------------------------------------------------
        // Fetch data
        // ---------------------------------------------------------------------
        async function fetchPemetik() {
            const res = await fetch("/api/user/pemetik");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            
            return res.json();
        }

        async function fetchCurrentOrder() {
            const res = await fetch("/api/user/current-order");
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            return res.json();
        }

        // ---------------------------------------------------------------------
        // Render: order banner
        // ---------------------------------------------------------------------
        function renderOrderBanner(data) {
            if (!data.order || data.state === "none") {
                orderBanner.style.display = "none";
                return;
            }

            const o = data.order;
            const pemetikNames = o.pemetik.map(p => p.nama).join(", ");
            const count = o.pemetik.length;

            let icon, title, detail;

            if (data.state === "ongoing") {
                icon = "🌿";
                title = `Pesanan sedang berjalan`;
                detail = `${count} pemetik (${pemetikNames}) bekerja dari
                          <strong>${formatDate(o.start_date)}</strong> sampai
                          <strong>${formatDate(o.end_date)}</strong>.`;
            } else if (data.state === "soon") {
                icon = "📅";
                title = `Pesanan akan segera dimulai`;
                detail = `${count} pemetik (${pemetikNames}) akan bekerja mulai
                          <strong>${formatDate(o.start_date)}</strong>
                          (${o.total_days} hari).`;
            } else if (data.state === "pending") {
                icon = "⏳";
                title = `Menunggu pembayaran`;
                detail = `Selesaikan pembayaran untuk melanjutkan pesanan.`;
            }

            orderBanner.className = `order-banner ${data.state}`;
            orderBanner.innerHTML = `
                <div class="order-banner-icon">${icon}</div>
                <div class="order-banner-content">
                    <div class="order-banner-title">
                        ${title} &nbsp; <span class="order-banner-code">${o.order_code}</span>
                    </div>
                    <div class="order-banner-detail">${detail}</div>
                </div>
                ${data.state === "pending"
                    ? `<button style="background:#0d47a1;color:#fff;border:none;
                          padding:8px 16px;border-radius:6px;cursor:pointer;font-size:0.85rem;">
                          Bayar Sekarang
                       </button>`
                    : ""}
            `;
            orderBanner.style.display = "block";
        }

        // ---------------------------------------------------------------------
        // Render: pemetik grid
        // ---------------------------------------------------------------------
        function renderPemetik(list) {
            if (!list || list.length === 0) {
                emptyState.style.display = "block";
                grid.innerHTML = "";
                return;
            }

            emptyState.style.display = "none";

            grid.innerHTML = list.map(p => `
                <div class="pemetik-card" data-id="${p.id}">
                    <div class="check-mark">✓</div>
                    <div class="pemetik-photo">${fotoThumb(p.foto_path)}</div>
                    <div class="pemetik-name">${escapeHtml(p.nama)}</div>
                    <div class="pemetik-desc">${escapeHtml(p.deskripsi || "—")}</div>
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
        // Selection
        // ---------------------------------------------------------------------
        function updateSelection() {
            selectedCount.textContent = selectedIds.size;
            actionCount.textContent = selectedIds.size;

            if (selectedIds.size > 0) {
                actionBar.style.display = "flex";
                document.body.style.paddingBottom = "80px";  // make room for sticky bar
            } else {
                actionBar.style.display = "none";
                document.body.style.paddingBottom = "0";
            }

            document.querySelectorAll(".pemetik-card").forEach(card => {
                const id = parseInt(card.dataset.id, 10);
                card.classList.toggle("selected", selectedIds.has(id));
            });
        }

        grid.addEventListener("click", (e) => {
            const card = e.target.closest(".pemetik-card");
            if (!card) return;
            const id = parseInt(card.dataset.id, 10);
            if (selectedIds.has(id)) {
                selectedIds.delete(id);
            } else {
                selectedIds.add(id);
            }
            updateSelection();
        });

        // ---------------------------------------------------------------------
        // Continue
        // ---------------------------------------------------------------------
        btnLanjut.addEventListener("click", () => {
            if (selectedIds.size === 0) return;

            // Save selection to sessionStorage for the booking page
            sessionStorage.setItem(
                "booking_pemetik_ids",
                JSON.stringify(Array.from(selectedIds))
            );

            window.location.href = "/user/booking/new";
        });

        // ---------------------------------------------------------------------
        // On load
        // ---------------------------------------------------------------------
        (async () => {
            try {
                const [pemetikData, orderData] = await Promise.all([
                    fetchPemetik(),
                    fetchCurrentOrder(),
                ]);

                pricePerDay = pemetikData.price_per_day || 0;
                priceDisplay.textContent = formatRupiah(pricePerDay);

                renderPemetik(pemetikData.pemetik);
                renderOrderBanner(orderData);

                updateSelection();
            } catch (err) {
                console.error("Failed to load page data:", err);
                emptyState.textContent = "Gagal memuat data. Coba refresh halaman.";
                emptyState.style.display = "block";
            }
        })();
    });
})();