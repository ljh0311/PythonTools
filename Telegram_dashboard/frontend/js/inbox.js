import { api } from "./api.js";

const DEFAULT_LIMIT = 10;

export const inboxState = {
  users: [],
  threads: [],
  messages: [],
  total: 0,
  offset: 0,
  limit: DEFAULT_LIMIT,
  view: "threads",
  filters: {
    q: "",
    userIds: [],
    chatType: "",
    direction: "",
    topics: "",
    dateFrom: "",
    dateTo: "",
  },
};

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

function displayName(item) {
  return item.username ? `@${item.username}` : `User ${item.user_id}`;
}

function threadTitle(thread) {
  if (thread.chat_type === "group") {
    return thread.chat_title || `Group chat ${thread.chat_id}`;
  }
  const first = thread.messages[0];
  return first ? displayName(first) : `Chat ${thread.chat_id}`;
}

function renderTopicChips(topics = []) {
  if (!topics.length) return "";
  return `<div class="topic-chips">${topics
    .map(
      (topic) =>
        `<span class="topic-chip ${topic.source || "manual"}">${escapeHtml(topic.name)}</span>`
    )
    .join("")}</div>`;
}

function buildFilterParams() {
  return {
    limit: inboxState.limit,
    offset: inboxState.offset,
    q: inboxState.filters.q || undefined,
    chat_type: inboxState.filters.chatType || undefined,
    direction: inboxState.filters.direction || undefined,
    topics: inboxState.filters.topics || undefined,
    date_from: inboxState.filters.dateFrom || undefined,
    date_to: inboxState.filters.dateTo || undefined,
    user_ids: inboxState.filters.userIds.length
      ? inboxState.filters.userIds.join(",")
      : undefined,
  };
}

export function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  inboxState.filters.q = params.get("q") || "";
  inboxState.filters.chatType = params.get("chat_type") || "";
  inboxState.filters.direction = params.get("direction") || "";
  inboxState.filters.topics = params.get("topics") || "";
  inboxState.filters.dateFrom = params.get("from") || "";
  inboxState.filters.dateTo = params.get("to") || "";
  inboxState.view = params.get("view") === "flat" ? "flat" : "threads";
  const userIds = params.get("user_ids");
  inboxState.filters.userIds = userIds ? userIds.split(",").filter(Boolean) : [];
  inboxState.offset = Number(params.get("offset") || 0);
}

export function writeFiltersToUrl() {
  const params = new URLSearchParams();
  const { q, userIds, chatType, direction, topics, dateFrom, dateTo } = inboxState.filters;
  if (q) params.set("q", q);
  if (userIds.length) params.set("user_ids", userIds.join(","));
  if (chatType) params.set("chat_type", chatType);
  if (direction) params.set("direction", direction);
  if (topics) params.set("topics", topics);
  if (dateFrom) params.set("from", dateFrom);
  if (dateTo) params.set("to", dateTo);
  if (inboxState.view === "flat") params.set("view", "flat");
  if (inboxState.offset) params.set("offset", String(inboxState.offset));
  const query = params.toString();
  const next = query ? `?${query}` : window.location.pathname;
  window.history.replaceState({}, "", next);
}

export function syncFilterForm() {
  document.getElementById("inbox-search").value = inboxState.filters.q;
  document.getElementById("inbox-topics").value = inboxState.filters.topics;
  document.getElementById("inbox-chat-type").value = inboxState.filters.chatType;
  document.getElementById("inbox-direction").value = inboxState.filters.direction;
  document.getElementById("inbox-date-from").value = inboxState.filters.dateFrom;
  document.getElementById("inbox-date-to").value = inboxState.filters.dateTo;
  document.getElementById("inbox-view").value = inboxState.view;

  const select = document.getElementById("inbox-users");
  [...select.options].forEach((option) => {
    if (!option.value) return;
    option.selected = inboxState.filters.userIds.includes(option.value);
  });
}

export function renderUserFilter(users = []) {
  inboxState.users = users;
  const select = document.getElementById("inbox-users");
  select.innerHTML = users
    .map(
      (user) =>
        `<option value="${user.user_id}">${escapeHtml(user.display_name)} (${user.message_count})</option>`
    )
    .join("");
  syncFilterForm();
}

function renderThreadMessages(messages) {
  return messages
    .map(
      (item) => `
      <li class="thread-message ${item.direction}">
        <div class="meta">
          <span>${escapeHtml(displayName(item))} · ${item.direction}</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        ${renderTopicChips(item.topics)}
        <div class="message-text">${escapeHtml(item.text)}</div>
      </li>`
    )
    .join("");
}

