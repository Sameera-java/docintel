const API_BASE = "/api/v1";

function renderValue(v) {
  if (v === null || v === undefined) return `<span class="value-missing">missing</span>`;
  if (typeof v === "object") return JSON.stringify(v);
  return v;
}

async function loadResult() {
  const res = await fetch(`${API_BASE}/documents/${encodeURIComponent(DOCUMENT_NAME)}`);
  if (!res.ok) {
    document.getElementById("summary-card").innerHTML = "<p>Document not found.</p>";
    return;
  }
  const data = await res.json();
  document.getElementById("doc-title").textContent = data.document_name;

  document.getElementById("summary-card").innerHTML = `
    <h2>Summary</h2>
    <p><b>Type:</b> ${data.document_type}</p>
    <p><b>Status:</b> <span class="status-pill status-${data.processing_status}">${data.processing_status}</span></p>
    <p><b>OCR used:</b> ${data.processing_metadata?.ocr_used ?? "-"}</p>
    <p><b>Processed at:</b> ${data.processing_metadata?.processed_at ?? "-"}</p>
    ${data.error_message ? `<p><b>Error:</b> ${data.error_message}</p>` : ""}
  `;

  const fieldsBody = document.getElementById("fields-table-body");
  const fieldEntries = Object.entries(data.extracted_data || {}).filter(([k]) => !k.startsWith("table:"));
  fieldsBody.innerHTML = fieldEntries.length
    ? fieldEntries.map(([name, f]) => `
        <tr>
          <td>${name}</td>
          <td>${renderValue(f?.value)}</td>
          <td>${f?.source_text ?? "-"}</td>
          <td>${f?.page_number ?? "-"}</td>
        </tr>
      `).join("")
    : `<tr><td colspan="4">No fields extracted.</td></tr>`;

  const tableEntries = Object.entries(data.extracted_data || {}).filter(([k]) => k.startsWith("table:"));
  const tablesSection = document.getElementById("tables-section");
  if (tableEntries.length) {
    tablesSection.innerHTML = tableEntries.map(([key, rows]) => {
      const name = key.replace("table:", "");
      if (!Array.isArray(rows) || !rows.length) return `<h2>${name}</h2><p>No rows.</p>`;
      const cols = Object.keys(rows[0]);
      return `
        <h2>${name}</h2>
        <table>
          <thead><tr>${cols.map(c => `<th>${c}</th>`).join("")}</tr></thead>
          <tbody>
            ${rows.map(r => `<tr>${cols.map(c => `<td>${renderValue(r[c])}</td>`).join("")}</tr>`).join("")}
          </tbody>
        </table>
      `;
    }).join("");
  } else {
    tablesSection.innerHTML = "<h2>Tables</h2><p>No tables extracted.</p>";
  }

  const validationBody = document.getElementById("validation-table-body");
  const checks = data.validation?.checks || [];
  validationBody.innerHTML = checks.length
    ? checks.map(c => `
        <tr>
          <td>${c.name}</td>
          <td>${c.formula}</td>
          <td>${renderValue(c.calculated_value)}</td>
          <td>${renderValue(c.reported_value)}</td>
          <td>${renderValue(c.variance)}</td>
          <td><span class="status-pill status-${c.status}">${c.status}</span></td>
        </tr>
      `).join("")
    : `<tr><td colspan="6">No validation checks performed.</td></tr>`;

  document.getElementById("raw-json").textContent = JSON.stringify(data, null, 2);
}

loadResult();
