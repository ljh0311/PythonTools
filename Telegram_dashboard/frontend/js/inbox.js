import { api } from "./api.js";
import { buildInboxEmptyHtml } from "./connection-status.js";
import { workflowState } from "./workflow.js";

const DEFAULT_LIMIT = 10;
const FILTER_DEBOUNCE_MS = 350;
const TOPIC_CHIP_LIMIT = 12;
let filterDebounceTimer = null;
let cachedTopics = [];

/** Local calendar date as YYYY-MM-DD for <input type="date">. */
export function localTodayInputValue() {
  const now = new Date();
  const y = now.getFullYear();
  const m = String(now.getMonth() + 1).padStart(2, "0");
  const d = String(now.getDate()).padStart(2, "0");
  return `${y}-${m}-${d}`;
}

function defaultDateFilters() {
  const today = localTodayInputValue();
  return { dateFrom: today, dateTo: today };
}

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
    ingestionSource: "",
    topics: "",
    ...defaultDateFilters(),
  },
  expandedContextChatIds: new Set(),
  operatorUser: null,
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

export function setOperatorUser(user) {
  inboxState.operatorUser = user || null;
}

export function displayName(item) {
  if (item.username) return `@${item.username}`;
  const me = inboxState.operatorUser;
  if (
    me?.username &&
    item.direction === "outgoing" &&
    item.ingestion_source === "user_account" &&
    String(item.user_id) === String(me.id)
  ) {
    return `@${me.username}`;
  }
  return `User ${item.user_id}`;
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
    ingestion_source: inboxState.filters.ingestionSource || undefined,
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
  inboxState.filters.ingestionSource = params.get("ingestion_source") || "";
  inboxState.filters.topics = params.get("topics") || "";
  // Default: today's messages. Explicit from/to in the URL win (including empty = all dates).
  if (!params.has("from") && !params.has("to")) {
    const today = localTodayInputValue();
    inboxState.filters.dateFrom = today;
    inboxState.filters.dateTo = today;
  } else {
    inboxState.filters.dateFrom = params.get("from") || "";
    inboxState.filters.dateTo = params.get("to") || "";
  }
  inboxState.view = params.get("view") === "flat" ? "flat" : "threads";
  const userIds = params.get("user_ids");
  inboxState.filters.userIds = userIds ? userIds.split(",").filter(Boolean) : [];
  inboxState.offset = Number(params.get("offset") || 0);
}

export function writeFiltersToUrl() {
  const params = new URLSearchParams();
  const { q, userIds, chatType, direction, ingestionSource, topics, dateFrom, dateTo } =
    inboxState.filters;
  if (q) params.set("q", q);
  if (userIds.length) params.set("user_ids", userIds.join(","));
  if (chatType) params.set("chat_type", chatType);
  if (direction) params.set("direction", direction);
  if (ingestionSource) params.set("ingestion_source", ingestionSource);
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
  const sourceEl = document.getElementById("inbox-source");
  if (sourceEl) sourceEl.value = inboxState.filters.ingestionSource;
  document.getElementById("inbox-date-from").value = inboxState.filters.dateFrom;
  document.getElementById("inbox-date-to").value = inboxState.filters.dateTo;
  document.getElementById("inbox-view").value = inboxState.view;

  const select = document.getElementById("inbox-users");
  [...select.options].forEach((option) => {
    if (!option.value) return;
    option.selected = inboxState.filters.userIds.includes(option.value);
  });
  updateTopicsFilterBadge();
  renderTopicFilterChips(cachedTopics);
}

function updateTopicsFilterBadge() {
  const badge = document.getElementById("filters-topic-badge");
  const toggleBtn = document.getElementById("toggle-filters");
  const active = Boolean(inboxState.filters.topics?.trim());
  if (badge) badge.hidden = !active;
  toggleBtn?.classList.toggle("has-topic-filter", active);
}

function renderTopicSuggestions(topics = []) {
  const datalist = document.getElementById("topic-suggestions");
  if (!datalist) return;
  datalist.innerHTML = topics
    .map((topic) => `<option value="${escapeHtml(topic.name)}"></option>`)
    .join("");
}

