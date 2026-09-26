import { api } from "./api.js";
import { asList, escapeHtml, formatTime, showToast, suggestionFields } from "./utils.js";

const state = {
  items: [],
  loading: false,
  refreshing: false,
  loadError: null,
  sendAvailable: false,
  sendUnavailableReason: "",
};

const TRIAGE_HINTS = {
  pending: "Needs attention",
  done: "Handled offline — no send needed",
  dismissed: "Not actionable",
  sent: "Sent from Act",
};

function root() {
  return document.getElementById("view-act");
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="act-workspace">
      <p class="view-hint">
        Triage queue: reply drafts from chat context, then send or mark handled.
        <strong>Mark done</strong> = handled offline / no send needed ·
        <strong>Dismiss</strong> = not actionable ·
        <strong>Reopen</strong> = undo.
      </p>
      <div class="panel" style="height:100%">
        <div class="panel-header">
          <div>
            <h2>Action queue</h2>
            <p class="panel-sub" id="act-provider-sub">Pending work from recent chats</p>
          </div>
          <div class="panel-actions">
            <button type="button" class="btn btn-ghost" id="act-reload">Reload</button>
            <button type="button" class="btn btn-primary" id="act-refresh-ai">Refresh AI</button>
          </div>
        </div>
        <div class="panel-body" id="act-list"></div>
      </div>
    </div>
  `;

  el.querySelector("#act-reload").addEventListener("click", () => loadAct());
  el.querySelector("#act-refresh-ai").addEventListener("click", () => refreshAi());
}

function replyStateLabel(f) {
  if (f.status === "sent" || f.replyState === "sent") return "Sent";
  if (f.alreadyReplied || f.replyState === "already_replied") return "Already replied";
  if (f.needsReply || f.replyState === "needs_reply") return "Needs reply";
  return TRIAGE_HINTS[f.status] || f.status;
}

function replyStateClass(f) {
  if (f.status === "sent" || f.replyState === "sent") return "is-sent";
  if (f.alreadyReplied || f.replyState === "already_replied") return "is-already-replied";
  if (f.needsReply || f.replyState === "needs_reply") return "is-needs-reply";
  return "";
}

function cardBodyHtml(f) {
  const who = f.user || (f.chatId != null ? `chat ${f.chatId}` : "Contact");
  const already = f.status === "sent" || f.alreadyReplied || f.replyState === "already_replied" || f.draftSuppressed;
  const needs = f.needsReply || f.replyState === "needs_reply";

  if (already) {
    const preview = f.lastOutboundText || "(no outbound preview)";
    return `
      <p class="act-who">${escapeHtml(who)}</p>
      <p class="act-reply-banner">Already replied</p>
      <p class="act-preview"><span class="act-preview-label">Last outbound</span>${escapeHtml(preview)}</p>
      ${f.action ? `<p class="list-meta">${escapeHtml(f.action)}</p>` : ""}
    `;
  }

  if (f.type === "reply") {
    const draft = f.displayDraft || f.draft || "";
    const showAiUnavailable = f.aiUnavailable && needs;
    return `
      <p class="act-who">${escapeHtml(who)}</p>
      ${showAiUnavailable ? `<p class="act-reply-banner is-warn">AI unavailable — outline draft / reply manually</p>` : ""}
      ${f.lastInboundText ? `<p class="act-preview"><span class="act-preview-label">Last inbound</span>${escapeHtml(f.lastInboundText)}</p>` : ""}
      ${draft
        ? `<pre class="act-draft">${escapeHtml(draft)}</pre>`
        : `<p class="act-draft-empty">No draft — use last inbound above to reply manually.</p>`}
      ${f.action ? `<p class="list-meta">${escapeHtml(f.action)}</p>` : ""}
    `;
  }

  return `
    <p class="act-who">${escapeHtml(who)}</p>
    <p class="act-body">${escapeHtml(f.action || f.draft || "(no details)")}</p>
  `;
}

function canSend(f) {
  if (f.status !== "pending") return false;
  if (f.chatId == null) return false;
  if (f.alreadyReplied || f.replyState === "already_replied") return false;
  if (f.draftSuppressed) return false;
  const draft = (f.displayDraft || f.draft || "").trim();
  return Boolean(draft);
}

function renderList() {
  const list = document.getElementById("act-list");
  if (!list) return;

  if (state.loading) {
    list.innerHTML = `<p class="loading-state">Loading actions…</p>`;
    return;
  }

  if (state.loadError) {
    list.innerHTML = `<p class="error-state">${escapeHtml(state.loadError)}</p>`;
    return;
  }

  if (!state.items.length) {
    list.innerHTML = `
      <div class="empty-card">
        <p class="empty-state">Nothing needs you right now.</p>
        <p class="empty-detail">Refresh AI drafts replies and next actions from recent personal chats (Gemini primary; Ollama on failure).</p>
      </div>`;
    return;
  }

  list.innerHTML = state.items
    .map((item) => {
      const f = suggestionFields(item);
      const statusClass = ["done", "dismissed", "sent"].includes(f.status)
        ? `is-${f.status}`
        : "";
      const replyClass = replyStateClass(f);
      const sendOk = canSend(f);
      const sendDisabled = !sendOk || !state.sendAvailable;
      let sendTitle = "";
      if (!sendOk) {
        sendTitle = f.alreadyReplied
          ? "Already replied in chat history"
          : "No draft to send";
      } else if (!state.sendAvailable) {
        sendTitle = state.sendUnavailableReason || "Personal account send unavailable";
      } else {
        sendTitle = "Send draft as your Telegram user account";
      }

      return `
        <article class="act-card ${statusClass} ${replyClass}" data-id="${escapeHtml(f.id)}">
          <div class="act-meta">
            <span class="badge">${escapeHtml(f.type)}</span>
            <span class="badge badge-priority-${escapeHtml(f.priority)}">${escapeHtml(f.priority)}</span>
            <span class="badge badge-status-${escapeHtml(f.status)}" title="${escapeHtml(TRIAGE_HINTS[f.status] || "")}">${escapeHtml(f.status)}</span>
            <span class="badge badge-reply-state">${escapeHtml(replyStateLabel(f))}</span>
            ${f.chatId != null ? `<span class="badge">chat ${escapeHtml(f.chatId)}</span>` : ""}
            ${f.createdAt ? `<span class="badge">${escapeHtml(formatTime(f.createdAt))}</span>` : ""}
          </div>
          ${cardBodyHtml(f)}
          ${f.dueHint ? `<p class="list-meta">Due: ${escapeHtml(f.dueHint)}</p>` : ""}
          <div class="act-actions">
            ${f.chatId != null
              ? `<a class="btn btn-ghost" data-open-chat href="/v2#talk?chat=${encodeURIComponent(f.chatId)}">Open chat</a>`
              : ""}
            <button type="button" class="btn btn-primary" data-send ${sendDisabled ? "disabled" : ""} title="${escapeHtml(sendTitle)}">Send draft</button>
            <button type="button" class="btn btn-ghost" data-status="pending" title="Undo done/dismiss/sent" ${f.status === "pending" ? "disabled" : ""}>Reopen</button>
            <button type="button" class="btn btn-ghost" data-status="done" title="${escapeHtml(TRIAGE_HINTS.done)}" ${f.status === "done" ? "disabled" : ""}>Mark done</button>
            <button type="button" class="btn btn-ghost btn-danger" data-status="dismissed" title="${escapeHtml(TRIAGE_HINTS.dismissed)}" ${f.status === "dismissed" ? "disabled" : ""}>Dismiss</button>
          </div>
          ${!state.sendAvailable && sendOk
            ? `<p class="list-meta act-send-reason">${escapeHtml(state.sendUnavailableReason || "Send disabled")}</p>`
            : ""}
        </article>
      `;
    })
    .join("");

  list.querySelectorAll(".act-card").forEach((card) => {
    card.querySelectorAll("[data-status]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = card.getAttribute("data-id");
        const status = btn.getAttribute("data-status");
        await patchStatus(id, status);
      });
    });
    card.querySelector("[data-send]")?.addEventListener("click", async () => {
      const id = card.getAttribute("data-id");
      await sendDraft(id);
    });
    card.querySelector("[data-open-chat]")?.addEventListener("click", (event) => {
      // Allow same-page hash navigation to select thread
      const href = event.currentTarget.getAttribute("href") || "";
      const match = href.match(/chat=([^&]+)/);
      if (match) {
        sessionStorage.setItem("v2-talk-chat", decodeURIComponent(match[1]));
      }
    });
  });
}

function applyQueueMeta(data) {
  if (!data || typeof data !== "object") return;
  state.sendAvailable = Boolean(data.send_available);
  state.sendUnavailableReason = data.send_unavailable_reason || "";
}

async function loadAct() {
  state.loading = true;
  state.loadError = null;
  renderList();
  try {
    const data = await api.getAct();
    applyQueueMeta(data);
    state.items = asList(data, ["items", "suggestions", "actions"]);
  } catch (err) {
    state.loadError = err.message || "Failed to load act queue";
    showToast(state.loadError, { error: true });
  } finally {
    state.loading = false;
    renderList();
  }
}

async function refreshAi() {
  const btn = document.getElementById("act-refresh-ai");
  const sub = document.getElementById("act-provider-sub");
  if (btn) btn.disabled = true;
  state.refreshing = true;
  try {
    const data = await api.refreshAct();
    applyQueueMeta(data);
    const refreshed = asList(data, ["items", "suggestions", "actions"]);
    if (refreshed.length) {
      state.items = refreshed;
      renderList();
    } else {
      await loadAct();
    }
    const provider = data?.provider || "unknown";
    if (sub) {
      sub.textContent = data?.degraded
        ? `Using ${provider} drafts (degraded / heuristic)`
        : `Provider: ${provider}`;
    }
    showToast(
      data?.degraded
        ? `Queue refreshed via ${provider} (fallback drafts)`
        : `Action queue refreshed (${provider})`,
    );
  } catch (err) {
    showToast(err.message || "AI refresh failed", { error: true });
  } finally {
    state.refreshing = false;
    if (btn) btn.disabled = false;
  }
}

async function patchStatus(id, status) {
  try {
    const updated = await api.patchAct(id, status);
    const idx = state.items.findIndex((item) => String(item.id) === String(id));
    if (idx >= 0) {
      state.items[idx] = { ...state.items[idx], ...updated, status };
    }
    if (status === "dismissed") {
      state.items = state.items.filter((item) => String(item.id) !== String(id));
    }
    renderList();
    const label =
      status === "done"
        ? "Marked done (handled offline)"
        : status === "dismissed"
          ? "Dismissed (not actionable)"
          : status === "pending"
            ? "Reopened"
            : `Marked ${status}`;
    showToast(label);
  } catch (err) {
    showToast(err.message || "Status update failed", { error: true });
  }
}

async function sendDraft(id) {
  try {
    const data = await api.sendActDraft(id);
    const updated = data?.suggestion || data;
    const idx = state.items.findIndex((item) => String(item.id) === String(id));
    if (idx >= 0 && updated) {
      state.items[idx] = { ...state.items[idx], ...updated, status: "sent" };
    }
    renderList();
    showToast("Draft sent — marked sent");
  } catch (err) {
    showToast(err.message || "Send failed", { error: true });
  }
}

export async function mountAct() {
  renderShell();
  await loadAct();
}

export function refreshActIfVisible() {
  const el = root();
  if (el?.classList.contains("is-visible")) {
    return loadAct();
  }
  return Promise.resolve();
}
