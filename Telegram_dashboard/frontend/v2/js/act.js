import { api } from "./api.js";
import { asList, escapeHtml, formatTime, showToast, suggestionFields } from "./utils.js";

const state = {
  items: [],
  loading: false,
  refreshing: false,
  loadError: null,
  provider: null,
  degraded: false,
  failureReason: null,
};

function root() {
  return document.getElementById("view-act");
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="act-workspace">
      <p class="view-hint">Things to reply to or act on. Mark done when triage is complete — Refresh AI rebuilds the queue with the current provider.</p>
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

function updateProviderSub() {
  const sub = document.getElementById("act-provider-sub");
  if (!sub) return;
  if (state.provider) {
    sub.textContent = state.degraded
      ? `Using ${state.provider} drafts (degraded / heuristic)`
      : `Provider: ${state.provider}`;
    return;
  }
  sub.textContent = "Pending work from recent chats";
}

function bodyText(fields) {
  if (fields.type === "reply") {
    const who = fields.user || (fields.chatId != null ? `chat ${fields.chatId}` : "Contact");
    const action = fields.action ? `\n${fields.action}` : "";
    return `${who}\n${fields.draft || "(no draft)"}${action}`;
  }
  return fields.action || fields.draft || "(no details)";
}

function replyBadge(fields) {
  if (fields.type !== "reply" && fields.chatId == null) return "";
  if (fields.alreadyReplied) {
    return `<span class="badge badge-reply-done">You already replied</span>`;
  }
  return `<span class="badge badge-reply-needed">Needs reply</span>`;
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
      const statusClass = f.status === "done" || f.status === "dismissed" ? `is-${f.status}` : "";
      const talkLink =
        f.chatId != null
          ? `<a class="act-talk-link" href="#talk">Open in Talk (chat ${escapeHtml(f.chatId)})</a>`
          : `<a class="act-talk-link" href="#talk">Open Talk</a>`;
      return `
        <article class="act-card ${statusClass}" data-id="${escapeHtml(f.id)}">
          <div class="act-meta">
            <span class="badge">${escapeHtml(f.type)}</span>
            <span class="badge badge-priority-${escapeHtml(f.priority)}">${escapeHtml(f.priority)}</span>
            <span class="badge badge-status-${escapeHtml(f.status)}">${escapeHtml(f.status)}</span>
            ${replyBadge(f)}
            ${f.chatId != null ? `<span class="badge">chat ${escapeHtml(f.chatId)}</span>` : ""}
            ${f.createdAt ? `<span class="badge">${escapeHtml(formatTime(f.createdAt))}</span>` : ""}
          </div>
          <p class="act-body">${escapeHtml(bodyText(f))}</p>
          ${f.lastInboundText ? `<p class="list-meta">Last inbound: ${escapeHtml(f.lastInboundText)}</p>` : ""}
          ${f.alreadyReplied && f.lastOutboundText ? `<p class="list-meta">Your last reply: ${escapeHtml(f.lastOutboundText)}</p>` : ""}
          ${f.dueHint ? `<p class="list-meta">Due: ${escapeHtml(f.dueHint)}</p>` : ""}
          <div class="act-actions">
            <button type="button" class="btn btn-ghost" data-status="pending" title="Bring back to pending" ${f.status === "pending" ? "disabled" : ""}>Reopen</button>
            <button type="button" class="btn btn-primary" data-status="done" title="Triage complete — handled" ${f.status === "done" ? "disabled" : ""}>Mark done</button>
            <button type="button" class="btn btn-ghost btn-danger" data-status="dismissed" title="Hide / ignore this item" ${f.status === "dismissed" ? "disabled" : ""}>Dismiss</button>
          </div>
          <p class="act-action-help">Mark done = triage complete (handled). Dismiss = hide/ignore. Reopen = bring back to pending.</p>
          ${talkLink}
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
  });
}

async function loadAct() {
  state.loading = true;
  state.loadError = null;
  renderList();
  try {
    const data = await api.getAct();
    state.items = asList(data, ["items", "suggestions", "actions"]);
    if (data?.provider) state.provider = data.provider;
    if (typeof data?.degraded === "boolean") state.degraded = data.degraded;
    if (data?.failure_reason) state.failureReason = data.failure_reason;
    updateProviderSub();
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
  if (btn) btn.disabled = true;
  state.refreshing = true;
  try {
    const data = await api.refreshAct();
    const refreshed = asList(data, ["items", "suggestions", "actions"]);
    if (refreshed.length) {
      state.items = refreshed;
      renderList();
    } else {
      await loadAct();
    }
    state.provider = data?.provider || "unknown";
    state.degraded = Boolean(data?.degraded);
    state.failureReason = data?.failure_reason || null;
    updateProviderSub();
    showToast(
      state.degraded
        ? `Queue refreshed via ${state.provider} (fallback drafts)`
        : `Action queue refreshed (${state.provider})`,
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
    const labels = { done: "done (handled)", dismissed: "dismissed", pending: "reopened" };
    showToast(`Marked ${labels[status] || status}`);
  } catch (err) {
    showToast(err.message || "Status update failed", { error: true });
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
