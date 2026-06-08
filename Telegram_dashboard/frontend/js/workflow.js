import { api } from "./api.js";

const MODE_LABELS = {
  manual: "Operator approves",
  auto: "Auto-reply",
  per_chat: "Per-chat",
};

const TOPIC_LABELS = {
  user_type: "User type",
  ai_assign: "AI assign",
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function chatLabel(chat) {
  if (chat.chat_title) return chat.chat_title;
  if (chat.participants?.length) {
    return chat.participants.map((p) => `@${p}`).join(", ");
  }
  if (chat.chat_type === "group") return `Group ${chat.chat_id}`;
  return `Chat ${chat.chat_id}`;
}

function chatInitials(chat) {
  const label = chatLabel(chat);
  const parts = label.replace(/@/g, "").split(/[\s,]+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return (parts[0]?.slice(0, 2) || "CH").toUpperCase();
}

function relativeTime(iso) {
  if (!iso) return "No activity";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  const diffMs = Date.now() - date.getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export const workflowState = {
  replyMode: "manual",
  topicMode: "user_type",
  chats: [],
  expandedChatId: null,
};

function renderReplyMode() {
  const select = document.getElementById("reply-mode");
  if (select) select.value = workflowState.replyMode;

  const label = document.getElementById("reply-mode-label");
  if (label) label.textContent = MODE_LABELS[workflowState.replyMode] || workflowState.replyMode;

  const perChatPanel = document.getElementById("per-chat-panel");
  if (perChatPanel) {
    perChatPanel.hidden = workflowState.replyMode !== "per_chat";
  }

  const list = document.getElementById("per-chat-list");
  const countEl = document.getElementById("per-chat-count");
  if (!list) return;

  if (countEl) {
    countEl.textContent = `${workflowState.chats.length} chat${workflowState.chats.length === 1 ? "" : "s"}`;
  }

  if (!workflowState.chats.length) {
    list.innerHTML = `
      <div class="per-chat-empty">
        <p>No conversations yet</p>
        <span>Chats appear here once messages are received.</span>
      </div>`;
    return;
  }

  list.innerHTML = workflowState.chats
    .map((chat) => {
      const expanded = workflowState.expandedChatId === chat.chat_id;
      const relSource = chat.relationship_source === "manual" ? "Edited by you" : "AI generated";
      const typeLabel = chat.chat_type === "group" ? "Group" : "Private";
      return `
      <article class="chat-card ${chat.auto_reply_enabled ? "auto-on" : ""} ${expanded ? "expanded" : ""}" data-chat-id="${chat.chat_id}">
        <header class="chat-card-header">
          <div class="chat-avatar" aria-hidden="true">${escapeHtml(chatInitials(chat))}</div>
          <div class="chat-card-meta">
            <div class="chat-card-title-row">
              <h4>${escapeHtml(chatLabel(chat))}</h4>
              <span class="chat-type-pill">${typeLabel}</span>
            </div>
            <p class="chat-card-sub">
              ${chat.message_count || 0} messages · ${relativeTime(chat.last_message_at)}
            </p>
          </div>
          <label class="toggle-switch" title="Auto-reply for this chat">
            <input type="checkbox" class="chat-auto-reply" data-chat-id="${chat.chat_id}" ${chat.auto_reply_enabled ? "checked" : ""} />
            <span class="toggle-track"><span class="toggle-thumb"></span></span>
            <span class="toggle-label">Auto</span>
          </label>
        </header>
        <div class="chat-relationship">
          <div class="relationship-toolbar">
            <div>
              <strong>Relationship context</strong>
              <span class="relationship-source ${chat.relationship_source || "ai"}">${relSource}</span>
            </div>
            <div class="relationship-actions">
              <button type="button" class="btn btn-ghost btn-sm regenerate-relationship" data-chat-id="${chat.chat_id}" title="Regenerate from messages">
                Regenerate
              </button>
              <button type="button" class="btn btn-ghost btn-sm toggle-relationship" data-chat-id="${chat.chat_id}">
                ${expanded ? "Collapse" : "Edit"}
              </button>
            </div>
          </div>
          <p class="relationship-preview">${escapeHtml(chat.relationship || "Generating context…")}</p>
          <div class="relationship-editor" ${expanded ? "" : "hidden"}>
            <textarea class="relationship-input" rows="3" data-chat-id="${chat.chat_id}" placeholder="Who is this person or group? The AI uses this when drafting replies.">${escapeHtml(chat.relationship || "")}</textarea>
            <div class="relationship-editor-actions">
              <button type="button" class="btn btn-primary btn-sm save-relationship" data-chat-id="${chat.chat_id}">Save context</button>
            </div>
          </div>
        </div>
      </article>`;
    })
    .join("");
}

function renderTopicMode() {
  const select = document.getElementById("topic-mode");
  if (select) select.value = workflowState.topicMode;

  const hint = document.getElementById("topic-mode-hint");
  if (hint) {
    hint.textContent =
      workflowState.topicMode === "ai_assign"
        ? "New messages get AI topic tags automatically."
        : "Type topic keywords to search tags and message text.";
  }

  const topicFilter = document.getElementById("inbox-topics");
  if (topicFilter) {
    topicFilter.placeholder =
      workflowState.topicMode === "ai_assign"
        ? "Filter by AI tags (e.g. billing, scheduling)…"
        : "Filter by topic or text (e.g. billing)…";
  }
}

function updateChatInState(chatId, patch) {
  const chat = workflowState.chats.find((c) => c.chat_id === chatId);
  if (chat) Object.assign(chat, patch);
}

export async function loadWorkflowSettings() {
  const [reply, topic] = await Promise.all([
    api.getReplyMode(),
    api.getTopicMode(),
  ]);
  workflowState.replyMode = reply.mode;
  workflowState.chats = reply.chats || [];
  workflowState.topicMode = topic.mode;
  renderReplyMode();
  renderTopicMode();
}

export function bindWorkflow(onChange, onError) {
  document.getElementById("reply-mode")?.addEventListener("change", async (event) => {
    try {
      const result = await api.setReplyMode(event.target.value);
      workflowState.replyMode = result.mode;
      workflowState.chats = result.chats || [];
      renderReplyMode();
      onChange?.("Reply mode updated.");
    } catch (error) {
      onError?.(error.message);
    }
  });

  document.getElementById("topic-mode")?.addEventListener("change", async (event) => {
    try {
      const result = await api.setTopicMode(event.target.value);
      workflowState.topicMode = result.mode;
      renderTopicMode();
      onChange?.("Topic mode updated.");
    } catch (error) {
      onError?.(error.message);
    }
  });

  document.getElementById("per-chat-list")?.addEventListener("change", async (event) => {
    const input = event.target.closest(".chat-auto-reply");
    if (!input) return;
    const chatId = Number(input.dataset.chatId);
    try {
      const saved = await api.updateChatSettings(chatId, { enabled: input.checked });
      updateChatInState(chatId, saved);
      input.closest(".chat-card")?.classList.toggle("auto-on", input.checked);
      onChange?.("Auto-reply updated.");
    } catch (error) {
      input.checked = !input.checked;
      onError?.(error.message);
    }
  });

  document.getElementById("per-chat-list")?.addEventListener("click", async (event) => {
    const toggleBtn = event.target.closest(".toggle-relationship");
    if (toggleBtn) {
      const chatId = Number(toggleBtn.dataset.chatId);
      workflowState.expandedChatId = workflowState.expandedChatId === chatId ? null : chatId;
      renderReplyMode();
      return;
    }

    const saveBtn = event.target.closest(".save-relationship");
    if (saveBtn) {
      const chatId = Number(saveBtn.dataset.chatId);
      const textarea = document.querySelector(`.relationship-input[data-chat-id="${chatId}"]`);
      const relationship = textarea?.value.trim();
      if (!relationship) {
        onError?.("Relationship context cannot be empty.");
        return;
      }
      saveBtn.disabled = true;
      try {
        const saved = await api.updateChatSettings(chatId, { relationship });
        updateChatInState(chatId, saved);
        workflowState.expandedChatId = null;
        renderReplyMode();
        onChange?.("Relationship context saved.");
      } catch (error) {
        onError?.(error.message);
      } finally {
        saveBtn.disabled = false;
      }
      return;
    }

    const regenBtn = event.target.closest(".regenerate-relationship");
    if (regenBtn) {
      const chatId = Number(regenBtn.dataset.chatId);
      const card = regenBtn.closest(".chat-card");
      regenBtn.disabled = true;
      card?.classList.add("is-loading");
      try {
        const saved = await api.regenerateChatRelationship(chatId);
        updateChatInState(chatId, saved);
        workflowState.expandedChatId = chatId;
        renderReplyMode();
        onChange?.("Relationship regenerated from messages.");
      } catch (error) {
        onError?.(error.message);
      } finally {
        regenBtn.disabled = false;
        card?.classList.remove("is-loading");
      }
    }
  });
}

export function topicModeLabel() {
  return TOPIC_LABELS[workflowState.topicMode] || workflowState.topicMode;
}
