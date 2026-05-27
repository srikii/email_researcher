const summariesEl = document.querySelector("#summaries");
const resultsEl = document.querySelector("#results");
const processButton = document.querySelector("#process");
const searchButton = document.querySelector("#search");
const queryInput = document.querySelector("#query");
const statusEl = document.querySelector("#status");

async function refreshSummaries() {
  const response = await fetch("/summaries");
  const summaries = await response.json();
  summariesEl.innerHTML = summaries.map(renderSummary).join("") || empty("No summaries yet.");
}

function renderSummary(item) {
  const points = (item.key_points || []).map(point => `<li>${escapeHtml(point)}</li>`).join("");
  return `
    <article class="item">
      <div class="meta">${escapeHtml(item.sender)} • ${escapeHtml(item.date)}</div>
      <h3>${escapeHtml(item.subject)}</h3>
      <p>${escapeHtml(item.short_summary)}</p>
      ${points ? `<ul class="points">${points}</ul>` : ""}
    </article>
  `;
}

function renderResult(item) {
  const meta = item.metadata || {};
  return `
    <article class="item">
      <div class="meta">${escapeHtml(meta.sender || "")} • ${escapeHtml(meta.date || "")}</div>
      <h3>${escapeHtml(meta.subject || "Search hit")}</h3>
      <p>${escapeHtml((item.text || "").slice(0, 500))}</p>
    </article>
  `;
}

function empty(text) {
  return `<div class="item"><p>${escapeHtml(text)}</p></div>`;
}

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "\"": "&quot;",
    "'": "&#039;"
  }[char]));
}

processButton.addEventListener("click", async () => {
  processButton.disabled = true;
  processButton.textContent = "Processing...";
  statusEl.textContent = "Starting graph...";
  const events = new EventSource("/process/stream");

  events.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    if (data.done) {
      statusEl.textContent = "Done. Summaries refreshed.";
      events.close();
      processButton.disabled = false;
      processButton.textContent = "Process Gmail";
      await refreshSummaries();
      return;
    }
    statusEl.textContent = `${data.node}: ${data.emails} emails, ${data.documents} documents, ${data.summaries} summaries`;
    if ((data.errors || []).length) {
      statusEl.textContent += `, ${data.errors.length} errors`;
    }
  };

  events.onerror = () => {
    statusEl.textContent = "Processing stopped. Check the server logs.";
    events.close();
    processButton.disabled = false;
    processButton.textContent = "Process Gmail";
  };
});

searchButton.addEventListener("click", async () => {
  const query = queryInput.value.trim();
  if (!query) return;
  resultsEl.innerHTML = empty("Searching...");
  const response = await fetch("/search", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query, limit: 5})
  });
  const data = await response.json();
  resultsEl.innerHTML = (data.results || []).map(renderResult).join("") || empty("No semantic matches.");
});

refreshSummaries();
