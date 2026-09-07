import { api } from "./api.js";
import { asList, escapeHtml, formatTime, showToast, suggestionFields } from "./utils.js";

const state = {
  items: [],
  loading: false,
  refreshing: false,
};

function root() {
  return document.getElementById("view-act");
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="panel" style="height:100%">
      <div class="panel-header">
        <h2>Action queue</h2>
        <div class="panel-actions">
          <button type="button" class="btn btn-ghost" id="act-reload">Reload</button>
          <button type="button" class="btn btn-primary" id="act-refresh-ai">Refresh AI</button>
        </div>
      </div>
      <div class="panel-body" id="act-list"></div>
    </div>
  `;

  el.querySelector("#act-reload").addEventListener("click", () => loadAct());
  el.querySelector("#act-refresh-ai").addEventListener("click", () => refreshAi());
}

function bodyText(fields) {
  if (fields.type === "reply") {
    const who = fields.user || (fields.chatId != null ? `chat ${fields.chatId}` : "Contact");
    return `${who}\n${fields.draft || "(no draft)"}`;
  }
  return fields.action || fields.draft || "(no details)";
}

function renderList() {
  const list = document.getElementById("act-list");
  if (!list) return;

  if (state.loading) {
    list.innerHTML = `<p class="loading-state">Loading actions…</p>`;
    return;
  }

  if (!state.items.length) {
    list.innerHTML = `<p class="empty-state">Nothing in the queue. Use Refresh AI to generate suggestions.</p>`;
    return;
  }

  list.innerHTML = state.items
    .map((item) => {
      const f = suggestionFields(item);
      const statusClass = f.status === "done" || f.status === "dismissed" ? `is-${f.status}` : "";
      return `
        <article class="act-card ${statusClass}" data-id="${escapeHtml(f.id)}">
          <div class="act-meta">
            <span class="badge">${escapeHtml(f.type)}</span>
            <span class="badge badge-priority-${escapeHtml(f.priority)}">${escapeHtml(f.priority)}</span>
            <span class="badge badge-status-${escapeHtml(f.status)}">${escapeHtml(f.status)}</span>
            ${f.chatId != null ? `<span class="badge">chat ${escapeHtml(f.chatId)}</span>` : ""}
            ${f.createdAt ? `<span class="badge">${escapeHtml(formatTime(f.createdAt))}</span>` : ""}
          </div>
          <p class="act-body">${escapeHtml(bodyText(f))}</p>
          ${f.dueHint ? `<p class="list-meta">Due: ${escapeHtml(f.dueHint)}</p>` : ""}
          <div class="act-actions">
            <button type="button" class="btn btn-ghost" data-status="pending" ${f.status === "pending" ? "disabled" : ""}>Reopen</button>
            <button type="button" class="btn btn-primary" data-status="done" ${f.status === "done" ? "disabled" : ""}>Mark done</button>
            <button type="button" class="btn btn-ghost btn-danger" data-status="dismissed" ${f.status === "dismissed" ? "disabled" : ""}>Dismiss</button>
          </div>
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
  renderList();
  try {
    const data = await api.getAct();
    state.items = asList(data, ["items", "suggestions", "actions"]);
    renderList();
  } catch (err) {
    const list = document.getElementById("act-list");
    if (list) {
      list.innerHTML = `<p class="error-state">${escapeHtml(err.message || "Failed to load act queue")}</p>`;
    }
    showToast(err.message || "Failed to load act queue", { error: true });
  } finally {
    state.loading = false;
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
    showToast("Action queue refreshed");
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
    showToast(`Marked ${status}`);
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