function renderTopicFilterChips(topics = []) {
  const strip = document.getElementById("topic-filter-chips");
  if (!strip) return;
  const activeTopic = (inboxState.filters.topics || "").trim().toLowerCase();

  if (!topics.length) {
    strip.innerHTML = `
      <span class="topic-filter-empty">No topic tags yet.</span>
      <button type="button" class="btn btn-ghost btn-sm" data-action="backfill-topics">Generate AI tags</button>`;
    return;
  }

  const top = topics.slice(0, TOPIC_CHIP_LIMIT);
  strip.innerHTML = top
    .map(
      (topic) =>
        `<button type="button" class="topic-filter-chip${activeTopic === topic.name ? " active" : ""}" data-topic="${escapeHtml(topic.name)}">${escapeHtml(topic.name)} <span class="topic-filter-count">${topic.message_count}</span></button>`
    )
    .join("");
}

export async function runTopicBackfill({ onError, onNotify, limit = 40 } = {}) {
  const buttons = document.querySelectorAll('[data-action="backfill-topics"], #workflow-generate-tags');
  buttons.forEach((btn) => {
    btn.disabled = true;
    btn.dataset.originalLabel = btn.textContent;
    btn.textContent = "Generating…";
  });
  try {
    const result = await api.backfillTopics(limit);
    if (result.mode === "ai_assign") {
      workflowState.topicMode = "ai_assign";
      const select = document.getElementById("topic-mode");
      if (select) select.value = "ai_assign";
    }
    await loadTopicSuggestions();
    await loadInbox();
    const topicCount = result.topics_created?.length ?? 0;
    onNotify?.(
      `Tagged ${result.tagged} message(s)${topicCount ? ` · ${topicCount} topic(s)` : ""}.`
    );
    return result;
  } catch (error) {
    onError?.(error);
    throw error;
  } finally {
    buttons.forEach((btn) => {
      btn.disabled = false;
      btn.textContent = btn.dataset.originalLabel || "Generate AI tags";
    });
  }
}

