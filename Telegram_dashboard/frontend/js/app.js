import { api, connectWebSocket, ensureAuthenticated } from "./api.js";
import { renderCommandChart } from "./chart.js";
import { bindInsights } from "./insights.js";
import { bindInbox, loadInbox, renderUserFilter } from "./inbox.js";
import { initTheme } from "./theme.js";
import { initNavigation } from "./navigation.js";
import { bindWorkflow, loadWorkflowSettings } from "./workflow.js";

const state = {
  quickActions: [],
  nav: null,
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

function setMetric(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function renderMetrics(metrics = {}) {
  const users = metrics.connected_users ?? 0;
  const messages = metrics.total_messages ?? 0;
  const commands = metrics.total_commands ?? 0;
  setMetric("connected-users", users);
  setMetric("total-messages", messages);
  setMetric("total-commands", commands);
  setMetric("analytics-users", users);
  setMetric("analytics-messages", messages);
  setMetric("analytics-commands", commands);
}

function renderEvents(events = []) {
  const feed = document.getElementById("events-feed");
  const list = Array.isArray(events) ? events : [];
  feed.innerHTML = list
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

function renderQuickActions(actions = []) {
  const panel = document.getElementById("quick-actions");
  if (!panel) return;
  const list = Array.isArray(actions) ? actions : [];
  state.quickActions = list;
  panel.innerHTML = list
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
      const chatId =
        document.getElementById("chat-id")?.value.trim() ||
        document.getElementById("chat-id-tools")?.value.trim();
      if (!chatId) {
        showToast("Enter a chat ID in Inbox or Tools before running a quick action.");
        return;
      }
      try {
        await api.sendMessage(chatId, command);
        showToast(`Sent ${command}`);
        await refreshDashboard();
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

function prefillReply(chatId) {
  state.nav?.showView("inbox");
  for (const id of ["chat-id", "chat-id-tools"]) {
    const field = document.getElementById(id);
    if (field) field.value = chatId;
  }
  document.getElementById("message-text")?.focus();
  document.querySelector(".compose-bar")?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  showToast(`Chat ID ${chatId} ready for reply.`);
}

async function submitSend(chatId, text, clearFields = []) {
  await api.sendMessage(chatId, text);
  clearFields.forEach((id) => {
    const el = document.getElementById(id);
    if (el) el.value = "";
  });
  showToast("Message sent.");
  await refreshDashboard();
}

async function refreshDashboard() {
  const [metrics, users, inbox, events, analytics, quickActions, botStatus] =
    await Promise.all([
      api.getMetrics(),
      api.getUsers(),
      loadWorkflowSettings(),
      loadInbox(),
      api.getEvents(),
      api.getAnalytics(),
      api.getQuickActions(),
      api.getBotStatus(),
    ]);

  renderMetrics(metrics);
  renderUserFilter(users);
  renderEvents(events);
  renderCommandChart(document.getElementById("command-chart"), analytics);
  renderQuickActions(quickActions);

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
    refreshDashboard().catch((error) => showToast(error.message));
  });

  document.getElementById("send-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const chatId = document.getElementById("chat-id").value.trim();
    const text = document.getElementById("message-text").value.trim();
    try {
      await submitSend(chatId, text, ["message-text"]);
      const toolsMsg = document.getElementById("message-text-tools");
      if (toolsMsg) toolsMsg.value = "";
      document.getElementById("chat-id-tools").value = chatId;
    } catch (error) {
      showToast(error.message);
    }
  });

  document.getElementById("send-form-tools")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const chatId = document.getElementById("chat-id-tools").value.trim();
    const text = document.getElementById("message-text-tools").value.trim();
    try {
      await submitSend(chatId, text, ["message-text-tools"]);
      document.getElementById("chat-id").value = chatId;
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
      await refreshDashboard();
    } catch (error) {
      showToast(error.message);
    }
  });
}

function handleRealtime(message) {
  const { event, data } = message;
  if (event === "snapshot") {
    renderMetrics(data.metrics);
    renderEvents(data.events);
    renderQuickActions(data.quick_actions);
    renderCommandChart(document.getElementById("command-chart"), data.analytics);
    return;
  }

  if (event === "telegram_update" || event === "message_sent") {
    refreshDashboard().catch(() => {});
  }

  if (
    event === "reply_mode_updated" ||
    event === "chat_reply_updated" ||
    event === "chat_relationship_updated"
  ) {
    loadWorkflowSettings().catch(() => {});
  }

  if (event === "quick_actions_updated") {
    renderQuickActions(data.actions);
  }
}

async function init() {
  const authed = await ensureAuthenticated();
  if (!authed) return;

  initTheme();
  state.nav = initNavigation();
  bindForms();
  bindInbox(prefillReply, (error) => showToast(error.message));
  bindWorkflow((message) => showToast(message), (error) => showToast(error));
  bindInsights(
    (error) => showToast(error),
    (message) => showToast(message || "Suggestion updated.")
  );

  try {
    await refreshDashboard();
  } catch (error) {
    showToast(error.message);
  }

  connectWebSocket(handleRealtime);
}

init();
