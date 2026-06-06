import { api } from "./api.js";
import { collectFiltersFromForm, inboxState } from "./inbox.js";

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return date.toLocaleString();
}

function buildFilterPayload() {
  collectFiltersFromForm();
  const { q, userIds, chatType, direction, topics, dateFrom, dateTo } = inboxState.filters;
  return {
    q: q || undefined,
    user_ids: userIds.length ? userIds.join(",") : undefined,
    chat_type: chatType || undefined,
    direction: direction || undefined,
    topics: topics || undefined,
    date_from: dateFrom || undefined,
    date_to: dateTo || undefined,
  };
}

function renderRedactionNotice(container, result) {
  if (!result.redaction_applied) return;
  const notice = document.createElement("p");
  notice.className = "redaction-notice";
  notice.textContent = `Sensitive data redacted (${result.redaction_count} field${result.redaction_count === 1 ? "" : "s"}) before AI processing.`;
  container.prepend(notice);
}

function renderOriginals(container, originals, visible) {
  const block = container.querySelector(".originals-block") || document.createElement("div");
  block.className = "originals-block";
  block.hidden = !visible;
  if (!visible) return;

  block.innerHTML = `
    <strong>Original messages</strong>
    <ul class="originals-list">
      ${originals
        .map(
          (item) => `
        <li>
          <span class="meta">${escapeHtml(item.username || "Unknown")} · ${formatTime(item.created_at)}</span>
          <div>${escapeHtml(item.text)}</div>
        </li>`
        )
        .join("")}
    </ul>`;
  container.appendChild(block);
}

function renderSummary(result) {
  const panel = document.getElementById("summary-panel");
  panel.hidden = false;
  panel.innerHTML = `
    <div class="insight-header">
      <strong>Filtered summary</strong>
      <span class="badge">${escapeHtml(result.summary_type || "brief")}</span>
      ${result.cached ? '<span class="badge">cached</span>' : ""}
      <button type="button" class="btn btn-ghost btn-sm" id="copy-summary">Copy</button>
    </div>
    <p class="insight-text">${escapeHtml(result.summary)}</p>
    <p class="summary-meta">${result.message_count} messages · via ${escapeHtml(result.provider)}</p>
    <label class="toggle-originals">
      <input type="checkbox" id="toggle-originals" />
      View original messages
    </label>`;

  renderRedactionNotice(panel, result);
  renderOriginals(panel, result.originals || [], false);

  panel.querySelector("#copy-summary").addEventListener("click", () => {
    navigator.clipboard.writeText(result.summary).catch(() => {});
  });
  panel.querySelector("#toggle-originals").addEventListener("change", (event) => {
    renderOriginals(panel, result.originals || [], event.target.checked);
  });
}

function priorityClass(priority) {
  return `priority-${priority || "medium"}`;
}

function statusBadge(status) {
  if (!status || status === "pending") return "";
  return `<span class="badge status-${status}">${escapeHtml(status)}</span>`;
}

