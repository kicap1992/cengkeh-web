/**
 * pemetik-list.js — Admin page to list, create, edit, delete pemetik.
 */

(function () {
    "use strict";

    document.addEventListener("DOMContentLoaded", () => {
        console.log("🍀 pemetik-list.js loaded");

        let dataTable = null;

        // Form state
        let uploadedFotoPath = null;    // set after successful upload (create or edit)
        let currentEditId = null;    // null when creating, N when editing

        // ---------------------------------------------------------------------
        // API helpers
        // ---------------------------------------------------------------------
        async function apiFetch(url, options = {}) {
            const res = await fetch(url, options);
            const data = await res.json().catch(() => ({}));
            return { ok: res.ok, status: res.status, data };
        }

        // ---------------------------------------------------------------------
        // Table rendering
        // ---------------------------------------------------------------------
        function fotoThumb(path) {
            if (!path) {
                return `<div style="width:40px;height:40px;border-radius:50%;
                    background:#e8f5e9;display:flex;align-items:center;
                    justify-content:center;color:#2d6a4f;font-weight:700;">👤</div>`;
            }
            return `<img src="/static/${path}" alt=""
                    style="width:40px;height:40px;border-radius:50%;object-fit:cover;"
                    onerror="this.style.display='none';this.parentNode.innerHTML='👤';">`;
        }

        function statusBadge(isActive) {
            return isActive
                ? `<span style="display:inline-block;padding:2px 10px;border-radius:10px;
                    background:#e8f5e9;color:#1b5e20;font-size:0.75rem;font-weight:600;">Aktif</span>`
                : `<span style="display:inline-block;padding:2px 10px;border-radius:10px;
                    background:#e2e3e5;color:#383d41;font-size:0.75rem;font-weight:600;">Tidak Aktif</span>`;
        }

        function actionButtons(p) {
            const toggleLabel = p.is_active ? "Nonaktifkan" : "Aktifkan";
            const toggleStyle = p.is_active
                ? "background:#fff3cd;color:#664d03;"   // amber for "deactivate"
                : "background:#e8f5e9;color:#1b5e20;";  // green for "activate"

            return `
        <button class="btn btn-sm btn-edit" data-id="${p.id}"
                style="padding:3px 10px;font-size:0.75rem;border:none;
                       background:#cce5ff;color:#004085;border-radius:4px;
                       cursor:pointer;margin-right:4px;">
            Edit
        </button>
        <button class="btn btn-sm btn-toggle" data-id="${p.id}" data-nama="${p.nama}" data-active="${p.is_active}"
                style="padding:3px 10px;font-size:0.75rem;border:none;
                       ${toggleStyle}border-radius:4px;cursor:pointer;">
            ${toggleLabel}
        </button>
    `;
        }

        async function loadPemetik() {
            try {
                const { ok, data } = await apiFetch("/api/admin/pemetik");
                if (!ok) throw new Error(`HTTP ${status}`);

                const total = data.pemetik.length;
                const actives = data.pemetik.filter(p => p.is_active).length;
                document.getElementById("count-active").textContent = actives;
                document.getElementById("count-inactive").textContent = total - actives;

                const rows = data.pemetik.map(p => [
                    fotoThumb(p.foto_path),
                    p.nama,
                    p.deskripsi
                        ? (p.deskripsi.length > 60 ? p.deskripsi.slice(0, 60) + "..." : p.deskripsi)
                        : '<span style="color:#999;">—</span>',
                    p.nomor_telepon || '<span style="color:#999;">—</span>',
                    statusBadge(p.is_active),
                    actionButtons(p),
                ]);

                if (dataTable) {
                    dataTable.clear().rows.add(rows).draw();
                } else {
                    dataTable = $("#pemetik-table").DataTable({
                        data: rows,
                        pageLength: 25,
                        order: [[1, "asc"]],
                        language: {
                            search: "Cari:",
                            lengthMenu: "Tampilkan _MENU_ baris",
                            info: "Menampilkan _START_–_END_ dari _TOTAL_",
                            infoEmpty: "Tidak ada data",
                            zeroRecords: "Tidak ada pemetik yang cocok",
                            paginate: {
                                first: "Pertama", last: "Terakhir",
                                next: "Berikut", previous: "Sebelum",
                            },
                        },
                        columnDefs: [{ orderable: false, targets: [0, 2, 5] }],
                    });
                }
            } catch (err) {
                console.error("Failed to load pemetik:", err);
                $("#pemetik-table").html(
                    '<tbody><tr><td colspan="6">Gagal memuat data.</td></tr></tbody>'
                );
            }
        }

        // ---------------------------------------------------------------------
        // Modal references
        // ---------------------------------------------------------------------
        const modal = document.getElementById("add-modal");
        const modalTitle = document.querySelector(".modal-title");
        const errBox = document.getElementById("add-error");
        const inNama = document.getElementById("add-nama");
        const inDeskripsi = document.getElementById("add-deskripsi");
        const inNomor = document.getElementById("add-nomor");
        const fileInput = document.getElementById("add-foto-input");
        const btnChoose = document.getElementById("btn-choose-photo");
        const preview = document.getElementById("photo-preview");
        const uploadStatus = document.getElementById("upload-status");
        const btnSave = document.getElementById("btn-save-add");

        // ---------------------------------------------------------------------
        // Modal open / close / reset
        // ---------------------------------------------------------------------
        function resetModal() {
            inNama.value = "";
            inDeskripsi.value = "";
            inNomor.value = "";
            fileInput.value = "";
            uploadedFotoPath = null;
            preview.innerHTML = "<span>👤</span>";
            uploadStatus.textContent = "";
            uploadStatus.className = "upload-status";
            errBox.classList.remove("open");
            errBox.textContent = "";
        }

        function openCreateModal() {
            currentEditId = null;
            resetModal();
            modalTitle.textContent = "Tambah Pemetik";
            btnSave.textContent = "Simpan";
            modal.classList.add("open");
            inNama.focus();
        }

        async function openEditModal(id) {
            resetModal();
            modalTitle.textContent = "Edit Pemetik";
            btnSave.textContent = "Simpan Perubahan";
            currentEditId = id;

            // Fetch the fresh data
            const { ok, data } = await apiFetch(`/api/admin/pemetik/${id}`);
            if (!ok) {
                alert(data.error || "Gagal memuat data pemetik.");
                currentEditId = null;
                return;
            }

            const p = data.pemetik;
            inNama.value = p.nama;
            inDeskripsi.value = p.deskripsi;
            inNomor.value = p.nomor_telepon;

            if (p.foto_path) {
                uploadedFotoPath = p.foto_path;
                preview.innerHTML = `<img src="/static/${p.foto_path}" alt="">`;
            }

            modal.classList.add("open");
            inNama.focus();
        }

        function closeModal() {
            modal.classList.remove("open");
        }

        function showError(msg) {
            errBox.textContent = msg;
            errBox.classList.add("open");
        }

        // ---------------------------------------------------------------------
        // Button bindings
        // ---------------------------------------------------------------------
        document.getElementById("btn-add-pemetik").addEventListener("click", openCreateModal);
        document.getElementById("btn-cancel-add").addEventListener("click", closeModal);

        modal.addEventListener("click", (e) => {
            if (e.target === modal) closeModal();
        });

        document.addEventListener("keydown", (e) => {
            if (e.key === "Escape" && modal.classList.contains("open")) closeModal();
        });

        // Force numeric on phone input
        inNomor.addEventListener("input", (e) => {
            e.target.value = e.target.value.replace(/\D/g, "").slice(0, 15);
        });

        // Delegated click handlers for table action buttons
        document.addEventListener("click", async (e) => {
            const editBtn = e.target.closest(".btn-edit");
            if (editBtn) {
                const id = parseInt(editBtn.dataset.id, 10);
                await openEditModal(id);
                return;
            }

            const toggleBtn = e.target.closest(".btn-toggle");
            if (toggleBtn) {
                const id = parseInt(toggleBtn.dataset.id, 10);
                const nama = toggleBtn.dataset.nama;
                const active = toggleBtn.dataset.active === "true";

                const question = active
                    ? `Nonaktifkan pemetik "${nama}"? Mereka tidak akan muncul untuk pemesanan baru, tetapi data dan foto tetap tersimpan.`
                    : `Aktifkan kembali pemetik "${nama}"?`;

                if (!confirm(question)) return;

                const { ok, data } = await apiFetch(`/api/admin/pemetik/${id}/toggle`, {
                    method: "POST",
                });
                if (ok) {
                    await loadPemetik();
                } else {
                    alert(data.error || "Gagal mengubah status.");
                }
                return;
            }

        });

        // ---------------------------------------------------------------------
        // Photo upload
        // ---------------------------------------------------------------------
        btnChoose.addEventListener("click", () => fileInput.click());

        fileInput.addEventListener("change", async () => {
            const file = fileInput.files[0];
            if (!file) return;

            uploadStatus.textContent = "Mengunggah...";
            uploadStatus.className = "upload-status";
            btnChoose.disabled = true;

            try {
                const fd = new FormData();
                fd.append("file", file);

                const res = await fetch("/api/admin/pemetik/upload", {
                    method: "POST",
                    body: fd,
                });
                const data = await res.json();

                if (res.ok) {
                    uploadedFotoPath = data.foto_path;
                    preview.innerHTML = `<img src="/static/${data.foto_path}" alt="">`;
                    uploadStatus.textContent = "✅ Foto berhasil diunggah.";
                    uploadStatus.className = "upload-status";
                } else {
                    uploadStatus.textContent = data.error || "Gagal mengunggah.";
                    uploadStatus.className = "upload-status error";
                    uploadedFotoPath = null;
                }
            } catch (err) {
                console.error("Upload failed:", err);
                uploadStatus.textContent = "Terjadi kesalahan saat mengunggah.";
                uploadStatus.className = "upload-status error";
                uploadedFotoPath = null;
            } finally {
                btnChoose.disabled = false;
            }
        });

        // ---------------------------------------------------------------------
        // Save (create or update)
        // ---------------------------------------------------------------------
        btnSave.addEventListener("click", async () => {
            errBox.classList.remove("open");

            const nama = inNama.value.trim();
            if (nama.length < 2) {
                showError("Nama minimal 2 karakter.");
                return;
            }

            btnSave.disabled = true;
            btnSave.textContent = "Menyimpan...";

            const payload = {
                nama: nama,
                deskripsi: inDeskripsi.value.trim(),
                nomor_telepon: inNomor.value.trim(),
            };

            // Include foto_path only if the user uploaded a new one (or it's the current one)
            if (uploadedFotoPath) {
                payload.foto_path = uploadedFotoPath;
            }

            let result;
            if (currentEditId === null) {
                // Create
                result = await apiFetch("/api/admin/pemetik", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
            } else {
                // Update
                result = await apiFetch(`/api/admin/pemetik/${currentEditId}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload),
                });
            }

            btnSave.disabled = false;
            btnSave.textContent = currentEditId === null ? "Simpan" : "Simpan Perubahan";

            if (result.ok) {
                closeModal();
                await loadPemetik();
            } else {
                showError(result.data.error || "Gagal menyimpan.");
            }
        });

        // ---------------------------------------------------------------------
        // On load
        // ---------------------------------------------------------------------
        loadPemetik();
    });
})();