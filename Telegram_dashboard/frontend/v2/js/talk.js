import { api } from "./api.js";
import { asList, escapeHtml, formatTime, showToast, threadTitle } from "./utils.js";
import { openProfileChat } from "./profiles.js";

const state = {
  threads: [],
  selectedChatId: null,
  messages: [],
  loadingThreads: false,
  loadingMessages: false,
  loadError: null,
  messageError: null,
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
    <div class="talk-workspace">
      <p class="view-hint">What others are saying on your personal account. Pick a thread, then decide if Act or Profiles need an update.</p>
      <div class="panel-grid talk-grid">
        <aside class="panel talk-threads">
          <div class="panel-header">
            <div>
              <h2>Threads</h2>
              <p class="panel-sub" id="talk-thread-count"></p>
            </div>
            <div class="panel-actions">
              <button type="button" class="btn btn-ghost" id="talk-refresh">Refresh</button>
            </div>
          </div>
          <div class="panel-body tight" id="talk-thread-list"></div>
        </aside>
        <section class="panel talk-messages">
          <div class="panel-header">
            <h2 id="talk-pane-title">Messages</h2>
            <div class="panel-actions">
              <button type="button" class="btn btn-primary" id="talk-create-profile" disabled title="Create or refresh a Markdown profile for this chat">
                Create profile
              </button>
            </div>
          </div>
          <div class="panel-body" id="talk-message-pane">
            <p class="empty-state">Select a thread to read the conversation.</p>
          </div>
        </section>
      </div>
    </div>
  `;

  el.querySelector("#talk-refresh").addEventListener("click", () => loadThreads());
  el.querySelector("#talk-create-profile").addEventListener("click", () => createProfileFromThread());
}

function setCreateProfileEnabled(enabled) {
  const btn = document.getElementById("talk-create-profile");
  if (btn) btn.disabled = !enabled;
}

function stubMarkdown(chatId, name) {
  const safe = String(name || `Chat ${chatId}`).replace(/"/g, "'");
  return [
    "---",
    `chat_id: ${chatId}`,
    `name: "${safe}"`,
    `updated_at: ${new Date().toISOString()}`,
    "relationship: ",
    "---",
    "",
    "## Summary",
    "",
    "(Created from Talk — use Refresh from chat to fill from history.)",
    "",
    "## Relationship",
    "",
    "",
    "## Facts/Memories",
    "",
    "",
    "## Notes",
    "",
    "",
  ].join("\n");
}

async function createProfileFromThread() {
  const chatId = state.selectedChatId;
  if (chatId == null) return;
  const btn = document.getElementById("talk-create-profile");
  if (btn) btn.disabled = true;
  const thread = state.threads.find((t) => String(t.chat_id) === String(chatId));
  const name = thread ? threadTitle(thread) : `Chat ${chatId}`;
  try {
    try {
      await api.refreshProfile(chatId);
      showToast("Profile created from chat");
    } catch (err) {
      // No messages / AI down — still create an editable stub on disk
      await api.saveProfile(chatId, {
        name,
        markdown: stubMarkdown(chatId, name),
      });
      showToast(err.message ? `Stub profile saved (${err.message})` : "Stub profile saved");
    }
    sessionStorage.setItem("v2-profiles-chat", String(chatId));
    const next = `#profiles?chat=${encodeURIComponent(chatId)}`;
    if (window.location.hash === next) {
      await openProfileChat(chatId, { forceReload: true });
    } else {
      window.location.hash = next;
    }
  } catch (err) {
    showToast(err.message || "Could not create profile", { error: true });
  } finally {
    setCreateProfileEnabled(Boolean(state.selectedChatId));
  }
}

function renderThreads() {
  const list = document.getElementById("talk-thread-list");
  const count = document.getElementById("talk-thread-count");
  if (!list) return;

  if (count) {
    count.textContent = state.loadingThreads
      ? "Refreshing…"
      : `${state.threads.length} conversation${state.threads.length === 1 ? "" : "s"}`;
  }

  if (state.loadingThreads) {
    list.innerHTML = `<p class="loading-state">Loading threads…</p>`;
    return;
  }

  if (state.loadError) {
    list.innerHTML = `
      <div class="empty-card">
        <p class="error-state">${escapeHtml(state.loadError)}</p>
        <button type="button" class="btn btn-primary" id="talk-retry">Try again</button>
      </div>`;
    list.querySelector("#talk-retry")?.addEventListener("click", () => loadThreads());
    return;
  }

  if (!state.threads.length) {
    list.innerHTML = `
      <div class="empty-card">
        <p class="empty-state">No personal-account threads yet.</p>
        <p class="empty-detail">Enable MTProto ingest, or open the classic dashboard if you still need the bot inbox.</p>
        <a class="btn btn-ghost" href="/">Open classic dashboard</a>
      </div>`;
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
    setCreateProfileEnabled(false);
    return;
  }

  setCreateProfileEnabled(!state.loadingMessages && !state.messageError);

  if (state.loadingMessages) {
    pane.innerHTML = `<p class="loading-state">Loading messages…</p>`;
    return;
  }

  if (state.messageError) {
    pane.innerHTML = `<p class="error-state">${escapeHtml(state.messageError)}</p>`;
    return;
  }

  if (!state.messages.length) {
    pane.innerHTML = `
      <div class="empty-card">
        <p class="empty-state">No messages in this thread.</p>
        <p class="empty-detail">You can still create a stub profile, then fill it later.</p>
      </div>`;
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
  state.loadError = null;
  renderThreads();
  try {
    const data = await api.getTalkThreads();
    state.threads = asList(data, ["threads", "items"]);
    if (state.selectedChatId) {
      const stillThere = state.threads.some(
        (t) => String(t.chat_id) === String(state.selectedChatId),
      );
      if (!stillThere) {
        state.selectedChatId = null;
        state.messages = [];
      }
    }
  } catch (err) {
    state.loadError = err.message || "Failed to load threads";
    showToast(state.loadError, { error: true });
  } finally {
    state.loadingThreads = false;
    renderThreads();
    renderMessages();
  }
}

async function selectThread(chatId) {
  state.selectedChatId = chatId;
  state.loadingMessages = true;
  state.messageError = null;
  renderThreads();
  renderMessages();
  try {
    const data = await api.getTalkMessages(chatId);
    state.messages = asList(data, ["messages", "items"]);
  } catch (err) {
    state.messageError = err.message || "Failed to load messages";
    showToast(state.messageError, { error: true });
  } finally {
    state.loadingMessages = false;
    renderThreads();
    renderMessages();
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
  await selectThread(chatId);
}

export function refreshTalkIfVisible() {
  const el = root();
  if (el?.classList.contains("is-visible")) {
    return loadThreads();
  }
  return Promise.resolve();
}
