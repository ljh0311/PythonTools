import { api } from "./api.js";
import {
  buildAiFilterPayload,
  collectFiltersFromForm,
  displayName,
} from "./inbox.js";

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
  return buildAiFilterPayload();
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

function truncateText(text, max = 220) {
  const value = String(text || "").trim();
  if (value.length <= max) return value;
  return `${value.slice(0, max - 1)}…`;
}

function providerBadge(provider) {
  const normalized = provider || "none";
  const cls =
    normalized === "fallback"
      ? "provider-badge provider-fallback"
      : normalized === "ollama" || normalized === "gemini"
        ? "provider-badge provider-ai"
        : "provider-badge";
  return `<span class="${cls}">via ${escapeHtml(normalized)}</span>`;
}

function renderMessageHighlights(messages = [], { title = "Recent messages" } = {}) {
  if (!messages.length) return "";
  return `
    <section class="message-highlights" aria-label="${escapeHtml(title)}">
      <div class="highlights-header">
        <strong>${escapeHtml(title)}</strong>
        <span class="highlights-count">${messages.length} shown</span>
      </div>
      <ul class="highlight-list">
        ${messages
          .map(
            (item) => `
          <li class="highlight-item highlight-${escapeHtml(item.direction || "incoming")}">
            <div class="highlight-meta">
              <strong>${escapeHtml(displayName(item))}</strong>
              ${
                item.chat_title
                  ? `<span class="highlight-chat">${escapeHtml(item.chat_title)}</span>`
                  : ""
              }
              <time>${formatTime(item.created_at)}</time>
            </div>
            <p class="highlight-text">${escapeHtml(truncateText(item.text))}</p>
          </li>`
          )
          .join("")}
      </ul>
    </section>`;
}

function renderFallbackNotice() {
  return `
    <p class="fallback-notice">
      AI is off or failed. Showing a short overview and recent messages instead of a full summary.
    </p>`;
}

function renderDegradationNotice(result) {
  if (!result?.degraded && !result?.failure_reason) return "";
  const text = result.failure_reason || "Using fallback provider";
  return `<p class="degradation-notice">${escapeHtml(text)}</p>`;
}

function renderSummaryBody(result) {
  const isFallback = result.provider === "fallback";
  const highlights = result.message_highlights || result.originals || [];

  if (isFallback && highlights.length) {
    return `
      ${renderFallbackNotice()}
      ${renderDegradationNotice(result)}
      <p class="insight-lead">${escapeHtml(result.summary || "")}</p>
      ${renderMessageHighlights(highlights)}`;
  }

  if (isFallback) {
    return `
      ${renderFallbackNotice()}
      ${renderDegradationNotice(result)}
      <p class="insight-lead">${escapeHtml(result.summary || "")}</p>`;
  }

  return `<p class="insight-text">${escapeHtml(result.summary || "")}</p>`;
}

