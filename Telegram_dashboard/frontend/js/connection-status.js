/** Shared bot + user account connection state for inbox empty states and send UI. */

export const connectionState = {
  botStatus: null,
  userAccountStatus: null,
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function setConnectionStatus(botStatus, userAccountStatus) {
  connectionState.botStatus = botStatus || null;
  connectionState.userAccountStatus = userAccountStatus || null;
}

export function hasActiveInboxFilters(filters = {}) {
  return Boolean(
    filters.q ||
      filters.topics ||
      filters.userIds?.length ||
      filters.chatType ||
      filters.direction ||
      filters.ingestionSource ||
      filters.dateFrom ||
      filters.dateTo
  );
}

function buildBotStatusLine(botStatus = connectionState.botStatus) {
  if (botStatus?.configured && botStatus?.bot) {
    return `Bot v0.1: @${botStatus.bot.username} — receiving`;
  }
  if (botStatus?.configured) {
    return "Bot v0.1: token set — check token & webhook";
  }
  return "Bot v0.1: not configured — set TELEGRAM_BOT_TOKEN";
}

function buildUserStatusLine(userAccountStatus = connectionState.userAccountStatus) {
  if (userAccountStatus?.listening) {
    return `My account v0.2: @${userAccountStatus.user?.username || "connected"} — receiving`;
  }
  if (userAccountStatus?.authorized) {
    return "My account v0.2: logged in — set MTProto_ENABLED=true & restart";
  }
  if (userAccountStatus?.configured) {
    return "My account v0.2: not logged in — run scripts/mtproto_login.py";
  }
  return "My account v0.2: set TELEGRAM_API_ID + TELEGRAM_API_HASH";
}

function isBotReceiving(botStatus = connectionState.botStatus) {
  return Boolean(botStatus?.configured && botStatus?.bot);
}

function isUserReceiving(userAccountStatus = connectionState.userAccountStatus) {
  return Boolean(userAccountStatus?.listening);
}

export function buildInboxEmptyHtml({ filters = {}, view = "threads", topicHint = "" } = {}) {
  if (hasActiveInboxFilters(filters)) {
    const label = view === "flat" ? "messages" : "conversations";
    return `<div class="empty-thread">
      <p class="empty-thread-title">No ${label} match your filters</p>
      <p class="empty-thread-reason">Try clearing filters or broadening your search.${topicHint}</p>
      <p class="empty-thread-action">Use <strong>Clear filters</strong> or adjust the search box.</p>
    </div>`;
  }

  const botStatus = connectionState.botStatus;
  const userStatus = connectionState.userAccountStatus;
  const steps = [];
  let reason = "No messages have been captured yet.";

  const botReceiving = isBotReceiving(botStatus);
  const userReceiving = isUserReceiving(userStatus);

  if (!botStatus?.configured && !userStatus?.configured) {
    reason = "Neither the bot nor your personal account is configured yet.";
  } else if (!botReceiving && !userReceiving) {
    reason = "Connections are not receiving messages yet.";
  }

  if (!botStatus?.configured) {
    steps.push("Set TELEGRAM_BOT_TOKEN in .env, register the webhook, then restart the server.");
  } else if (!botStatus?.bot) {
    steps.push("Bot token is set but not verified — check TELEGRAM_BOT_TOKEN and restart.");
  } else if (!botReceiving) {
    steps.push("Message your bot in Telegram or add it to a group to generate bot traffic.");
  }

  if (!userStatus?.configured) {
    steps.push(
      "Optional: add TELEGRAM_API_ID and TELEGRAM_API_HASH from my.telegram.org for your personal inbox."
    );
  } else if (!userStatus?.authorized) {
    steps.push("Run scripts/mtproto_login.py once to log in to your Telegram account.");
  } else if (!userStatus?.listening) {
    steps.push("Set MTProto_ENABLED=true in .env and restart the server to capture your chats.");
  }

  if (steps.length === 0) {
    steps.push("Send a test message in Telegram, then click Refresh.");
  }

  const stepsHtml = `<ul class="empty-thread-steps">${steps
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join("")}</ul>`;

  return `<div class="empty-thread empty-thread-setup">
    <p class="empty-thread-title">Inbox is empty</p>
    <p class="empty-thread-reason">${escapeHtml(reason)}</p>
    ${stepsHtml}
  </div>`;
}

export function renderTopbarStatus() {
  const statusEl = document.getElementById("bot-status");
  if (statusEl) {
    statusEl.textContent = `${buildBotStatusLine()} · ${buildUserStatusLine()}`;
  }

  const userStatusEl = document.getElementById("user-account-status");
  if (userStatusEl) {
    userStatusEl.textContent = buildUserStatusLine();
  }
}

export function updateSendFormAvailability() {
  const botStatus = connectionState.botStatus;
  const userStatus = connectionState.userAccountStatus;
  const botReady = Boolean(botStatus?.configured);
  const userReady = Boolean(userStatus?.authorized);

  const composeBtn = document.querySelector("#send-form button[type='submit']");
  const composeHint = document.getElementById("compose-send-hint");
  if (composeBtn) {
    composeBtn.textContent = "Send via bot (v0.1)";
    composeBtn.disabled = !botReady;
    composeBtn.title = botReady
      ? "Recipients see your bot identity, not your personal account"
      : "Set TELEGRAM_BOT_TOKEN in .env first";
  }
  if (composeHint) {
    composeHint.textContent = botReady
      ? "Sends as your bot — not your personal Telegram name."
      : "Bot not configured. Set TELEGRAM_BOT_TOKEN in .env to enable sending.";
  }

  const toolsBtn = document.querySelector("#send-form-tools button[type='submit']");
  const toolsHint = document.getElementById("send-tools-hint");
  if (toolsBtn) {
    toolsBtn.disabled = !botReady;
    toolsBtn.title = botReady ? "Sends via bot API (v0.1)" : "Set TELEGRAM_BOT_TOKEN first";
  }
  if (toolsHint) {
    toolsHint.textContent = botReady
      ? "Bot send — message appears from @your_bot, not from you personally."
      : "Configure TELEGRAM_BOT_TOKEN before sending via bot.";
  }

  const userBtn = document.querySelector("#send-form-user button[type='submit']");
  const userHint = document.getElementById("send-user-hint");
  if (userBtn) {
    userBtn.disabled = !userReady;
    userBtn.title = userReady
      ? "Sends from your logged-in Telegram account (v0.2)"
      : "Run scripts/mtproto_login.py to enable Send as me";
  }
  if (userHint) {
    userHint.textContent = userReady
      ? "Personal send — recipients see your account, not the bot."
      : "Not logged in. Run scripts/mtproto_login.py once, then restart if needed.";
  }
}
