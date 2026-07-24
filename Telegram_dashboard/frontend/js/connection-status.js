/** Shared bot + user account connection state for inbox empty states and send UI. */

export const connectionState = {
  botStatus: null,
  userAccountStatus: null,
};

export const SETUP_WARNINGS_DISMISS_KEY = "setup-warnings-dismissed";

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

function isBotReceiving(botStatus = connectionState.botStatus) {
  return Boolean(botStatus?.configured && botStatus?.bot);
}

function isUserReceiving(userAccountStatus = connectionState.userAccountStatus) {
  return Boolean(userAccountStatus?.listening);
}

export function getBotPill(botStatus = connectionState.botStatus) {
  if (!botStatus) {
    return { state: "loading", label: "Bot", text: "Checking…", title: "Bot: checking connection" };
  }
  if (isBotReceiving(botStatus)) {
    const handle = botStatus.bot?.username ? `@${botStatus.bot.username}` : "";
    const text = handle ? `Connected ${handle}` : "Connected";
    return { state: "connected", label: "Bot", text, title: `Bot: ${text}` };
  }
  if (botStatus.configured) {
    return {
      state: "needs-setup",
      label: "Bot",
      text: "Needs setup",
      title: "Bot: token set but not verified — check TELEGRAM_BOT_TOKEN",
    };
  }
  return {
    state: "offline",
    label: "Bot",
    text: "Offline",
    title: "Bot: not configured — set TELEGRAM_BOT_TOKEN",
  };
}

export function getUserPill(userAccountStatus = connectionState.userAccountStatus) {
  if (!userAccountStatus) {
    return {
      state: "loading",
      label: "My account",
      text: "Checking…",
      title: "My account: checking connection",
    };
  }
  if (isUserReceiving(userAccountStatus)) {
    const handle = userAccountStatus.user?.username
      ? `@${userAccountStatus.user.username}`
      : "";
    const text = handle ? `Connected ${handle}` : "Connected";
    return { state: "connected", label: "My account", text, title: `My account: ${text}` };
  }
  if (userAccountStatus.authorized) {
    return {
      state: "needs-setup",
      label: "My account",
      text: "Needs setup",
      title: "My account: logged in — set MTProto_ENABLED=true and restart",
    };
  }
  if (userAccountStatus.configured) {
    return {
      state: "needs-setup",
      label: "My account",
      text: "Needs setup",
      title: "My account: run scripts/mtproto_login.py to log in",
    };
  }
  return {
    state: "offline",
    label: "My account",
    text: "Offline",
    title: "My account: optional — set TELEGRAM_API_ID and TELEGRAM_API_HASH",
  };
}

function renderStatusPill(pill) {
  const modifier = pill.state === "loading" ? "loading" : pill.state;
  return `<span class="status-pill status-pill--${modifier}" title="${escapeHtml(pill.title)}">
    <span class="status-pill-label">${escapeHtml(pill.label)}</span>
    <span class="status-pill-state">${escapeHtml(pill.text)}</span>
  </span>`;
}

function buildUserStatusLine(userAccountStatus = connectionState.userAccountStatus) {
  const pill = getUserPill(userAccountStatus);
  if (pill.state === "connected") {
    return userAccountStatus?.user?.username
      ? `Logged in as @${userAccountStatus.user.username} — receiving`
      : "Logged in — receiving";
  }
  if (pill.state === "needs-setup") {
    if (userAccountStatus?.authorized) {
      return "Logged in — enable MTProto (MTProto_ENABLED=true) and restart";
    }
    if (userAccountStatus?.configured) {
      return "Not logged in — run scripts/mtproto_login.py";
    }
    return "Needs setup — see Tools for credentials";
  }
  return "Optional — not configured";
}

