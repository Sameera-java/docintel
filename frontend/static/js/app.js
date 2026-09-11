const API_BASE = "/api/v1";

async function loadDocuments() {
  const tbody = document.getElementById("doc-table-body");
  try {
    const res = await fetch(`${API_BASE}/documents`);
    const docs = await res.json();
    if (!docs.length) {
      tbody.innerHTML = `<tr><td colspan="5">No documents processed yet.</td></tr>`;
      return;
    }
    tbody.innerHTML = docs.map(d => `
      <tr>
        <td>${d.document_name}</td>
        <td>${d.document_type}</td>
        <td><span class="status-pill status-${d.processing_status}">${d.processing_status}</span></td>
        <td>${new Date(d.processed_at).toLocaleString()}</td>
        <td><a class="row-link" href="/document/${encodeURIComponent(d.document_name)}">View →</a></td>
      </tr>
    `).join("");
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5">Failed to load documents.</td></tr>`;
  }
}

document.getElementById("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fileInput = document.getElementById("file");
  const docType = document.getElementById("document_type").value;
  const statusEl = document.getElementById("upload-status");
  const btn = document.getElementById("submit-btn");

  if (!fileInput.files.length) return;

  const formData = new FormData();
  formData.append("file", fileInput.files[0]);
  formData.append("document_type", docType);

  btn.disabled = true;
  statusEl.textContent = "Processing... this can take a few seconds.";

  try {
    const res = await fetch(`${API_BASE}/documents/process`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) {
      statusEl.textContent = `Error: ${data.error?.message || "Processing failed."}`;
    } else {
      statusEl.textContent = `Done — status: ${data.processing_status}.`;
      await loadDocuments();
    }
  } catch (err) {
    statusEl.textContent = "Network error while processing document.";
  } finally {
    btn.disabled = false;
  }
});

loadDocuments();
