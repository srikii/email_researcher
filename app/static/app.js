// Grab the page elements once so the rest of the code can reuse them.
const summariesEl = document.querySelector("#summaries");
const resultsEl = document.querySelector("#results");
const processButton = document.querySelector("#process");
const searchButton = document.querySelector("#search");
const queryInput = document.querySelector("#query");
const statusEl = document.querySelector("#status");
const sinceInput = document.querySelector("#since");
const untilInput = document.querySelector("#until");
const viewRangeButton = document.querySelector("#view-range");
const processRangeButton = document.querySelector("#process-range");

function setDefaultRange() {
  // Default the range picker to "today from midnight until now".
  const now = new Date();
  const start = new Date(now);
  start.setHours(0, 0, 0, 0);

  sinceInput.value = toDateTimeLocal(start);
  untilInput.value = toDateTimeLocal(now);
}

function toDateTimeLocal(date) {
  // datetime-local inputs need a value like 2026-05-27T09:30.
  const year = date.getFullYear();
  const month = padTwoDigits(date.getMonth() + 1);
  const day = padTwoDigits(date.getDate());
  const hour = padTwoDigits(date.getHours());
  const minute = padTwoDigits(date.getMinutes());

  return `${year}-${month}-${day}T${hour}:${minute}`;
}

function padTwoDigits(value) {
  return String(value).padStart(2, "0");
}

function rangeParams() {
  // Convert the range form into URL query parameters.
  const params = new URLSearchParams();

  if (sinceInput.value) {
    params.set("since", sinceInput.value);
  }

  if (untilInput.value) {
    params.set("until", untilInput.value);
  }

  return params;
}

async function refreshSummaries(params = new URLSearchParams()) {
  // Load summaries from the backend. If params are provided, only show that range.
  let url = "/summaries";
  if (params.toString()) {
    url = `/summaries?${params}`;
  }

  const response = await fetch(url);
  const summaries = await response.json();

  let html = "";
  for (const summary of summaries) {
    html += renderSummary(summary);
  }

  summariesEl.innerHTML = html || empty("No summaries yet.");
}

function renderSummary(item) {
  let pointsHtml = "";
  const keyPoints = item.key_points || [];

  for (const point of keyPoints) {
    pointsHtml += `<li>${escapeHtml(point)}</li>`;
  }

  let listHtml = "";
  if (pointsHtml) {
    listHtml = `<ul class="points">${pointsHtml}</ul>`;
  }

  return `
    <article class="item">
      <div class="meta">${escapeHtml(item.sender)} - received ${escapeHtml(item.received_at || item.date)}</div>
      <h3>${escapeHtml(item.subject)}</h3>
      <p>${escapeHtml(item.short_summary)}</p>
      ${listHtml}
    </article>
  `;
}

function renderResult(item) {
  const meta = item.metadata || {};
  const textPreview = String(item.text || "").slice(0, 500);

  return `
    <article class="item">
      <div class="meta">${escapeHtml(meta.sender || "")} - ${escapeHtml(meta.received_at || meta.date || "")}</div>
      <h3>${escapeHtml(meta.subject || "Search hit")}</h3>
      <p>${escapeHtml(textPreview)}</p>
    </article>
  `;
}

function empty(text) {
  return `<div class="item"><p>${escapeHtml(text)}</p></div>`;
}

function escapeHtml(value) {
  // Never inject raw text into HTML. This prevents broken layouts and XSS bugs.
  const text = String(value);
  return text.replace(/[&<>"']/g, char => {
    const replacements = {
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      "\"": "&quot;",
      "'": "&#039;"
    };
    return replacements[char];
  });
}

processButton.addEventListener("click", async () => {
  // Normal processing uses the saved backend cursor and does not backfill old mail.
  processButton.disabled = true;
  processButton.textContent = "Processing...";
  statusEl.textContent = "Starting graph from saved cursor...";

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

    if (data.node === "cursor") {
      statusEl.textContent = `Processing new email since ${data.since}`;
      return;
    }

    updateGraphStatus(data);
  };

  events.onerror = () => {
    statusEl.textContent = "Processing stopped. Check the server logs.";
    events.close();
    processButton.disabled = false;
    processButton.textContent = "Process Gmail";
  };
});

viewRangeButton.addEventListener("click", async () => {
  // This only reads summaries that already exist in SQLite.
  statusEl.textContent = "Showing summaries in selected range.";
  await refreshSummaries(rangeParams());
});

processRangeButton.addEventListener("click", async () => {
  // This intentionally processes a selected range, useful for today's digest
  // or a one-time backfill.
  processRangeButton.disabled = true;
  processRangeButton.textContent = "Processing...";
  statusEl.textContent = "Processing selected range...";

  const params = rangeParams();
  const events = new EventSource(`/process/stream?${params}`);

  events.onmessage = async (event) => {
    const data = JSON.parse(event.data);

    if (data.done) {
      statusEl.textContent = "Range processed. Summaries refreshed.";
      events.close();
      processRangeButton.disabled = false;
      processRangeButton.textContent = "Process Range";
      await refreshSummaries(params);
      return;
    }

    if (data.node === "cursor") {
      statusEl.textContent = `Processing from ${data.since || "start"} to ${data.until || "now"}`;
      return;
    }

    updateGraphStatus(data);
  };

  events.onerror = () => {
    statusEl.textContent = "Range processing stopped. Check the server logs.";
    events.close();
    processRangeButton.disabled = false;
    processRangeButton.textContent = "Process Range";
  };
});

searchButton.addEventListener("click", async () => {
  const query = queryInput.value.trim();
  if (!query) {
    return;
  }

  resultsEl.innerHTML = empty("Searching...");

  const response = await fetch("/search", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({query, limit: 5})
  });

  const data = await response.json();
  const results = data.results || [];

  let html = "";
  for (const result of results) {
    html += renderResult(result);
  }

  resultsEl.innerHTML = html || empty("No semantic matches.");
});

function updateGraphStatus(data) {
  statusEl.textContent = `${data.node}: ${data.emails} emails, ${data.documents} documents, ${data.summaries} summaries`;

  const errors = data.errors || [];
  if (errors.length) {
    statusEl.textContent += `, ${errors.length} errors`;
  }
}

setDefaultRange();
refreshSummaries();
