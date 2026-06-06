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
  if (chat.chat_type === "group") return `Group ${chat.chat_id}`;
  return `Chat ${chat.chat_id}`;
}

export const workflowState = {
  replyMode: "manual",
  topicMode: "user_type",
  chats: [],
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
  if (!list) return;

  if (!workflowState.chats.length) {
    list.innerHTML = `<p class="filter-hint">No chats yet. Messages will appear here.</p>`;
    return;
  }

  list.innerHTML = workflowState.chats
    .map(
      (chat) => `
      <label class="chat-toggle-row">
        <span>
          <strong>${escapeHtml(chatLabel(chat))}</strong>
          <span class="filter-hint">${chat.message_count || 0} messages · ${chat.chat_type || "chat"}</span>
        </span>
        <input
          type="checkbox"
          class="chat-auto-reply"
          data-chat-id="${chat.chat_id}"
          ${chat.auto_reply_enabled ? "checked" : ""}
        />
      </label>`
    )
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
    try {
      await api.setChatAutoReply(Number(input.dataset.chatId), input.checked);
      const chat = workflowState.chats.find((c) => c.chat_id === Number(input.dataset.chatId));
      if (chat) chat.auto_reply_enabled = input.checked ? 1 : 0;
      onChange?.("Chat auto-reply updated.");
    } catch (error) {
      onError?.(error.message);
    }
  });
}

export function topicModeLabel() {
  return TOPIC_LABELS[workflowState.topicMode] || workflowState.topicMode;
}