function renderSuggestions(result, onSent) {
  const panel = document.getElementById("suggestions-panel");
  panel.hidden = false;

  const suggestions = (result.suggestions || []).filter((item) => item.status !== "dismissed");
  panel.innerHTML = `
    <div class="insight-header">
      <strong>Suggested actions</strong>
      <span class="summary-meta">via ${escapeHtml(result.provider)}</span>
    </div>
    <p class="insight-text">${escapeHtml(result.summary || "")}</p>
    <div class="suggestion-cards">
      ${
        suggestions.length
          ? suggestions
              .map(
                (item, index) => `
          <article class="suggestion-card ${priorityClass(item.priority)} ${item.status && item.status !== "pending" ? "is-handled" : ""}" data-index="${index}" data-id="${item.id || ""}">
            <div class="suggestion-meta">
              <span class="badge">${escapeHtml(item.type)}</span>
              <span class="badge">${escapeHtml(item.priority || "medium")}</span>
              ${item.confidence != null ? `<span class="badge">${Math.round(item.confidence * 100)}%</span>` : ""}
              ${statusBadge(item.status)}
            </div>
            ${
              item.type === "reply"
                ? `
              <p><strong>${escapeHtml(item.user || "Contact")}</strong>${item.chat_id ? ` · chat ${item.chat_id}` : ""}</p>
              <textarea class="suggestion-draft" rows="3" ${item.status === "sent" ? "disabled" : ""}>${escapeHtml(item.draft || "")}</textarea>
              <div class="suggestion-actions">
                <button type="button" class="btn btn-primary btn-sm send-suggestion" ${item.status === "sent" ? "disabled" : ""}>Send</button>
                <button type="button" class="btn btn-ghost btn-sm mark-done" ${item.status === "done" ? "disabled" : ""}>Mark done</button>
                <button type="button" class="btn btn-ghost btn-sm dismiss-suggestion" ${item.status === "dismissed" ? "disabled" : ""}>Dismiss</button>
              </div>`
                : `
              <p>${escapeHtml(item.action || "")}</p>
              ${item.due_hint ? `<p class="summary-meta">Due: ${escapeHtml(item.due_hint)}</p>` : ""}
              <div class="suggestion-actions">
                <button type="button" class="btn btn-ghost btn-sm mark-done" ${item.status === "done" ? "disabled" : ""}>Mark done</button>
                <button type="button" class="btn btn-ghost btn-sm dismiss-suggestion" ${item.status === "dismissed" ? "disabled" : ""}>Dismiss</button>
              </div>`
            }
          </article>`
              )
              .join("")
          : "<p class='empty-thread'>No suggestions for the current filters.</p>"
      }
    </div>`;

  renderRedactionNotice(panel, result);

  async function updateStatus(card, status) {
    const id = Number(card.dataset.id);
    if (!id) {
      card.remove();
      return;
    }
    await api.updateSuggestionStatus(id, status);
    if (status === "dismissed") {
      card.remove();
      return;
    }
    const badge = card.querySelector(".suggestion-meta");
    const existing = badge.querySelector(`.status-${status}`);
    if (!existing) {
      badge.insertAdjacentHTML("beforeend", statusBadge(status));
    }
    card.classList.add("is-handled");
    card.querySelectorAll("button").forEach((btn) => {
      if (status === "sent" && btn.classList.contains("send-suggestion")) btn.disabled = true;
      if (status === "done" && btn.classList.contains("mark-done")) btn.disabled = true;
    });
    if (status === "sent") {
      card.querySelector(".suggestion-draft")?.setAttribute("disabled", "disabled");
    }
  }

  panel.querySelectorAll(".send-suggestion").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const card = event.target.closest(".suggestion-card");
      const index = Number(card.dataset.index);
      const item = suggestions[index];
      const draft = card.querySelector(".suggestion-draft")?.value.trim();
      if (!item.chat_id || !draft) return;
      await api.sendMessage(item.chat_id, draft);
      await updateStatus(card, "sent");
      onSent();
    });
  });

  panel.querySelectorAll(".mark-done").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const card = event.target.closest(".suggestion-card");
      await updateStatus(card, "done");
      onSent("Suggestion marked done.");
    });
  });

  panel.querySelectorAll(".dismiss-suggestion").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const card = event.target.closest(".suggestion-card");
      await updateStatus(card, "dismissed");
    });
  });
}

export function bindInsights(onError, onSent = () => {}) {
  document.getElementById("btn-summarize").addEventListener("click", async () => {
    const panel = document.getElementById("summary-panel");
    const summaryType = document.getElementById("summary-type").value;
    panel.hidden = false;
    panel.innerHTML = `<p class="summary-loading">Generating summary…</p>`;
    try {
      const result = await api.summarize({ ...buildFilterPayload(), summary_type: summaryType });
      renderSummary(result);
    } catch (error) {
      panel.innerHTML = `<p class="error-text">${escapeHtml(error.message)}</p>`;
      onError(error.message);
    }
  });

  document.getElementById("btn-suggest").addEventListener("click", async () => {
    const panel = document.getElementById("suggestions-panel");
    panel.hidden = false;
    panel.innerHTML = `<p class="summary-loading">Generating suggestions…</p>`;
    try {
      const result = await api.suggestActions(buildFilterPayload());
      renderSuggestions(result, onSent);
    } catch (error) {
      panel.innerHTML = `<p class="error-text">${escapeHtml(error.message)}</p>`;
      onError(error.message);
    }
  });
}