export async function loadTopicSuggestions() {
  try {
    cachedTopics = await api.getTopics();
    renderTopicSuggestions(cachedTopics);
    renderTopicFilterChips(cachedTopics);
  } catch {
    /* keep existing suggestions */
  }
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

function sourceLabel(item) {
  return item.ingestion_source === "user_account" ? "My account" : "Bot";
}

function renderSourceBadge(item) {
  const cls = item.ingestion_source === "user_account" ? "user-account" : "bot";
  return `<span class="source-badge ${cls}">${sourceLabel(item)}</span>`;
}

function renderThreadMessages(messages) {
  return messages
    .map(
      (item) => `
      <li class="thread-message ${item.direction}">
        <div class="meta">
          <span>${escapeHtml(displayName(item))} · ${item.direction} ${renderSourceBadge(item)}</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        ${renderTopicChips(item.topics)}
        <div class="message-text">${escapeHtml(item.text)}</div>
      </li>`
    )
    .join("");
}

function emptyInboxHtml(view = "threads") {
  const topicHint =
    inboxState.filters.topics && workflowState.topicMode === "ai_assign"
      ? " AI assign mode only matches AI topic tags — switch to User type in Workflow, or use the message search box."
      : "";
  return buildInboxEmptyHtml({
    filters: inboxState.filters,
    view,
    topicHint,
  });
}

function renderFlatMessages(messages = []) {
  const feed = document.getElementById("messages-feed");
  if (!messages.length) {
    feed.innerHTML = emptyInboxHtml("flat");
    return;
  }

  feed.innerHTML = `<ul class="feed inbox-feed">${messages
    .map(
      (item) => `
      <li class="${item.direction}">
        <div class="meta">
          <span>${escapeHtml(displayName(item))} · ${item.chat_type || "chat"} · ${item.direction} ${renderSourceBadge(item)}</span>
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

function renderThreadContext(thread) {
  if (!thread.chat_id) return "";

  const expanded = inboxState.expandedContextChatIds.has(Number(thread.chat_id));
  const notes = thread.ai_context || "";
  const preview = notes
    ? escapeHtml(notes.length > 120 ? `${notes.slice(0, 120)}…` : notes)
    : "<em>No extra context yet.</em>";

  return `
    <div class="thread-context" data-chat-id="${thread.chat_id}">
      <div class="thread-context-toolbar">
        <strong>Your context</strong>
        <button type="button" class="btn btn-ghost btn-sm toggle-thread-context" data-chat-id="${thread.chat_id}">
          ${expanded ? "Hide" : notes ? "Edit" : "Add"}
        </button>
      </div>
      <p class="thread-context-preview" ${expanded ? "hidden" : ""}>${preview}</p>
      <div class="thread-context-editor" ${expanded ? "" : "hidden"}>
        <textarea
          class="thread-context-input"
          rows="3"
          data-chat-id="${thread.chat_id}"
          placeholder="Notes for the AI: aliases (y4ppy = yappy/yappie), people, topics, background…"
        >${escapeHtml(notes)}</textarea>
        <div class="thread-context-actions">
          <button type="button" class="btn btn-primary btn-sm save-thread-context" data-chat-id="${thread.chat_id}">
            Save context
          </button>
          <span class="thread-context-hint">Used by Summarize and AI suggestions</span>
        </div>
      </div>
    </div>`;
}

export function renderInboxThreads(threads = [], total = 0) {
  inboxState.threads = threads;
  inboxState.total = total;

  const feed = document.getElementById("messages-feed");
  if (!threads.length) {
    feed.innerHTML = emptyInboxHtml("threads");
  } else {
    feed.innerHTML = threads
      .map((thread, index) => {
        const chatId = thread.chat_id ?? `thread-${index}`;
        const typeBadge =
          thread.chat_type === "group"
            ? "Group"
            : thread.chat_type === "channel"
              ? "Channel"
              : "Private";
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
          ${renderThreadContext(thread)}
          <div class="thread-summary" id="summary-${chatId}" data-chat-id="${thread.chat_id ?? ""}">
            <div class="summary-toolbar">
              <strong>AI Summary</strong>
              ${
                thread.chat_id
                  ? `<button type="button" class="btn btn-ghost btn-sm summarize-thread-btn" data-chat-id="${thread.chat_id}" data-message-ids="${thread.messages.map((m) => m.id).join(",")}">Summarize</button>`
                  : ""
              }
            </div>
            <div class="summary-body"><em>No summary yet.</em></div>
          </div>
          <ul class="thread-messages">${renderThreadMessages(thread.messages)}</ul>
        </article>`;
      })
      .join("");
  }

  updateInboxCount(total, threads.length);
}

export function refreshInboxEmptyStateIfNeeded() {
  if (inboxState.view === "flat") {
    if (!inboxState.messages.length) {
      renderFlatMessages([]);
      updateInboxCount(inboxState.total || 0, 0);
    }
    return;
  }
  if (!inboxState.threads.length) {
    renderInboxThreads([], inboxState.total || 0);
  }
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

function renderNameCorrections(corrections = []) {
  if (!corrections?.length) return "";
  const items = corrections
    .map((item) => `${escapeHtml(item.from)} → ${escapeHtml(item.to)}`)
    .join(", ");
  return `<p class="summary-corrections">Names corrected: ${items}</p>`;
}

function renderThreadSummaryPanel(summaryEl, result) {
  const body = summaryEl.querySelector(".summary-body");
  const btn = summaryEl.querySelector(".summarize-thread-btn");
  if (!body) return;

  if (!result?.summary) {
    body.innerHTML = "<em>Click Summarize to generate an AI summary.</em>";
    if (btn) {
      btn.textContent = "Summarize";
      btn.disabled = false;
    }
    return;
  }

  const redaction = result.redaction_applied
    ? `<p class="redaction-notice">Sensitive data redacted (${result.redaction_count}) before AI.</p>`
    : "";
  const stale = result.stale
    ? `<p class="summary-stale">New messages since this summary — click Refresh to update.</p>`
    : "";
  const meta = result.cached
    ? `<span class="summary-cached">Saved summary</span>`
    : `<span class="summary-cached">Just generated</span>`;

  body.innerHTML = `
    ${redaction}
    ${stale}
    ${renderNameCorrections(result.name_corrections)}
    ${
      result.provider === "fallback"
        ? `<p class="fallback-notice">AI unavailable — showing basic overview.</p>`
        : ""
    }
    ${
      result.degraded || result.failure_reason
        ? `<p class="degradation-notice">${escapeHtml(result.failure_reason || "Using fallback provider")}</p>`
        : ""
    }
    <p>${escapeHtml(result.summary)}</p>
    <span class="summary-provider">${meta} · via ${escapeHtml(result.provider || "ai")}</span>`;

  if (btn) {
    btn.textContent = result.summary ? "Refresh summary" : "Summarize";
    btn.disabled = false;
  }
}

async function loadCachedThreadSummary(thread, index) {
  const chatId = thread.chat_id ?? `thread-${index}`;
  const summaryEl = document.getElementById(`summary-${chatId}`);
  if (!summaryEl || !thread.chat_id || thread.messages.length < 1) {
    if (summaryEl) {
      summaryEl.querySelector(".summary-body").innerHTML = "<em>No summary available.</em>";
    }
    return;
  }

  try {
    const messageIds = thread.messages.map((m) => m.id);
    const result = await api.getThreadSummary(thread.chat_id, messageIds);
    if (result.summary) {
      renderThreadSummaryPanel(summaryEl, result);
    }
  } catch {
    /* keep default placeholder */
  }
}

async function requestThreadSummary(chatId, messageIds, { force = false, summaryEl } = {}) {
  const btn = summaryEl?.querySelector(".summarize-thread-btn");
  const body = summaryEl?.querySelector(".summary-body");
  if (btn) {
    btn.disabled = true;
    btn.textContent = force ? "Refreshing…" : "Summarizing…";
  }
  if (body) {
    body.innerHTML = `<p class="summary-loading">${force ? "Refreshing" : "Generating"} AI summary…</p>`;
  }

  try {
    const result = await api.summarizeThread(chatId, messageIds, { force });
    renderThreadSummaryPanel(summaryEl, result);
    return result;
  } catch (error) {
    if (body) {
      body.innerHTML = `<p class="error-text">${escapeHtml(error.message)}</p>`;
    }
    if (btn) {
      btn.disabled = false;
      btn.textContent = force ? "Refresh summary" : "Summarize";
    }
    throw error;
  }
}

async function loadCachedSummariesForThreads(threads) {
  await Promise.all(threads.map((thread, index) => loadCachedThreadSummary(thread, index)));
}

export function clearInboxFilters(onError) {
  // Reset to the default inbox view: today only.
  inboxState.filters = {
    q: "",
    topics: "",
    userIds: [],
    chatType: "",
    direction: "",
    ingestionSource: "",
    ...defaultDateFilters(),
  };
  syncFilterForm();
  return loadInbox().catch(onError);
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
    ingestionSource: document.getElementById("inbox-source")?.value || "",
    dateFrom: document.getElementById("inbox-date-from").value,
    dateTo: document.getElementById("inbox-date-to").value,
  };
  inboxState.view = document.getElementById("inbox-view").value;
}

export async function loadInbox({ append = false } = {}) {
  if (!append) {
    collectFiltersFromForm();
    inboxState.offset = 0;
  }

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
  await loadCachedSummariesForThreads(append ? result.threads : threads);
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
    ingestionSource: f.ingestionSource || f.ingestion_source || "",
    dateFrom: f.dateFrom || f.date_from || "",
    dateTo: f.dateTo || f.date_to || "",
  };
  inboxState.view = f.view || "threads";
  syncFilterForm();
}

function applyFiltersNow(onError) {
  clearTimeout(filterDebounceTimer);
  collectFiltersFromForm();
  updateTopicsFilterBadge();
  loadInbox().catch(onError);
}

function scheduleFilterApply(onError) {
  clearTimeout(filterDebounceTimer);
  filterDebounceTimer = setTimeout(() => applyFiltersNow(onError), FILTER_DEBOUNCE_MS);
}

function bindFilterInput(id, onError) {
  const el = document.getElementById(id);
  if (!el) return;
  el.addEventListener("search", () => applyFiltersNow(onError));
  el.addEventListener("input", () => scheduleFilterApply(onError));
}

function handleEmptyStateAction(action, button, { onError, onOpenTools, onRefresh } = {}) {
  if (action === "clear-filters") {
    clearInboxFilters(onError);
    return true;
  }
  if (action === "refresh-inbox") {
    if (onRefresh) onRefresh();
    else loadInbox().catch(onError);
    return true;
  }
  if (action === "open-tools") {
    onOpenTools?.();
    return true;
  }
  if (action === "toggle-connect-details") {
    const details = button.closest(".empty-thread-setup")?.querySelector(".empty-thread-details");
    if (!details) return true;
    const open = details.hidden;
    details.hidden = !open;
    button.setAttribute("aria-expanded", String(open));
    button.textContent = open ? "Hide details" : "How to connect";
    return true;
  }
  return false;
}

export function bindInbox(onReply, onError, onNotify, { onOpenTools, onRefresh } = {}) {
  readFiltersFromUrl();
  syncFilterForm();
  loadPresets().catch(onError);
  loadTopicSuggestions().catch(onError);

  const toggleBtn = document.getElementById("toggle-filters");
  const advanced = document.getElementById("advanced-filters");
  toggleBtn?.addEventListener("click", () => {
    const open = advanced.hidden;
    advanced.hidden = !open;
    toggleBtn.setAttribute("aria-expanded", String(open));
    toggleBtn.classList.toggle("active", open);
  });

  initAiPanel();

  document.getElementById("inbox-apply").addEventListener("click", () => applyFiltersNow(onError));

  document.getElementById("inbox-clear").addEventListener("click", () => {
    clearInboxFilters(onError);
  });

  bindFilterInput("inbox-search", onError);
  bindFilterInput("inbox-topics", onError);

  document.getElementById("topic-filter-chips")?.addEventListener("click", (event) => {
    const backfillBtn = event.target.closest('[data-action="backfill-topics"]');
    if (backfillBtn) {
      runTopicBackfill({ onError, onNotify }).catch(onError);
      return;
    }
    const chip = event.target.closest(".topic-filter-chip");
    if (!chip) return;
    document.getElementById("inbox-topics").value = chip.dataset.topic || "";
    applyFiltersNow(onError);
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
    const emptyActionBtn = event.target.closest("[data-empty-action]");
    if (emptyActionBtn) {
      handleEmptyStateAction(emptyActionBtn.dataset.emptyAction, emptyActionBtn, {
        onError,
        onOpenTools,
        onRefresh,
      });
      return;
    }

    const toggleContextBtn = event.target.closest(".toggle-thread-context");
    if (toggleContextBtn) {
      const chatId = Number(toggleContextBtn.dataset.chatId);
      if (inboxState.expandedContextChatIds.has(chatId)) {
        inboxState.expandedContextChatIds.delete(chatId);
      } else {
        inboxState.expandedContextChatIds.add(chatId);
      }
      renderInboxThreads(inboxState.threads, inboxState.total);
      return;
    }

    const saveContextBtn = event.target.closest(".save-thread-context");
    if (saveContextBtn) {
      const chatId = Number(saveContextBtn.dataset.chatId);
      const textarea = document.querySelector(`.thread-context-input[data-chat-id="${chatId}"]`);
      const aiContext = textarea?.value.trim() ?? "";
      saveContextBtn.disabled = true;
      api
        .updateChatSettings(chatId, { ai_context: aiContext })
        .then((saved) => {
          const thread = inboxState.threads.find((item) => Number(item.chat_id) === chatId);
          if (thread) {
            thread.ai_context = saved.ai_context || "";
          }
          inboxState.expandedContextChatIds.delete(chatId);
          renderInboxThreads(inboxState.threads, inboxState.total);
          onNotify?.("Chat context saved.");
        })
        .catch(onError)
        .finally(() => {
          saveContextBtn.disabled = false;
        });
      return;
    }

    const summarizeBtn = event.target.closest(".summarize-thread-btn");
    if (summarizeBtn) {
      const chatId = Number(summarizeBtn.dataset.chatId);
      const messageIds = (summarizeBtn.dataset.messageIds || "")
        .split(",")
        .filter(Boolean)
        .map(Number);
      const summaryEl = document.getElementById(`summary-${chatId}`);
      const force = summarizeBtn.textContent.toLowerCase().includes("refresh");
      requestThreadSummary(chatId, messageIds, { force, summaryEl }).catch(onError);
      return;
    }

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

function initAiPanel() {
  const layout = document.getElementById("inbox-layout");
  const toggleBtn = document.getElementById("toggle-ai-panel");
  const closeBtn = document.getElementById("close-ai-panel");
  const backdrop = document.getElementById("ai-drawer-backdrop");
  if (!layout || !toggleBtn) return;

  const isMobile = () => window.matchMedia("(max-width: 1100px)").matches;

  function setOpen(open) {
    layout.classList.toggle("ai-panel-open", open);
    toggleBtn.setAttribute("aria-expanded", String(open));
    toggleBtn.textContent = open ? "Hide AI" : "AI panel";
    if (backdrop) {
      backdrop.hidden = !(open && isMobile());
      backdrop.setAttribute("aria-hidden", String(!(open && isMobile())));
    }
  }

  toggleBtn.addEventListener("click", () => setOpen(!layout.classList.contains("ai-panel-open")));
  closeBtn?.addEventListener("click", () => setOpen(false));
  backdrop?.addEventListener("click", () => setOpen(false));
  window.addEventListener("resize", () => {
    if (!isMobile() && backdrop) backdrop.hidden = true;
  });

  setOpen(!isMobile());
}