function renderFlatMessages(messages = []) {
  const feed = document.getElementById("messages-feed");
  if (!messages.length) {
    feed.innerHTML = `<div class="empty-thread">No messages match your filters.</div>`;
    return;
  }

  feed.innerHTML = `<ul class="feed inbox-feed">${messages
    .map(
      (item) => `
      <li class="${item.direction}">
        <div class="meta">
          <span>${escapeHtml(displayName(item))} · ${item.chat_type || "chat"} · ${item.direction}</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        ${renderTopicChips(item.topics)}
        <div class="message-text">${escapeHtml(item.text)}</div>
        ${
          item.chat_id
            ? `<div class="message-actions"><button type="button" class="btn btn-ghost btn-sm reply-btn" data-chat-id="${item.chat_id}">Reply</button></div>`
            : ""
        }
      </li>`
    )
    .join("")}</ul>`;
}

export function renderInboxThreads(threads = [], total = 0) {
  inboxState.threads = threads;

  const feed = document.getElementById("messages-feed");
  if (!threads.length) {
    feed.innerHTML = `<div class="empty-thread">No conversations match your filters.</div>`;
  } else {
    feed.innerHTML = threads
      .map((thread, index) => {
        const chatId = thread.chat_id ?? `thread-${index}`;
        const typeBadge = thread.chat_type === "group" ? "Group" : "Private";
        return `
        <article class="thread-card" data-chat-id="${chatId}" data-thread-index="${index}">
          <header class="thread-header">
            <div>
              <h3 class="thread-title">${escapeHtml(threadTitle(thread))}</h3>
              <p class="thread-meta">
                <span class="badge">${typeBadge}</span>
                ${thread.message_count} message${thread.message_count === 1 ? "" : "s"}
                · ${escapeHtml(thread.participants.join(", "))}
              </p>
            </div>
            ${
              thread.chat_id
                ? `<button type="button" class="btn btn-ghost btn-sm reply-btn" data-chat-id="${thread.chat_id}">Reply</button>`
                : ""
            }
          </header>
          <div class="thread-summary" id="summary-${chatId}">
            <span class="summary-loading">Generating AI summary…</span>
          </div>
          <ul class="thread-messages">${renderThreadMessages(thread.messages)}</ul>
        </article>`;
      })
      .join("");
  }

  updateInboxCount(total, threads.length);
}

function updateInboxCount(total, shownCount) {
  const countEl = document.getElementById("inbox-count");
  const showing = Math.min(inboxState.offset + shownCount, total);
  const label = inboxState.view === "flat" ? "messages" : "conversations";
  countEl.textContent = `Showing ${showing} of ${total} ${label}`;

  const loadMoreBtn = document.getElementById("inbox-load-more");
  loadMoreBtn.textContent =
    inboxState.view === "flat" ? "Load more messages" : "Load more conversations";
  loadMoreBtn.disabled = inboxState.offset + shownCount >= total;
  loadMoreBtn.hidden = inboxState.offset + shownCount >= total;
}

async function loadThreadSummary(thread, index) {
  const chatId = thread.chat_id ?? `thread-${index}`;
  const summaryEl = document.getElementById(`summary-${chatId}`);
  if (!summaryEl || !thread.chat_id || thread.messages.length < 1) {
    if (summaryEl) {
      summaryEl.innerHTML = "<em>No summary available.</em>";
    }
    return;
  }

  try {
    const messageIds = thread.messages.map((m) => m.id);
    const result = await api.summarizeThread(thread.chat_id, messageIds);
    const redaction = result.redaction_applied
      ? `<p class="redaction-notice">Sensitive data redacted (${result.redaction_count}) before AI.</p>`
      : "";
    summaryEl.innerHTML = `
      <strong>AI Summary</strong>
      ${redaction}
      <p>${escapeHtml(result.summary)}</p>
      <span class="summary-provider">via ${escapeHtml(result.provider)}</span>`;
  } catch {
    summaryEl.innerHTML = "<em>Could not generate summary.</em>";
  }
}

async function loadSummariesForThreads(threads) {
  await Promise.all(threads.map((thread, index) => loadThreadSummary(thread, index)));
}

export function collectFiltersFromForm() {
  const select = document.getElementById("inbox-users");
  const selected = [...select.selectedOptions].map((o) => o.value);
  inboxState.filters = {
    q: document.getElementById("inbox-search").value.trim(),
    topics: document.getElementById("inbox-topics").value.trim(),
    userIds: selected,
    chatType: document.getElementById("inbox-chat-type").value,
    direction: document.getElementById("inbox-direction").value,
    dateFrom: document.getElementById("inbox-date-from").value,
    dateTo: document.getElementById("inbox-date-to").value,
  };
  inboxState.view = document.getElementById("inbox-view").value;
}

