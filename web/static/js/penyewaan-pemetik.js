/* ============================================================
   Penyewaan Pemetik — admin panel
   First paid, first served.
   ============================================================ */
(function () {
    "use strict";

    var $tbody = document.querySelector("#tbl-penyewaan tbody");
    var $counts = document.getElementById("status-counts");
    var $countsText = document.getElementById("counts-text");

    // Cache of the last fetched orders, keyed by id — used by the detail modal.
    var ordersById = {};

    var STATUS_LABEL = {
        pending_payment: { text: "Menunggu Pembayaran", cls: "label-warning" },
        paid: { text: "Sudah Bayar", cls: "label-info" },
        confirmed: { text: "Dikonfirmasi", cls: "label-success" },
        cancelled: { text: "Dibatalkan", cls: "label-danger" },
        completed: { text: "Selesai", cls: "label-default" },
    };

    function rupiah(n) {
        return "Rp " + Number(n || 0).toLocaleString("id-ID");
    }

    function esc(s) {
        var d = document.createElement("div");
        d.textContent = s == null ? "" : String(s);
        return d.innerHTML;
    }

    function badge(status) {
        var b = STATUS_LABEL[status] || { text: status, cls: "label-default" };
        return '<span class="label ' + b.cls + '">' + esc(b.text) + "</span>";
    }

    function pemetikHtml(list) {
        if (!list || !list.length) return '<em class="text-muted">—</em>';
        return list.map(function (p) { return "<div>" + esc(p.nama) + "</div>"; }).join("");
    }

    function actionButtons(o) {
        var btns = [
            '<button class="btn btn-xs btn-default js-detail" data-id="' +
            o.id + '"><i class="fa fa-eye"></i> Detail</button>'
        ];
        if (o.status === "pending_payment") {
            btns.push(
                '<button class="btn btn-xs btn-info js-markpaid" data-id="' +
                o.id + '" data-code="' + esc(o.order_code) + '">' +
                '<i class="fa fa-money"></i> Tandai Lunas</button>'
            );
        }
        if (o.status === "paid") {
            btns.push(
                '<button class="btn btn-xs btn-success js-approve" data-id="' +
                o.id + '" data-code="' + esc(o.order_code) + '">' +
                '<i class="fa fa-check"></i> Setujui</button>'
            );
        }
        if (o.status === "pending_payment" || o.status === "paid") {
            btns.push(
                '<button class="btn btn-xs btn-danger js-cancel" data-id="' +
                o.id + '" data-code="' + esc(o.order_code) + '">' +
                '<i class="fa fa-times"></i> Batal</button>'
            );
        }
        return btns.join(" ");
    }

    function rowHtml(o) {
        var range = (o.start_date || "?") + " &rarr; " + (o.end_date || "?");
        var cancelNote = "";
        if (o.status === "cancelled" && o.cancel_reason) {
            cancelNote =
                '<div class="text-danger" style="font-size:11px;margin-top:4px;">' +
                esc(o.cancel_reason) + "</div>";
        }
        return (
            "<tr>" +
            "<td><strong>" + esc(o.order_code) + "</strong>" +
            (o.notes
                ? '<div class="text-muted" style="font-size:11px;">' + esc(o.notes) + "</div>"
                : "") + "</td>" +
            "<td>" + esc(o.user_nama) +
            '<div class="text-muted" style="font-size:11px;">' +
            esc(o.user_telepon) + "</div></td>" +
            "<td>" + pemetikHtml(o.pemetik) + "</td>" +
            "<td>" + range +
            '<div class="text-muted" style="font-size:11px;">' +
            (o.total_days || "?") + " hari</div></td>" +
            "<td>" + rupiah(o.total_amount) + "</td>" +
            "<td>" + badge(o.status) + cancelNote + "</td>" +
            "<td>" + actionButtons(o) + "</td>" +
            "</tr>"
        );
    }

    function renderCounts(counts) {
        if (!counts) return;
        var parts = [];
        ["pending_payment", "paid", "confirmed", "cancelled", "completed"].forEach(function (k) {
            if (counts[k]) {
                parts.push((STATUS_LABEL[k] || { text: k }).text + ": " + counts[k]);
            }
        });
        parts.push("Total: " + (counts.total || 0));
        $countsText.textContent = parts.join(" | ");
        $counts.style.display = "block";
    }

    function fetchOrders() {
        var status = document.getElementById("filter-status").value;
        var q = document.getElementById("filter-q").value.trim();

        var url = "/api/admin/penyewaan?";
        if (status) url += "status=" + encodeURIComponent(status) + "&";
        if (q) url += "q=" + encodeURIComponent(q) + "&";

        fetch(url, { credentials: "same-origin" })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data.error) {
                    swal("Gagal", data.error, "error");
                    return;
                }
                var orders = data.orders || [];
                ordersById = {};
                orders.forEach(function (o) { ordersById[o.id] = o; });

                if (!orders.length) {
                    $tbody.innerHTML =
                        '<tr><td colspan="7" class="text-center text-muted">' +
                        "Tidak ada data.</td></tr>";
                } else {
                    $tbody.innerHTML = orders.map(rowHtml).join("");
                }
                renderCounts(data.counts);
            })
            .catch(function (err) {
                console.error(err);
                swal("Error", "Gagal memuat data penyewaan.", "error");
            });
    }

        /* ------- mark paid ------- */
    function markPaid(id, code) {
        swal({
            title: "Tandai order lunas?",
            text: "Order " + code + " akan berubah dari 'Menunggu Pembayaran' menjadi 'Sudah Bayar'.",
            type: "info",
            showCancelButton: true,
            confirmButtonText: "Ya, tandai lunas",
            cancelButtonText: "Batal",
        }, function (ok) {
            if (!ok) return;
            
            fetch("/api/admin/penyewaan/" + id + "/mark-paid", {
                method: "POST",
                credentials: "same-origin",
            })
                .then(function (r) { 
                    // We parse JSON even if status is 409, so we get the error message
                    return r.json().then(function(data) {
                        return { status: r.status, data: data };
                    });
                })
                .then(function (result) {
                    if (result.status === 409 || result.data.error) {
                        // THIS IS THE MAGIC: Show the error, then instantly refresh the table
                        swal("Dibatalkan Otomatis", result.data.error, "error");
                        fetchOrders(); // <--- THIS makes the table update to Image 2 immediately!
                        return;
                    }
                    
                    // Success
                    swal("Berhasil", result.data.message, "success");
                    fetchOrders();
                })
                .catch(function (err) {
                    console.error(err);
                    swal("Error", "Gagal menandai lunas. Periksa koneksi server.", "error");
                });
        });
    }
    

    /* ------- approve ------- */
    function approveOrder(id, code) {
        swal({
            title: "Setujui order?",
            text: "Order " + code + " akan dikonfirmasi. Order lain yang bentrok " +
                "(pemetik & tanggal sama) akan otomatis dibatalkan.",
            type: "warning",
            showCancelButton: true,
            confirmButtonText: "Ya, setujui",
            cancelButtonText: "Batal",
        }, function (ok) {
            if (!ok) return;
            fetch("/api/admin/penyewaan/" + id + "/approve", {
                method: "POST",
                credentials: "same-origin",
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.error) { swal("Tidak bisa disetujui", data.error, "error"); return; }
                    var extra = "";
                    if (data.cancelled && data.cancelled.length) {
                        extra = "\n\nDibatalkan: " +
                            data.cancelled.map(function (c) { return c.order_code; }).join(", ");
                    }
                    swal("Berhasil", data.message + extra, "success");
                    fetchOrders();
                })
                .catch(function () {
                    swal("Error", "Gagal menyetujui order.", "error");
                });
        });
    }

    /* ------- cancel (with reason) ------- */
    function cancelOrder(id, code) {
        swal({
            title: "Batalkan order " + code + "?",
            text: "Alasan pembatalan:",
            type: "input",
            showCancelButton: true,
            confirmButtonText: "Batalkan",
            cancelButtonText: "Tutup",
            closeOnConfirm: false,
        }, function (reason) {
            if (reason === false) return;
            reason = (reason || "").trim() || "Dibatalkan oleh admin.";
            fetch("/api/admin/penyewaan/" + id + "/cancel", {
                method: "POST",
                credentials: "same-origin",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ reason: reason }),
            })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data.error) { swal("Gagal", data.error, "error"); return; }
                    swal("Dibatalkan", data.message, "success");
                    fetchOrders();
                })
                .catch(function () {
                    swal("Error", "Gagal membatalkan order.", "error");
                });
        });
    }

    /* ------- detail modal ------- */
    function showDetail(id) {
        console.log("Detail clicked for order id", id);
        var o = ordersById[id];
        if (!o) { swal("Tidak ditemukan", "Order tidak ditemukan.", "error"); return; }

        var pemetikRows = (o.pemetik || []).map(function (p) {
            return (
                "<tr><td>" + esc(p.nama) + "</td>" +
                "<td>" + rupiah(p.price_per_day) + "/hari</td>" +
                "<td>" + p.total_days + " hari</td>" +
                "<td>" + rupiah(p.subtotal) + "</td></tr>"
            );
        }).join("");

        document.getElementById("modal-detail-body").innerHTML =
            '<dl class="dl-horizontal">' +
            "<dt>Kode</dt><dd>" + esc(o.order_code) + "</dd>" +
            "<dt>Penyewa</dt><dd>" + esc(o.user_nama) +
            " (" + esc(o.user_telepon) + ")</dd>" +
            "<dt>Tanggal</dt><dd>" + esc(o.start_date) + " &rarr; " +
            esc(o.end_date) + " (" + o.total_days + " hari)</dd>" +
            "<dt>Total</dt><dd>" + rupiah(o.total_amount) + "</dd>" +
            "<dt>Status</dt><dd>" + badge(o.status) + "</dd>" +
            (o.paid_at
                ? "<dt>Dibayar pada</dt><dd>" + esc(o.paid_at) + "</dd>" : "") +
            (o.cancel_reason
                ? "<dt>Alasan batal</dt><dd class='text-danger'>" +
                esc(o.cancel_reason) + "</dd>" : "") +
            (o.notes
                ? "<dt>Catatan</dt><dd>" + esc(o.notes) + "</dd>" : "") +
            "</dl>" +
            "<h5>Pemetik</h5>" +
            '<table class="table table-condensed table-bordered">' +
            "<thead><tr><th>Nama</th><th>Harga/hari</th><th>Hari</th><th>Subtotal</th></tr></thead>" +
            "<tbody>" + (pemetikRows || '<tr><td colspan="4">—</td></tr>') + "</tbody></table>";

        document.getElementById("modal-detail").classList.add("open");
    }

    /* ------- events ------- */
    $tbody.addEventListener("click", function (e) {
        var t = e.target.closest("button");
        if (!t) return;
        var id = parseInt(t.getAttribute("data-id"), 10);
        var code = t.getAttribute("data-code") || "";
        if (t.classList.contains("js-detail")) showDetail(id);
        if (t.classList.contains("js-markpaid")) markPaid(id, code);
        if (t.classList.contains("js-approve")) approveOrder(id, code);
        if (t.classList.contains("js-cancel")) cancelOrder(id, code);
    });

    document.getElementById("btn-refresh").addEventListener("click", fetchOrders);
    document.getElementById("filter-status").addEventListener("change", fetchOrders);
    document.getElementById("filter-q").addEventListener("keydown", function (e) {
        if (e.key === "Enter") fetchOrders();
    });

    fetchOrders();
})();