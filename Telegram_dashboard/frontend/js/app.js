import { api, connectWebSocket } from "./api.js";
import { renderCommandChart } from "./chart.js";
import { initTheme } from "./theme.js";

const state = {
  quickActions: [],
};

function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return date.toLocaleString();
}

function renderMetrics(metrics = {}) {
  document.getElementById("connected-users").textContent = metrics.connected_users ?? 0;
  document.getElementById("total-messages").textContent = metrics.total_messages ?? 0;
  document.getElementById("total-commands").textContent = metrics.total_commands ?? 0;
}

function renderMessages(messages = []) {
  const feed = document.getElementById("messages-feed");
  feed.innerHTML = messages
    .map(
      (item) => `
      <li class="${item.direction}">
        <div class="meta">
          <span>${item.username || `User ${item.user_id}`} · ${item.direction}</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        <div>${escapeHtml(item.text)}</div>
      </li>`
    )
    .join("");
}

function renderEvents(events = []) {
  const feed = document.getElementById("events-feed");
  feed.innerHTML = events
    .map(
      (item) => `
      <li>
        <div class="meta">
          <span>${item.event_type}</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        <div>${escapeHtml(JSON.stringify(item.payload))}</div>
      </li>`
    )
    .join("");
}

function renderFeedback(items = []) {
  const feed = document.getElementById("feedback-feed");
  feed.innerHTML = items
    .map(
      (item) => `
      <li>
        <div class="meta">
          <span>${item.username || "Anonymous"} · ${item.rating}/5</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        <div>${escapeHtml(item.comment)}</div>
      </li>`
    )
    .join("");
}

function renderQuickActions(actions = []) {
  state.quickActions = actions;
  const panel = document.getElementById("quick-actions");
  panel.innerHTML = actions
    .map(
      (action, index) => `
      <div class="action-row" data-index="${index}">
        <input class="action-label" value="${escapeHtml(action.label)}" />
        <input class="action-command" value="${escapeHtml(action.command)}" />
        <button class="btn btn-ghost btn-sm run-action" type="button">Run</button>
        <button class="btn btn-danger btn-sm remove-action" type="button">Remove</button>
      </div>`
    )
    .join("");

  panel.querySelectorAll(".run-action").forEach((button) => {
    button.addEventListener("click", async (event) => {
      const row = event.target.closest(".action-row");
      const command = row.querySelector(".action-command").value.trim();
      const chatId = document.getElementById("chat-id").value.trim();
      if (!chatId) {
        showToast("Enter a chat ID before running a quick action.");
        return;
      }
      try {
        await api.sendMessage(chatId, command);
        showToast(`Sent ${command}`);
        await refreshAll();
      } catch (error) {
        showToast(error.message);
      }
    });
  });

  panel.querySelectorAll(".remove-action").forEach((button) => {
    button.addEventListener("click", (event) => {
      const row = event.target.closest(".action-row");
      const index = Number(row.dataset.index);
      state.quickActions.splice(index, 1);
      renderQuickActions(state.quickActions);
    });
  });
}

function collectQuickActionsFromDom() {
  return [...document.querySelectorAll(".action-row")].map((row) => ({
    label: row.querySelector(".action-label").value.trim(),
    command: row.querySelector(".action-command").value.trim(),
    enabled: true,
  }));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function refreshAll() {
  const [metrics, messages, events, analytics, quickActions, feedback, botStatus] =
    await Promise.all([
      api.getMetrics(),
      api.getMessages(),
      api.getEvents(),
      api.getAnalytics(),
      api.getQuickActions(),
      api.getFeedback(),
      api.getBotStatus(),
    ]);

  renderMetrics(metrics);
  renderMessages(messages);
  renderEvents(events);
  renderCommandChart(document.getElementById("command-chart"), analytics);
  renderQuickActions(quickActions);
  renderFeedback(feedback);

  const status = document.getElementById("bot-status");
  if (botStatus.configured && botStatus.bot) {
    status.textContent = `Connected as @${botStatus.bot.username}`;
  } else if (botStatus.configured) {
    status.textContent = "Bot token configured, unable to verify bot.";
  } else {
    status.textContent = "Telegram bot token not configured.";
  }
}

function bindForms() {
  document.getElementById("refresh-btn").addEventListener("click", () => {
    refreshAll().catch((error) => showToast(error.message));
  });

  document.getElementById("send-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const chatId = document.getElementById("chat-id").value.trim();
    const text = document.getElementById("message-text").value.trim();
    try {
      await api.sendMessage(chatId, text);
      document.getElementById("message-text").value = "";
      showToast("Message sent.");
      await refreshAll();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("feedback-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const rating = Number(document.getElementById("feedback-rating").value);
    const comment = document.getElementById("feedback-comment").value.trim();
    try {
      await api.submitFeedback({ rating, comment, username: "dashboard_user" });
      document.getElementById("feedback-comment").value = "";
      showToast("Feedback submitted.");
      await refreshAll();
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("add-action-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const label = document.getElementById("action-label").value.trim();
    const command = document.getElementById("action-command").value.trim();
    state.quickActions.push({ label, command, enabled: true });
    renderQuickActions(state.quickActions);
    document.getElementById("action-label").value = "";
    document.getElementById("action-command").value = "";
  });

  document.getElementById("save-actions-btn").addEventListener("click", async () => {
    try {
      const actions = collectQuickActionsFromDom();
      await api.saveQuickActions(actions);
      showToast("Quick actions saved.");
      await refreshAll();
    } catch (error) {
      showToast(error.message);
    }
  });
}

function handleRealtime(message) {
  const { event, data } = message;
  if (event === "snapshot") {
    renderMetrics(data.metrics);
    renderMessages(data.messages);
    renderEvents(data.events);
    renderQuickActions(data.quick_actions);
    renderFeedback(data.feedback);
    renderCommandChart(document.getElementById("command-chart"), data.analytics);
    return;
  }

  if (event === "telegram_update" || event === "message_sent") {
    refreshAll().catch(() => {});
  }

  if (event === "feedback_received") {
    renderFeedback([data, ...state.feedback || []]);
  }

  if (event === "quick_actions_updated") {
    renderQuickActions(data.actions);
  }
}

async function init() {
  initTheme();
  bindForms();

  try {
    await refreshAll();
  } catch (error) {
    showToast(error.message);
  }

  connectWebSocket(handleRealtime);
}

init();
