import { showAlert } from "./alerts.js"

// ── API Keys ──────────────────────────────────────────────────────────────────

const createKeyBtn = document.getElementById("create-key-btn");
if (createKeyBtn) {
  createKeyBtn.addEventListener("click", async () => {
    const label = document.getElementById("key-label").value.trim();
    const resp = await fetch("/admin/api/keys/create", {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({ label }),
    });
    const data = await resp.json();
    if (!data.key) { showAlert("Failed to create key.", "danger"); return; }

    document.getElementById("new-key-value").textContent = data.key;
    document.getElementById("new-key-alert").classList.remove("d-none");
    document.getElementById("key-label").value = "";

    const tbody = document.querySelector("#keys-table tbody");
    const emptyRow = document.getElementById("keys-empty-row");
    if (emptyRow) emptyRow.remove();
    const row = document.createElement("tr");
    row.id = `key-row-${data.id}`;
    row.innerHTML = `
      <td class="font-monospace small"></td>
      <td></td>
      <td class="small">${new Date().toISOString().slice(0, 10)}</td>
      <td class="small">Never</td>
      <td>0</td>
      <td><span class="badge bg-success">Active</span></td>
      <td><button class="btn btn-sm btn-outline-danger revoke-btn" data-id="${data.id}">Revoke</button></td>`;
    // The prefix and label cells carry server-echoed text, so they are set
    // via textContent to match the escaping the server-rendered rows get.
    const prefixLink = document.createElement("a");
    prefixLink.href = `/admin/api?key=${encodeURIComponent(data.prefix)}`;
    prefixLink.title = "View this key's requests";
    prefixLink.textContent = `${data.prefix}…`;
    row.cells[0].appendChild(prefixLink);
    row.cells[1].textContent = data.label || "—";
    tbody.prepend(row);
  });

  document.getElementById("copy-key-btn").addEventListener("click", () => {
    navigator.clipboard.writeText(document.getElementById("new-key-value").textContent);
    const btn = document.getElementById("copy-key-btn");
    btn.innerHTML = '<i class="bi bi-clipboard-check"></i> Copied!';
    setTimeout(() => { btn.innerHTML = '<i class="bi bi-clipboard"></i> Copy'; }, 2000);
  });

  document.querySelector("#keys-table tbody").addEventListener("click", async (e) => {
    const btn = e.target.closest(".revoke-btn, .delete-btn");
    if (!btn) return;
    const id = btn.dataset.id;

    if (btn.classList.contains("revoke-btn")) {
      if (!confirm("Revoke this key? Any integrations using it will immediately lose access.")) return;
      const resp = await fetch(`/admin/api/keys/${id}/revoke`, { method: "POST" });
      if (!(await resp.json()).success) { showAlert("Failed to revoke key.", "danger"); return; }
      const row = document.getElementById(`key-row-${id}`);
      row.classList.add("text-muted");
      row.querySelector(".badge").className = "badge bg-secondary";
      row.querySelector(".badge").textContent = "Revoked";
      btn.outerHTML = `<button class="btn btn-sm btn-outline-secondary delete-btn" data-id="${id}">Delete</button>`;
    }

    if (btn.classList.contains("delete-btn")) {
      if (!confirm("Permanently delete this key record?")) return;
      const resp = await fetch(`/admin/api/keys/${id}/delete`, { method: "POST" });
      if (!(await resp.json()).success) { showAlert("Failed to delete key.", "danger"); return; }
      document.getElementById(`key-row-${id}`).remove();
      const tbody = document.querySelector("#keys-table tbody");
      if (!tbody.querySelector("tr")) {
        tbody.innerHTML = `<tr id="keys-empty-row"><td colspan="7" class="text-center text-muted py-3">No API keys yet.</td></tr>`;
      }
    }
  });
}

// ── API Keys table: sort + search ─────────────────────────────────────────────

const keysTable = document.getElementById("keys-table");
if (keysTable) {
  let sortCol = -1;
  let sortAsc = true;

  keysTable.querySelectorAll("th.sortable").forEach(th => {
    th.style.cursor = "pointer";
    th.addEventListener("click", () => {
      const col = parseInt(th.dataset.col, 10);
      if (sortCol === col) {
        sortAsc = !sortAsc;
      } else {
        sortCol = col;
        sortAsc = true;
      }
      keysTable.querySelectorAll("th.sortable").forEach(h => {
        h.dataset.sort = "";
      });
      th.dataset.sort = sortAsc ? "asc" : "desc";

      const tbody = keysTable.querySelector("tbody");
      const rows = Array.from(tbody.querySelectorAll("tr:not(#keys-empty-row)"));
      rows.sort((a, b) => {
        const av = a.cells[col]?.textContent.trim() ?? "";
        const bv = b.cells[col]?.textContent.trim() ?? "";
        const an = parseFloat(av);
        const bn = parseFloat(bv);
        let cmp;
        if (!isNaN(an) && !isNaN(bn)) {
          cmp = an - bn;
        } else {
          cmp = av.localeCompare(bv);
        }
        return sortAsc ? cmp : -cmp;
      });
      rows.forEach(r => tbody.appendChild(r));
    });
  });

  document.getElementById("keys-search")?.addEventListener("input", e => {
    const q = e.target.value.toLowerCase();
    const tbody = keysTable.querySelector("tbody");
    tbody.querySelectorAll("tr:not(#keys-empty-row)").forEach(row => {
      const text = Array.from(row.cells).map(c => c.textContent).join(" ").toLowerCase();
      row.style.display = text.includes(q) ? "" : "none";
    });
  });
}
