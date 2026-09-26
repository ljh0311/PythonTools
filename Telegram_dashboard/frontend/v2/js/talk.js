import { api } from "./api.js";
import { asList, escapeHtml, formatTime, showToast, threadTitle } from "./utils.js";

const state = {
  threads: [],
  selectedChatId: null,
  messages: [],
  loadingThreads: false,
  loadingMessages: false,
};

function root() {
  return document.getElementById("view-talk");
}

function previewText(thread) {
  if (thread.preview) return thread.preview;
  const msgs = thread.messages || [];
  const last = msgs[msgs.length - 1];
  return last?.text || thread.last_text || "No messages yet";
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="panel-grid">
      <aside class="panel">
        <div class="panel-header">
          <h2>Threads</h2>
          <div class="panel-actions">
            <button type="button" class="btn btn-ghost" id="talk-refresh">Refresh</button>
          </div>
        </div>
        <div class="panel-body" id="talk-thread-list"></div>
      </aside>
      <section class="panel">
        <div class="panel-header">
          <h2 id="talk-pane-title">Messages</h2>
        </div>
        <div class="panel-body" id="talk-message-pane">
          <p class="empty-state">Select a thread to read the conversation.</p>
        </div>
      </section>
    </div>
  `;

  el.querySelector("#talk-refresh").addEventListener("click", () => loadThreads());
}

function renderThreads() {
  const list = document.getElementById("talk-thread-list");
  if (!list) return;

  if (state.loadingThreads) {
    list.innerHTML = `<p class="loading-state">Loading threads…</p>`;
    return;
  }

  if (!state.threads.length) {
    list.innerHTML = `<p class="empty-state">No personal threads yet. MTProto ingest will fill this list.</p>`;
    return;
  }

  list.innerHTML = state.threads
    .map((thread) => {
      const chatId = thread.chat_id;
      const active = String(chatId) === String(state.selectedChatId);
      return `
        <button type="button" class="list-item ${active ? "is-active" : ""}" data-chat-id="${escapeHtml(chatId)}">
          <p class="list-title">${escapeHtml(threadTitle(thread))}</p>
          <p class="list-meta">${escapeHtml(thread.chat_type || "private")} · ${escapeHtml(formatTime(thread.latest_at || thread.updated_at))}</p>
          <p class="list-preview">${escapeHtml(previewText(thread))}</p>
        </button>
      `;
    })
    .join("");

  list.querySelectorAll("[data-chat-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const chatId = btn.getAttribute("data-chat-id");
      selectThread(chatId);
    });
  });
}

function speakerLabel(msg) {
  if (msg.username) return `@${msg.username}`;
  if (msg.direction === "outgoing") return "You";
  if (msg.user_id != null) return `User ${msg.user_id}`;
  return "Unknown";
}

function renderMessages() {
  const pane = document.getElementById("talk-message-pane");
  const title = document.getElementById("talk-pane-title");
  if (!pane || !title) return;

  const thread = state.threads.find((t) => String(t.chat_id) === String(state.selectedChatId));
  title.textContent = thread ? threadTitle(thread) : "Messages";

  if (!state.selectedChatId) {
    pane.innerHTML = `<p class="empty-state">Select a thread to read the conversation.</p>`;
    return;
  }

  if (state.loadingMessages) {
    pane.innerHTML = `<p class="loading-state">Loading messages…</p>`;
    return;
  }

  if (!state.messages.length) {
    pane.innerHTML = `<p class="empty-state">No messages in this thread.</p>`;
    return;
  }

  pane.innerHTML = `
    <div class="message-list">
      ${state.messages
        .map((msg) => {
          const outgoing = msg.direction === "outgoing";
          return `
            <article class="message-bubble ${outgoing ? "is-out" : ""}">
              <p class="message-who">${escapeHtml(speakerLabel(msg))} · ${escapeHtml(formatTime(msg.created_at || msg.timestamp))}</p>
              <p class="message-text">${escapeHtml(msg.text || msg.body || "")}</p>
            </article>
          `;
        })
        .join("")}
    </div>
  `;
  pane.scrollTop = pane.scrollHeight;
}

async function loadThreads() {
  state.loadingThreads = true;
  renderThreads();
  try {
    const data = await api.getTalkThreads();
    state.threads = asList(data, ["threads", "items"]);
    renderThreads();
    if (state.selectedChatId) {
      const stillThere = state.threads.some(
        (t) => String(t.chat_id) === String(state.selectedChatId),
      );
      if (!stillThere) {
        state.selectedChatId = null;
        state.messages = [];
        renderMessages();
      }
    }
  } catch (err) {
    const list = document.getElementById("talk-thread-list");
    if (list) {
      list.innerHTML = `<p class="error-state">${escapeHtml(err.message || "Failed to load threads")}</p>`;
    }
    showToast(err.message || "Failed to load threads", { error: true });
  } finally {
    state.loadingThreads = false;
  }
}

async function selectThread(chatId) {
  state.selectedChatId = chatId;
  state.loadingMessages = true;
  renderThreads();
  renderMessages();
  try {
    const data = await api.getTalkMessages(chatId);
    state.messages = asList(data, ["messages", "items"]);
    renderMessages();
  } catch (err) {
    const pane = document.getElementById("talk-message-pane");
    if (pane) {
      pane.innerHTML = `<p class="error-state">${escapeHtml(err.message || "Failed to load messages")}</p>`;
    }
    showToast(err.message || "Failed to load messages", { error: true });
  } finally {
    state.loadingMessages = false;
  }
}

export async function mountTalk() {
  renderShell();
  await loadThreads();
  const pending = sessionStorage.getItem("v2-talk-chat");
  if (pending) {
    sessionStorage.removeItem("v2-talk-chat");
    await openTalkChat(pending);
  }
}

export async function openTalkChat(chatId) {
  if (chatId == null || chatId === "") return;
  if (!root()?.querySelector(".talk-workspace")) {
    sessionStorage.setItem("v2-talk-chat", String(chatId));
    return;
  }
  const exists = state.threads.some((t) => String(t.chat_id) === String(chatId));
  if (!exists && state.threads.length) {
    // Still open — messages endpoint may work even if not in current page
  }
  await selectThread(chatId);
}

export function refreshTalkIfVisible() {
  const el = root();
  if (el?.classList.contains("is-visible")) {
    return loadThreads();
  }
  return Promise.resolve();
}
