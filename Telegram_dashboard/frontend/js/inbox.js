import { api } from "./api.js";

const DEFAULT_LIMIT = 20;

export const inboxState = {
  users: [],
  items: [],
  total: 0,
  offset: 0,
  limit: DEFAULT_LIMIT,
  filters: {
    q: "",
    userIds: [],
    chatType: "",
    direction: "",
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

function chatLabel(item) {
  if (item.chat_type === "group") {
    return item.chat_title ? `Group: ${item.chat_title}` : "Group chat";
  }
  return "Private";
}

export function readFiltersFromUrl() {
  const params = new URLSearchParams(window.location.search);
  inboxState.filters.q = params.get("q") || "";
  inboxState.filters.chatType = params.get("chat_type") || "";
  inboxState.filters.direction = params.get("direction") || "";
  inboxState.filters.dateFrom = params.get("from") || "";
  inboxState.filters.dateTo = params.get("to") || "";
  const userIds = params.get("user_ids");
  inboxState.filters.userIds = userIds ? userIds.split(",").filter(Boolean) : [];
  inboxState.offset = Number(params.get("offset") || 0);
}

export function writeFiltersToUrl() {
  const params = new URLSearchParams();
  const { q, userIds, chatType, direction, dateFrom, dateTo } = inboxState.filters;
  if (q) params.set("q", q);
  if (userIds.length) params.set("user_ids", userIds.join(","));
  if (chatType) params.set("chat_type", chatType);
  if (direction) params.set("direction", direction);
  if (dateFrom) params.set("from", dateFrom);
  if (dateTo) params.set("to", dateTo);
  if (inboxState.offset) params.set("offset", String(inboxState.offset));
  const query = params.toString();
  const next = query ? `?${query}` : window.location.pathname;
  window.history.replaceState({}, "", next);
}

export function syncFilterForm() {
  document.getElementById("inbox-search").value = inboxState.filters.q;
  document.getElementById("inbox-chat-type").value = inboxState.filters.chatType;
  document.getElementById("inbox-direction").value = inboxState.filters.direction;
  document.getElementById("inbox-date-from").value = inboxState.filters.dateFrom;
  document.getElementById("inbox-date-to").value = inboxState.filters.dateTo;

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

export function renderInbox(items = [], total = 0) {
  inboxState.items = items;
  inboxState.total = total;

  const feed = document.getElementById("messages-feed");
  if (!items.length) {
    feed.innerHTML = `<li class="empty">No messages match your filters.</li>`;
  } else {
    feed.innerHTML = items
      .map(
        (item) => `
        <li class="${item.direction}">
          <div class="meta">
            <span>
              ${escapeHtml(displayName(item))}
              · ${item.direction}
              · <span class="badge">${escapeHtml(chatLabel(item))}</span>
            </span>
            <span>${formatTime(item.created_at)}</span>
          </div>
          <div class="message-text">${escapeHtml(item.text)}</div>
          <div class="message-actions">
            ${
              item.chat_id
                ? `<button type="button" class="btn btn-ghost btn-sm reply-btn" data-chat-id="${item.chat_id}">Reply</button>`
                : ""
            }
          </div>
        </li>`
      )
      .join("");
  }

  const countEl = document.getElementById("inbox-count");
  const showing = Math.min(inboxState.offset + items.length, total);
  countEl.textContent = `Showing ${showing} of ${total}`;

  const loadMoreBtn = document.getElementById("inbox-load-more");
  loadMoreBtn.disabled = inboxState.offset + items.length >= total;
  loadMoreBtn.hidden = inboxState.offset + items.length >= total;
}

export function collectFiltersFromForm() {
  const select = document.getElementById("inbox-users");
  const selected = [...select.selectedOptions].map((o) => o.value);
  inboxState.filters = {
    q: document.getElementById("inbox-search").value.trim(),
    userIds: selected,
    chatType: document.getElementById("inbox-chat-type").value,
    direction: document.getElementById("inbox-direction").value,
    dateFrom: document.getElementById("inbox-date-from").value,
    dateTo: document.getElementById("inbox-date-to").value,
  };
}

export async function loadInbox({ append = false } = {}) {
  if (!append) inboxState.offset = 0;

  const params = {
    limit: inboxState.limit,
    offset: inboxState.offset,
    q: inboxState.filters.q || undefined,
    chat_type: inboxState.filters.chatType || undefined,
    direction: inboxState.filters.direction || undefined,
    date_from: inboxState.filters.dateFrom || undefined,
    date_to: inboxState.filters.dateTo || undefined,
    user_ids: inboxState.filters.userIds.length
      ? inboxState.filters.userIds.join(",")
      : undefined,
  };

  const result = await api.getMessages(params);
  const items = append ? [...inboxState.items, ...result.items] : result.items;
  renderInbox(items, result.total);
  writeFiltersToUrl();
  return result;
}

export function bindInbox(onReply, onError) {
  readFiltersFromUrl();
  syncFilterForm();

  document.getElementById("inbox-apply").addEventListener("click", () => {
    collectFiltersFromForm();
    loadInbox().catch(onError);
  });

  document.getElementById("inbox-clear").addEventListener("click", () => {
    inboxState.filters = {
      q: "",
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

  document.getElementById("inbox-load-more").addEventListener("click", () => {
    inboxState.offset += inboxState.limit;
    loadInbox({ append: true }).catch(onError);
  });

  document.getElementById("messages-feed").addEventListener("click", (event) => {
    const button = event.target.closest(".reply-btn");
    if (!button) return;
    onReply(button.dataset.chatId);
  });
}