export async function loadInbox({ append = false } = {}) {
  if (!append) inboxState.offset = 0;

  const params = buildFilterParams();

  if (inboxState.view === "flat") {
    const result = await api.getMessages(params);
    const messages = append ? [...inboxState.messages, ...result.items] : result.items;
    inboxState.messages = messages;
    renderFlatMessages(messages);
    updateInboxCount(result.total, messages.length);
    writeFiltersToUrl();
    return result;
  }

  const result = await api.getInboxThreads(params);
  const threads = append ? [...inboxState.threads, ...result.threads] : result.threads;
  renderInboxThreads(threads, result.total);
  writeFiltersToUrl();
  await loadSummariesForThreads(append ? result.threads : threads);
  return result;
}

async function loadPresets() {
  const select = document.getElementById("inbox-presets");
  if (!select) return;
  const presets = await api.getPresets();
  select.innerHTML =
    `<option value="">Load preset…</option>` +
    presets.map((p) => `<option value="${p.id}">${p.name}</option>`).join("");
  select.dataset.presets = JSON.stringify(presets);
}

function applyPreset(presetId) {
  const select = document.getElementById("inbox-presets");
  const presets = JSON.parse(select.dataset.presets || "[]");
  const preset = presets.find((p) => String(p.id) === String(presetId));
  if (!preset) return;
  const f = preset.filters || {};
  inboxState.filters = {
    q: f.q || "",
    topics: f.topics || "",
    userIds: f.userIds || (f.user_ids ? String(f.user_ids).split(",") : []),
    chatType: f.chatType || f.chat_type || "",
    direction: f.direction || "",
    dateFrom: f.dateFrom || f.date_from || "",
    dateTo: f.dateTo || f.date_to || "",
  };
  inboxState.view = f.view || "threads";
  syncFilterForm();
}

export function bindInbox(onReply, onError) {
  readFiltersFromUrl();
  syncFilterForm();
  loadPresets().catch(onError);

  const toggleBtn = document.getElementById("toggle-filters");
  const advanced = document.getElementById("advanced-filters");
  toggleBtn?.addEventListener("click", () => {
    const open = advanced.hidden;
    advanced.hidden = !open;
    toggleBtn.setAttribute("aria-expanded", String(open));
    toggleBtn.classList.toggle("active", open);
  });

  document.getElementById("inbox-apply").addEventListener("click", () => {
    collectFiltersFromForm();
    loadInbox().catch(onError);
  });

  document.getElementById("inbox-clear").addEventListener("click", () => {
    inboxState.filters = {
      q: "",
      topics: "",
      userIds: [],
      chatType: "",
      direction: "",
      dateFrom: "",
      dateTo: "",
    };
    syncFilterForm();
    loadInbox().catch(onError);
  });

  document.getElementById("inbox-search").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      collectFiltersFromForm();
      loadInbox().catch(onError);
    }
  });

  document.getElementById("inbox-topics").addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      collectFiltersFromForm();
      loadInbox().catch(onError);
    }
  });

  document.getElementById("inbox-view").addEventListener("change", () => {
    collectFiltersFromForm();
    loadInbox().catch(onError);
  });

  document.getElementById("inbox-load-more").addEventListener("click", () => {
    inboxState.offset += inboxState.limit;
    loadInbox({ append: true }).catch(onError);
  });

  document.getElementById("messages-feed").addEventListener("click", (event) => {
    const button = event.target.closest(".reply-btn");
    if (!button) return;
    onReply(button.dataset.chatId);
  });

  document.getElementById("inbox-presets")?.addEventListener("change", (event) => {
    if (!event.target.value) return;
    applyPreset(event.target.value);
    loadInbox().catch(onError);
  });

  document.getElementById("inbox-save-preset")?.addEventListener("click", async () => {
    const name = window.prompt("Preset name (e.g. VIP today)");
    if (!name) return;
    collectFiltersFromForm();
    await api.savePreset(name, { ...inboxState.filters, view: inboxState.view });
    await loadPresets();
  });

  document.getElementById("inbox-delete-preset")?.addEventListener("click", async () => {
    const select = document.getElementById("inbox-presets");
    if (!select.value) return;
    await api.deletePreset(Number(select.value));
    await loadPresets();
  });

  document.getElementById("inbox-export")?.addEventListener("click", async () => {
    collectFiltersFromForm();
    const params = buildFilterParams();
    const csv = await api.exportMessages(params);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "messages-export.csv";
    link.click();
    URL.revokeObjectURL(url);
  });
}
