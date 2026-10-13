/**
 * user-list.js — Admin user list page.
 *
 * Fetches /api/admin/users and renders it in a DataTable.
 * Provides approve/reject/suspend actions per row.
 */

(function () {
    "use strict";

    console.log("🍀 user-list.js loaded");

    // ---------------------------------------------------------------------
    // Fetch users from API
    // ---------------------------------------------------------------------
    async function fetchUsers() {
        const res = await fetch("/api/admin/users");
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}`);
        }
        return res.json();
    }

    // ---------------------------------------------------------------------
    // Render helpers
    // ---------------------------------------------------------------------
    function statusBadge(status) {
        const colors = {
            pending:   { bg: "#fff3cd", fg: "#664d03" },
            active:    { bg: "#e8f5e9", fg: "#1b5e20" },
            rejected:  { bg: "#f8d7da", fg: "#842029" },
            suspended: { bg: "#e2e3e5", fg: "#383d41" },
        };
        const c = colors[status] || colors.suspended;
        return `<span style="display:inline-block; padding:2px 10px; border-radius:10px;
            background:${c.bg}; color:${c.fg}; font-size:0.75rem; font-weight:600;
            text-transform:capitalize;">${status}</span>`;
    }

    function levelBadge(level) {
        const colors = {
            admin: { bg: "#cce5ff", fg: "#004085" },
            user:  { bg: "#f1f3f5", fg: "#495057" },
        };
        const c = colors[level] || colors.user;
        return `<span style="display:inline-block; padding:2px 10px; border-radius:10px;
            background:${c.bg}; color:${c.fg}; font-size:0.75rem; font-weight:600;
            text-transform:capitalize;">${level}</span>`;
    }

    function formatDate(iso) {
        if (!iso) return "—";
        return new Date(iso).toLocaleString("id-ID", {
            year: "numeric", month: "short", day: "2-digit",
            hour: "2-digit", minute: "2-digit",
        });
    }

    function actionButtons(user) {
        const btn = (label, cls, action, color) =>
            `<button class="btn btn-sm" data-action="${action}" data-user-id="${user.id}"
                style="padding:3px 10px; font-size:0.75rem; margin-right:4px;
                border-radius:4px; border:none; cursor:pointer;
                background:${color.bg}; color:${color.fg};">${label}</button>`;

        const actions = [];

        if (user.status === "pending") {
            actions.push(btn("Setujui", "", "approve", { bg: "#2d6a4f", fg: "#fff" }));
            actions.push(btn("Tolak",   "", "reject",  { bg: "#f8d7da", fg: "#842029" }));
        }
        if (user.status === "active" && user.level !== "admin") {
            actions.push(btn("Tangguhkan", "", "suspend", { bg: "#fff3cd", fg: "#664d03" }));
        }
        if (user.status === "suspended") {
            actions.push(btn("Aktifkan", "", "approve", { bg: "#2d6a4f", fg: "#fff" }));
        }
        if (user.status === "rejected") {
            actions.push(btn("Setujui", "", "approve", { bg: "#2d6a4f", fg: "#fff" }));
        }

        return actions.join("") || '<span style="color:#999; font-size:0.8rem;">—</span>';
    }

    // ---------------------------------------------------------------------
    // Main render
    // ---------------------------------------------------------------------
    let dataTable = null;

    async function loadUsers() {
        try {
            const data = await fetchUsers();

            // Update counts
            document.getElementById("count-pending").textContent   = data.counts.pending   || 0;
            document.getElementById("count-active").textContent    = data.counts.active    || 0;
            document.getElementById("count-rejected").textContent  = data.counts.rejected  || 0;
            document.getElementById("count-suspended").textContent = data.counts.suspended || 0;

            // Prepare rows for DataTables
            const rows = data.users.map(u => [
                u.nomor_telepon,
                u.nama,
                levelBadge(u.level),
                statusBadge(u.status),
                formatDate(u.created_at),
                formatDate(u.last_login_at),
                actionButtons(u),
            ]);

            // Init or update the DataTable
            if (dataTable) {
                dataTable.clear().rows.add(rows).draw();
            } else {
                dataTable = $("#users-table").DataTable({
                    data: rows,
                    order: [[4, "desc"]],        // sort by created_at
                    pageLength: 25,
                    language: {
                        search: "Cari:",
                        lengthMenu: "Tampilkan _MENU_ baris",
                        info: "Menampilkan _START_–_END_ dari _TOTAL_",
                        infoEmpty: "Tidak ada data",
                        zeroRecords: "Tidak ada pengguna yang cocok",
                        paginate: {
                            first: "Pertama",
                            last: "Terakhir",
                            next: "Berikut",
                            previous: "Sebelum",
                        },
                    },
                    columnDefs: [
                        { orderable: false, targets: [2, 3, 6] },
                    ],
                });
            }
        } catch (err) {
            console.error("Failed to load users:", err);
            $("#users-table").html('<tbody><tr><td colspan="7">Gagal memuat data.</td></tr></tbody>');
        }
    }

    // ---------------------------------------------------------------------
    // Action handler (delegated — works for dynamically-added rows)
    // ---------------------------------------------------------------------
    $(document).on("click", "[data-action]", async function () {
        const $btn    = $(this);
        const action  = $btn.data("action");
        const userId  = $btn.data("user-id");

        const labels = { approve: "Setujui", reject: "Tolak", suspend: "Tangguhkan" };
        const confirmMsg = `Yakin ingin ${labels[action].toLowerCase()} pengguna ini?`;

        if (!confirm(confirmMsg)) return;

        $btn.prop("disabled", true).text("Memproses...");

        try {
            const res = await fetch(`/api/admin/${action}/${userId}`, { method: "POST" });
            const data = await res.json();

            if (res.ok) {
                await loadUsers();   // refresh table
            } else {
                alert(data.error || "Aksi gagal.");
                $btn.prop("disabled", false).text(labels[action]);
            }
        } catch (err) {
            console.error("Action failed:", err);
            alert("Terjadi kesalahan teknis.");
            $btn.prop("disabled", false).text(labels[action]);
        }
    });

    // ---------------------------------------------------------------------
    // On load
    // ---------------------------------------------------------------------
    loadUsers();
})();