function buildSetupConnectSteps(botStatus, userStatus) {
  const steps = [];
  const botReceiving = isBotReceiving(botStatus);
  const userReceiving = isUserReceiving(userStatus);

  if (!botStatus?.configured) {
    steps.push("Bot: add TELEGRAM_BOT_TOKEN to .env, register the webhook, then restart.");
  } else if (!botStatus?.bot) {
    steps.push("Bot: token is set but not verified — check TELEGRAM_BOT_TOKEN and restart.");
  } else if (!botReceiving) {
    steps.push("Bot: message your bot in Telegram or add it to a group.");
  }

  if (!userStatus?.configured) {
    steps.push(
      "My Telegram account (optional): add TELEGRAM_API_ID and TELEGRAM_API_HASH from my.telegram.org."
    );
  } else if (!userStatus?.authorized) {
    steps.push("My Telegram account: run scripts/mtproto_login.py once to log in.");
  } else if (!userReceiving) {
    steps.push("My Telegram account: set MTProto_ENABLED=true in .env and restart.");
  }

  if (steps.length === 0) {
    steps.push("Send a test message in Telegram, then click Refresh.");
  }

  return steps;
}

export function buildInboxEmptyHtml({ filters = {}, view = "threads", topicHint = "" } = {}) {
  if (hasActiveInboxFilters(filters)) {
    const label = view === "flat" ? "messages" : "conversations";
    return `<div class="empty-thread">
      <p class="empty-thread-title">No ${label} match your filters</p>
      <p class="empty-thread-reason">Try clearing filters or broadening your search.${topicHint}</p>
      <div class="empty-thread-actions">
        <button type="button" class="btn btn-primary btn-sm" data-empty-action="clear-filters">Clear filters</button>
      </div>
    </div>`;
  }

  const botStatus = connectionState.botStatus;
  const userStatus = connectionState.userAccountStatus;
  const botReceiving = isBotReceiving(botStatus);
  const userReceiving = isUserReceiving(userStatus);

  let reason = "No messages captured yet.";
  if (!botStatus?.configured && !userStatus?.configured) {
    reason = "Connect your bot or personal Telegram account to start receiving messages.";
  } else if (!botReceiving && !userReceiving) {
    reason = "Your connections are set up but not receiving messages yet.";
  }

  const steps = buildSetupConnectSteps(botStatus, userStatus);
  const stepsHtml = `<ul class="empty-thread-steps">${steps
    .map((step) => `<li>${escapeHtml(step)}</li>`)
    .join("")}</ul>`;

  return `<div class="empty-thread empty-thread-setup">
    <p class="empty-thread-title">Inbox is empty</p>
    <p class="empty-thread-reason">${escapeHtml(reason)}</p>
    <div class="empty-thread-actions">
      <button type="button" class="btn btn-primary btn-sm" data-empty-action="open-tools">Open Tools</button>
      <button type="button" class="btn btn-ghost btn-sm" data-empty-action="refresh-inbox">Refresh</button>
      <button type="button" class="btn btn-ghost btn-sm" data-empty-action="toggle-connect-details" aria-expanded="false">How to connect</button>
    </div>
    <div class="empty-thread-details" hidden>
      ${stepsHtml}
    </div>
  </div>`;
}

export function renderTopbarStatus() {
  const container = document.getElementById("connection-status");
  if (container) {
    const botPill = getBotPill();
    const userPill = getUserPill();
    container.innerHTML = `${renderStatusPill(botPill)}${renderStatusPill(userPill)}`;
  }

  const userStatusEl = document.getElementById("user-account-status");
  if (userStatusEl) {
    userStatusEl.textContent = buildUserStatusLine();
  }
}

export function shortenSetupWarning(text) {
  const value = String(text || "").trim();
  const rules = [
    [/Telegram bot token not configured \(TELEGRAM_BOT_TOKEN\)/i, "Bot token missing — set TELEGRAM_BOT_TOKEN"],
    [/Bot token set but verification returned no bot profile/i, "Bot token not verified — check TELEGRAM_BOT_TOKEN"],
    [/Bot token invalid or unreachable: (.+)/i, "Bot token invalid — check TELEGRAM_BOT_TOKEN"],
    [
      /User account not configured \(TELEGRAM_API_ID \+ TELEGRAM_API_HASH\)/i,
      "Personal account not configured — set API ID/hash in .env",
    ],
    [/User account not logged in \(run scripts\/mtproto_login\.py\)/i, "Personal account not logged in — run mtproto_login.py"],
    [
      /User account logged in but not listening \(set MTProto_ENABLED=true and restart\)/i,
      "Personal account not listening — set MTProto_ENABLED=true",
    ],
    [
      /No AI provider available \(configure GEMINI_API_KEY or Ollama\)/i,
      "No AI provider — set GEMINI_API_KEY or start Ollama",
    ],
  ];
  for (const [pattern, replacement] of rules) {
    if (pattern.test(value)) {
      return typeof replacement === "function" ? replacement(value) : replacement;
    }
  }
  return value.length > 72 ? `${value.slice(0, 69)}…` : value;
}

