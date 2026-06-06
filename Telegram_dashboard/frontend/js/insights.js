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
  const { q, userIds, chatType, direction, dateFrom, dateTo } = inboxState.filters;
  return {
    q: q || undefined,
    user_ids: userIds.length ? userIds.join(",") : undefined,
    chat_type: chatType || undefined,
    direction: direction || undefined,
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

function renderSuggestions(result) {
  const panel = document.getElementById("suggestions-panel");
  panel.hidden = false;

  const suggestions = result.suggestions || [];
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
          <article class="suggestion-card ${priorityClass(item.priority)}" data-index="${index}">
            <div class="suggestion-meta">
              <span class="badge">${escapeHtml(item.type)}</span>
              <span class="badge">${escapeHtml(item.priority || "medium")}</span>
              ${item.confidence != null ? `<span class="badge">${Math.round(item.confidence * 100)}%</span>` : ""}
            </div>
            ${
              item.type === "reply"
                ? `
              <p><strong>${escapeHtml(item.user || "Contact")}</strong>${item.chat_id ? ` · chat ${item.chat_id}` : ""}</p>
              <textarea class="suggestion-draft" rows="3">${escapeHtml(item.draft || "")}</textarea>
              <div class="suggestion-actions">
                <button type="button" class="btn btn-primary btn-sm send-suggestion">Send</button>
                <button type="button" class="btn btn-ghost btn-sm dismiss-suggestion">Dismiss</button>
              </div>`
                : `
              <p>${escapeHtml(item.action || "")}</p>
              ${item.due_hint ? `<p class="summary-meta">Due: ${escapeHtml(item.due_hint)}</p>` : ""}
              <button type="button" class="btn btn-ghost btn-sm dismiss-suggestion">Dismiss</button>`
            }
          </article>`
              )
              .join("")
          : "<p class='empty-thread'>No suggestions for the current filters.</p>"
      }
    </div>`;

  renderRedactionNotice(panel, result);

  panel.querySelectorAll(".send-suggestion").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const card = event.target.closest(".suggestion-card");
      const index = Number(card.dataset.index);
      const item = suggestions[index];
      const draft = card.querySelector(".suggestion-draft")?.value.trim();
      if (!item.chat_id || !draft) return;
      await api.sendMessage(item.chat_id, draft);
      card.remove();
      onSent();
    });
  });

  panel.querySelectorAll(".dismiss-suggestion").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.target.closest(".suggestion-card")?.remove();
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
      renderSuggestions(result);
    } catch (error) {
      panel.innerHTML = `<p class="error-text">${escapeHtml(error.message)}</p>`;
      onError(error.message);
    }
  });

  document.getElementById("suggestions-panel").addEventListener("suggestion-sent", () => {
    onSent?.();
  });
}