function renderSummary(result) {
  const panel = document.getElementById("summary-panel");
  panel.hidden = false;
  panel.innerHTML = `
    <div class="insight-header">
      <strong>Filtered summary</strong>
      <span class="badge">${escapeHtml(result.summary_type || "brief")}</span>
      ${result.cached ? '<span class="badge">cached</span>' : ""}
      ${providerBadge(result.provider)}
      <button type="button" class="btn btn-ghost btn-sm" id="copy-summary">Copy</button>
    </div>
    ${renderDegradationNotice(result)}
    ${
      result.name_corrections?.length
        ? `<p class="summary-corrections">Names corrected: ${result.name_corrections
            .map((item) => `${escapeHtml(item.from)} → ${escapeHtml(item.to)}`)
            .join(", ")}</p>`
        : ""
    }
    ${renderSummaryBody(result)}
    <p class="summary-meta">${result.message_count} messages</p>
    ${
      !result.message_highlights?.length && (result.originals || []).length
        ? `<label class="toggle-originals">
      <input type="checkbox" id="toggle-originals" />
      View original messages
    </label>`
        : ""
    }`;

  renderRedactionNotice(panel, result);
  renderOriginals(panel, result.originals || [], false);

  panel.querySelector("#copy-summary")?.addEventListener("click", () => {
    navigator.clipboard.writeText(result.summary).catch(() => {});
  });
  panel.querySelector("#toggle-originals")?.addEventListener("change", (event) => {
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

function renderTruncationNotice(result) {
  if (!result.truncated_for_ai) return "";
  return `<p class="summary-meta">Analyzed ${result.messages_analyzed} of ${result.messages_total} filtered messages (most recent).</p>`;
}

function renderSuggestions(result, onSent) {
  const panel = document.getElementById("suggestions-panel");
  panel.hidden = false;

  const suggestions = (result.suggestions || []).filter((item) => item.status !== "dismissed");
  const isFallback = result.provider === "fallback";
  panel.innerHTML = `
    <div class="insight-header">
      <strong>Suggested actions</strong>
      ${providerBadge(result.provider)}
    </div>
    ${renderTruncationNotice(result)}
    ${renderDegradationNotice(result)}
    ${
      isFallback
        ? `${renderFallbackNotice()}<p class="insight-lead">${escapeHtml(result.summary || "")}</p>${renderMessageHighlights(result.message_highlights || [])}`
        : `<p class="insight-text">${escapeHtml(result.summary || "")}</p>`
    }
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

function renderIntelSection(title, text, tone = "default") {
  return `
    <section class="intel-section intel-${escapeHtml(tone)}">
      <h3>${escapeHtml(title)}</h3>
      <p>${escapeHtml(text || "No summary available.")}</p>
    </section>`;
}

function renderIntel(result) {
  const panel = document.getElementById("intel-panel");
  const summaryPanel = document.getElementById("summary-panel");
  const suggestionsPanel = document.getElementById("suggestions-panel");
  if (summaryPanel) summaryPanel.hidden = true;
  if (suggestionsPanel) suggestionsPanel.hidden = true;
  panel.hidden = false;
  const isFallback = result.provider === "fallback";
  panel.innerHTML = `
    <div class="insight-header">
      <strong>Conversation intel</strong>
      ${providerBadge(result.provider)}
    </div>
    ${renderTruncationNotice(result)}
    ${renderDegradationNotice(result)}
    ${isFallback ? renderFallbackNotice() : ""}
    ${renderIntelSection("What people talked about", result.topics_summary)}
    ${renderIntelSection("What people felt", result.sentiment_summary, "sentiment")}
    ${renderIntelSection("What they need from you", result.needs_summary, "needs")}
    ${
      result.key_points?.length
        ? `<section class="intel-section">
            <h3>Key points</h3>
            <ul class="intel-points">
              ${result.key_points.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
            </ul>
          </section>`
        : ""
    }
    ${isFallback ? renderMessageHighlights(result.message_highlights || []) : ""}
    <p class="summary-meta">${escapeHtml(String(result.message_count || 0))} messages</p>
    <button type="button" class="btn btn-ghost btn-sm" id="copy-intel">Copy</button>`;

  renderRedactionNotice(panel, result);
  panel.querySelector("#copy-intel")?.addEventListener("click", () => {
    const lines = [
      "Conversation intel",
      `What people talked about: ${result.topics_summary || ""}`,
      `What people felt: ${result.sentiment_summary || ""}`,
      `What they need from you: ${result.needs_summary || ""}`,
      ...(result.key_points?.length ? ["Key points:", ...result.key_points.map((item) => `- ${item}`)] : []),
    ];
    navigator.clipboard.writeText(lines.join("\n")).catch(() => {});
  });
}

export function bindInsights(onError, onSent = () => {}) {
  document.getElementById("btn-summarize").addEventListener("click", async () => {
    const panel = document.getElementById("summary-panel");
    document.getElementById("intel-panel").hidden = true;
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
    document.getElementById("intel-panel").hidden = true;
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

  document.getElementById("btn-intel").addEventListener("click", async () => {
    const panel = document.getElementById("intel-panel");
    panel.hidden = false;
    panel.innerHTML = `<p class="summary-loading">Analyzing conversation intel…</p>`;
    try {
      const result = await api.getConversationIntel(buildFilterPayload());
      renderIntel(result);
    } catch (error) {
      panel.innerHTML = `<p class="error-text">${escapeHtml(error.message)}</p>`;
      onError(error.message);
    }
  });
}