export function renderSetupWarnings(warnings = []) {
  const banner = document.getElementById("setup-warnings");
  if (!banner) return;

  const list = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
  if (!list.length || sessionStorage.getItem(SETUP_WARNINGS_DISMISS_KEY) === "1") {
    banner.hidden = true;
    banner.innerHTML = "";
    return;
  }

  banner.hidden = false;
  banner.innerHTML = `
    <div class="setup-warnings-inner">
      <ul>${list.map((item) => `<li>${escapeHtml(shortenSetupWarning(item))}</li>`).join("")}</ul>
      <button type="button" class="setup-warnings-dismiss btn btn-ghost btn-sm" aria-label="Dismiss setup warnings for this session">
        Dismiss
      </button>
    </div>`;

  banner.querySelector(".setup-warnings-dismiss")?.addEventListener("click", () => {
    sessionStorage.setItem(SETUP_WARNINGS_DISMISS_KEY, "1");
    banner.hidden = true;
    banner.innerHTML = "";
  });
}

function updateComposeIdentityChip(botStatus, botReady) {
  const chip = document.getElementById("compose-identity-chip");
  if (!chip) return;

  chip.classList.remove("identity-chip-unavailable", "identity-chip-bot");
  if (!botReady) {
    chip.textContent = "Bot unavailable";
    chip.classList.add("identity-chip-unavailable");
    return;
  }

  const username = botStatus?.bot?.username;
  chip.textContent = username ? `Sending as: Bot @${username}` : "Sending as: Bot";
  chip.classList.add("identity-chip-bot");
}

export function updateSendFormAvailability() {
  const botStatus = connectionState.botStatus;
  const userStatus = connectionState.userAccountStatus;
  const botReady = Boolean(botStatus?.configured);
  const userReady = Boolean(userStatus?.authorized);
  const botUsername = botStatus?.bot?.username;

  const composeBtn = document.querySelector("#send-form button[type='submit']");
  const composeHint = document.getElementById("compose-send-hint");
  updateComposeIdentityChip(botStatus, botReady);
  if (composeBtn) {
    composeBtn.textContent = "Send";
    composeBtn.disabled = !botReady;
    composeBtn.setAttribute("aria-describedby", "compose-send-hint");
    composeBtn.removeAttribute("title");
  }
  if (composeHint) {
    composeHint.textContent = botReady
      ? botUsername
        ? `Sends as @${botUsername} — not your personal Telegram name.`
        : "Sends as your bot — not your personal Telegram name."
      : "Bot not configured. Set TELEGRAM_BOT_TOKEN in .env to enable sending.";
  }

  const toolsBtn = document.querySelector("#send-form-tools button[type='submit']");
  const toolsHint = document.getElementById("send-tools-hint");
  if (toolsBtn) {
    toolsBtn.textContent = "Send as bot";
    toolsBtn.disabled = !botReady;
    toolsBtn.setAttribute("aria-describedby", "send-tools-hint");
    toolsBtn.removeAttribute("title");
  }
  if (toolsHint) {
    toolsHint.textContent = botReady
      ? botUsername
        ? `Bot send — message appears from @${botUsername}, not from you personally.`
        : "Bot send — message appears from your bot, not from you personally."
      : "Configure TELEGRAM_BOT_TOKEN before sending via bot.";
  }

  const userBtn = document.querySelector("#send-form-user button[type='submit']");
  const userHint = document.getElementById("send-user-hint");
  const userUsername = userStatus?.user?.username;
  if (userBtn) {
    userBtn.disabled = !userReady;
    userBtn.setAttribute("aria-describedby", "send-user-hint");
    userBtn.removeAttribute("title");
  }
  if (userHint) {
    userHint.textContent = userReady
      ? userUsername
        ? `Personal send — recipients see @${userUsername}, not the bot.`
        : "Personal send — recipients see your account, not the bot."
      : "Not logged in. Run scripts/mtproto_login.py once, then restart if needed.";
  }
}
