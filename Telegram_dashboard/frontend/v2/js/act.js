import { api } from "./api.js";
import {
  asList,
  escapeHtml,
  formatCompactTime,
  formatTime,
  showToast,
  suggestionFields,
} from "./utils.js";

const state = {
  items: [],
  loading: false,
  refreshing: false,
  loadError: null,
  sendAvailable: false,
  sendUnavailableReason: "",
  needsReplyCount: 0,
  quality: null,
};

const TRIAGE_HINTS = {
  pending: "Needs attention",
  done: "Handled offline — no send needed",
  dismissed: "Not actionable",
  sent: "Sent from Act",
};

function root() {
  return document.getElementById("view-act");
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="act-workspace">
      <p class="view-hint">
        Needs-reply queue (truthful last-message state). Open chat or send a draft —
        not an AI dump. <strong>Mark done</strong> = handled offline ·
        <strong>Dismiss</strong> = not actionable · <strong>Reopen</strong> = undo.
      </p>
      <div class="digest-bar" id="digest-bar">
        <div class="digest-bar-copy">
          <strong>Needs-reply digest</strong>
          <span class="digest-bar-sub" id="digest-status-sub">Telegram summary of waiting threads</span>
        </div>
        <label class="digest-toggle">
          <input type="checkbox" id="digest-enabled" />
          <span>Scheduled</span>
        </label>
        <button type="button" class="btn btn-ghost" id="digest-send-now">Send digest now</button>
      </div>
      <div class="panel" style="height:100%">
        <div class="panel-header">
          <div>
            <h2>Action queue</h2>
            <p class="panel-sub" id="act-provider-sub">What must you do today?</p>
          </div>
          <div class="panel-actions">
            <button type="button" class="btn btn-ghost" id="act-reload">Reload</button>
            <button type="button" class="btn btn-primary" id="act-refresh-ai">Refresh AI</button>
          </div>
        </div>
        <div class="panel-body" id="act-list"></div>
      </div>
    </div>
  `;

  el.querySelector("#act-reload").addEventListener("click", () => loadAct());
  el.querySelector("#act-refresh-ai").addEventListener("click", () => refreshAi());
  el.querySelector("#digest-enabled").addEventListener("change", (event) => {
    toggleDigest(event.target.checked);
  });
  el.querySelector("#digest-send-now").addEventListener("click", () => sendDigestNow());
}

function replyStateLabel(f) {
  if (f.status === "sent" || f.replyState === "sent") return "Sent";
  if (f.alreadyReplied || f.replyState === "already_replied") return "Already replied";
  if (f.needsReply || f.replyState === "needs_reply") return "Needs reply";
  return TRIAGE_HINTS[f.status] || f.status;
}

function replyStateClass(f) {
  if (f.status === "sent" || f.replyState === "sent") return "is-sent";
  if (f.alreadyReplied || f.replyState === "already_replied") return "is-already-replied";
  if (f.needsReply || f.replyState === "needs_reply") return "is-needs-reply";
  return "";
}

function isPlaceholderPeerLabel(value) {
  const text = String(value || "").trim();
  if (!text) return true;
  const lowered = text.toLowerCase();
  if (lowered.startsWith("chat ") || lowered.startsWith("chat-")) {
    const rest = text.includes(" ") ? text.split(/\s+/, 2)[1] : text.slice(4);
    return /^-?\d+$/.test(String(rest || "").trim());
  }
  return false;
}

function displayWho(f) {
  const candidates = [f.displayTitle, f.chatTitle, f.user];
  for (const raw of candidates) {
    const named = String(raw || "").trim();
    if (named && !isPlaceholderPeerLabel(named)) return named;
  }
  if (f.chatId != null) return `Chat ${f.chatId}`;
  return "Contact";
}

function displayWhoSub(f) {
  const title = displayWho(f);
  const user = String(f.user || "").trim();
  const isGroup = f.chatType === "group" || f.chatType === "channel";
  if (isGroup && user && !isPlaceholderPeerLabel(user) && user !== title) {
    return `Last from @${user.replace(/^@/, "")}`;
  }
  return "";
}

function whenLabel(f) {
  const raw = f.lastInboundAt || f.createdAt || f.lastOutboundAt || "";
  return raw ? formatCompactTime(raw) : "";
}

function whenFull(f) {
  const raw = f.lastInboundAt || f.createdAt || f.lastOutboundAt || "";
  return raw ? formatTime(raw) : "";
}

function metaBadgesHtml(f) {
  const badges = [];
  const needs = f.needsReply || f.replyState === "needs_reply";
  const already =
    f.status === "sent" ||
    f.alreadyReplied ||
    f.replyState === "already_replied";

  if (needs) {
    badges.push(
      `<span class="badge badge-reply-state badge-emphasis">Needs reply</span>`,
    );
  } else if (already) {
    badges.push(
      `<span class="badge badge-reply-state">${escapeHtml(replyStateLabel(f))}</span>`,
    );
  } else if (f.status && f.status !== "pending") {
    badges.push(
      `<span class="badge badge-status-${escapeHtml(f.status)}" title="${escapeHtml(TRIAGE_HINTS[f.status] || "")}">${escapeHtml(f.status)}</span>`,
    );
  }

  if (f.priority === "high") {
    badges.push(
      `<span class="badge badge-priority-high" title="Priority">High</span>`,
    );
  } else if (f.priority === "low") {
    badges.push(
      `<span class="badge badge-priority-low" title="Priority">Low</span>`,
    );
  }

  if (f.dueHint) {
    badges.push(`<span class="badge badge-due">Due ${escapeHtml(f.dueHint)}</span>`);
  }

  if (f.type && f.type !== "reply" && f.type !== "next_action") {
    badges.push(`<span class="badge">${escapeHtml(f.type)}</span>`);
  }

  return badges.join("");
}

function cardBodyHtml(f) {
  const already =
    f.status === "sent" ||
    f.alreadyReplied ||
    f.replyState === "already_replied" ||
    f.draftSuppressed;
  const needs = f.needsReply || f.replyState === "needs_reply";

  if (already && !needs) {
    const preview = f.lastOutboundText || "(no outbound preview)";
    return `
      <p class="act-preview"><span class="act-preview-label">Last outbound</span>${escapeHtml(preview)}</p>
      ${f.action ? `<p class="list-meta">${escapeHtml(f.action)}</p>` : ""}
    `;
  }

  if (f.type === "reply" || needs) {
    const draft = (f.displayDraft || f.draft || "").trim();
    const showAiUnavailable = f.aiUnavailable && needs;
    return `
      ${showAiUnavailable ? `<p class="act-reply-banner is-warn">AI unavailable — reply manually or use outline draft</p>` : ""}
      ${f.lastInboundText ? `<p class="act-preview"><span class="act-preview-label">They said</span>${escapeHtml(f.lastInboundText)}</p>` : ""}
      ${draft
        ? `<div class="act-draft-block"><span class="act-preview-label">Your draft</span><pre class="act-draft">${escapeHtml(draft)}</pre></div>`
        : `<p class="act-draft-empty">No draft yet — open the chat to reply, or refresh AI.</p>`}
      ${f.action ? `<p class="list-meta">${escapeHtml(f.action)}</p>` : ""}
    `;
  }

  return `
    <p class="act-body">${escapeHtml(f.action || f.draft || "(no details)")}</p>
  `;
}

function canSend(f) {
  if (f.status !== "pending") return false;
  if (f.chatId == null) return false;
  if (String(f.id || "").startsWith("open-")) return false;
  if (f.alreadyReplied || f.replyState === "already_replied") return false;
  if (f.draftSuppressed) return false;
  const draft = (f.displayDraft || f.draft || "").trim();
  return Boolean(draft);
}

function actionsHtml(f, sendOk, sendDisabled, sendTitle) {
  const isOpenStub = String(f.id || "").startsWith("open-");
  const openChat =
    f.chatId != null
      ? `<a class="btn ${sendOk && state.sendAvailable ? "btn-ghost" : "btn-primary"}" data-open-chat href="/v2#talk?chat=${encodeURIComponent(f.chatId)}">Open chat</a>`
      : "";

  const sendBtn = sendOk
    ? `<button type="button" class="btn btn-primary" data-send ${sendDisabled ? "disabled" : ""} title="${escapeHtml(sendTitle)}">Send draft</button>`
    : "";

  const secondary = [];
  if (f.status !== "pending" && !isOpenStub) {
    secondary.push(
      `<button type="button" class="btn btn-ghost" data-status="pending" title="Undo done/dismiss/sent">Reopen</button>`,
    );
  }
  if (f.status !== "done" && !isOpenStub) {
    secondary.push(
      `<button type="button" class="btn btn-ghost" data-status="done" title="${escapeHtml(TRIAGE_HINTS.done)}">Mark done</button>`,
    );
  }
  if (f.status !== "dismissed" && !isOpenStub) {
    secondary.push(
      `<button type="button" class="btn btn-ghost btn-danger" data-status="dismissed" title="${escapeHtml(TRIAGE_HINTS.dismissed)}">Dismiss</button>`,
    );
  }

  return `
    <div class="act-actions">
      <div class="act-actions-primary">
        ${openChat}
        ${sendBtn}
      </div>
      ${secondary.length ? `<div class="act-actions-secondary">${secondary.join("")}</div>` : ""}
    </div>
  `;
}

function updateSubtitle(extra = "") {
  const sub = document.getElementById("act-provider-sub");
  if (!sub) return;
  const n = state.needsReplyCount;
  const q = state.quality;
  let line = n === 1 ? "1 chat needs a reply" : `${n} chats need a reply`;
  if (q && (q.false_needs_reply_count || q.missing_dues_count)) {
    line += ` · quality: ${q.false_needs_reply_count || 0} false needs, ${q.missing_dues_count || 0} gaps filled`;
  }
  if (extra) line = `${extra} · ${line}`;
  sub.textContent = line;
}

function renderList() {
  const list = document.getElementById("act-list");
  if (!list) return;

  if (state.loading) {
    list.innerHTML = `<p class="loading-state">Loading actions…</p>`;
    return;
  }

  if (state.loadError) {
    list.innerHTML = `<p class="error-state">${escapeHtml(state.loadError)}</p>`;
    return;
  }

  if (!state.items.length) {
    list.innerHTML = `
      <div class="empty-card">
        <p class="empty-state">Nothing needs you right now.</p>
        <p class="empty-detail">Refresh AI rebuilds drafts for unanswered personal chats only.</p>
      </div>`;
    return;
  }

  list.innerHTML = state.items
    .map((item) => {
      const f = suggestionFields(item);
      const statusClass = ["done", "dismissed", "sent"].includes(f.status)
        ? `is-${f.status}`
        : "";
      const replyClass = replyStateClass(f);
      const sendOk = canSend(f);
      const sendDisabled = !sendOk || !state.sendAvailable;
      const when = whenLabel(f);
      const whenTitle = whenFull(f);
      const who = displayWho(f);
      const whoSub = displayWhoSub(f);
      const needs = f.needsReply || f.replyState === "needs_reply";
      let sendTitle = "";
      if (!sendOk) {
        sendTitle = f.alreadyReplied
          ? "Already replied in chat history"
          : String(f.id || "").startsWith("open-")
            ? "Open chat to reply (no saved draft)"
            : "No draft to send";
      } else if (!state.sendAvailable) {
        sendTitle = state.sendUnavailableReason || "Personal account send unavailable";
      } else {
        sendTitle = "Send draft as your Telegram user account";
      }

      return `
        <article class="act-card ${statusClass} ${replyClass}" data-id="${escapeHtml(String(f.id))}">
          <header class="act-card-head">
            <div class="act-card-title-row">
              ${needs ? `<img class="act-needs-icon" src="/static/assets/icons/icon-needs-reply.svg" width="18" height="18" alt="" />` : ""}
              <div class="act-who-block">
                <h3 class="act-who" title="${escapeHtml(f.chatId != null ? `chat ${f.chatId}` : who)}">${escapeHtml(who)}</h3>
                ${whoSub ? `<p class="act-who-sub">${escapeHtml(whoSub)}</p>` : ""}
              </div>
              ${when ? `<time class="act-when" datetime="${escapeHtml(f.lastInboundAt || f.createdAt || "")}" title="${escapeHtml(whenTitle)}">${escapeHtml(when)}</time>` : ""}
            </div>
            <div class="act-meta">${metaBadgesHtml(f)}</div>
          </header>
          ${cardBodyHtml(f)}
          ${actionsHtml(f, sendOk, sendDisabled, sendTitle)}
          ${!state.sendAvailable && sendOk
            ? `<p class="list-meta act-send-reason">${escapeHtml(state.sendUnavailableReason || "Send disabled")}</p>`
            : ""}
        </article>
      `;
    })
    .join("");

  list.querySelectorAll(".act-card").forEach((card) => {
    card.querySelectorAll("[data-status]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = card.getAttribute("data-id");
        const status = btn.getAttribute("data-status");
        await patchStatus(id, status);
      });
    });
    card.querySelector("[data-send]")?.addEventListener("click", async () => {
      const id = card.getAttribute("data-id");
      await sendDraft(id);
    });
    card.querySelector("[data-open-chat]")?.addEventListener("click", (event) => {
      const href = event.currentTarget.getAttribute("href") || "";
      const match = href.match(/chat=([^&]+)/);
      if (match) {
        sessionStorage.setItem("v2-talk-chat", decodeURIComponent(match[1]));
      }
    });
  });
}

function applyQueueMeta(data) {
  if (!data || typeof data !== "object") return;
  state.sendAvailable = Boolean(data.send_available);
  state.sendUnavailableReason = data.send_unavailable_reason || "";
  state.needsReplyCount = Number(data.needs_reply_count || 0);
  state.quality = data.quality || null;
}

async function loadAct() {
  state.loading = true;
  state.loadError = null;
  renderList();
  try {
    const data = await api.getAct();
    applyQueueMeta(data);
    state.items = asList(data, ["items", "suggestions", "actions"]);
    updateSubtitle();
  } catch (err) {
    state.loadError = err.message || "Failed to load act queue";
    showToast(state.loadError, { error: true });
  } finally {
    state.loading = false;
    renderList();
  }
}

async function refreshAi() {
  const btn = document.getElementById("act-refresh-ai");
  if (btn) btn.disabled = true;
  state.refreshing = true;
  try {
    const data = await api.refreshAct();
    applyQueueMeta(data);
    const refreshed = asList(data, ["items", "suggestions", "actions"]);
    if (refreshed.length) {
      state.items = refreshed;
      renderList();
    } else {
      await loadAct();
    }
    const provider = data?.provider || "unknown";
    updateSubtitle(
      data?.degraded
        ? `Using ${provider} (degraded)`
        : `Provider: ${provider}`,
    );
    showToast(
      data?.degraded
        ? `Queue refreshed via ${provider} (fallback drafts)`
        : `Action queue refreshed (${provider})`,
    );
  } catch (err) {
    showToast(err.message || "AI refresh failed", { error: true });
  } finally {
    state.refreshing = false;
    if (btn) btn.disabled = false;
  }
}

async function patchStatus(id, status) {
  try {
    const updated = await api.patchAct(id, status);
    const idx = state.items.findIndex((item) => String(item.id) === String(id));
    if (idx >= 0) {
      state.items[idx] = { ...state.items[idx], ...updated, status };
    }
    if (status === "dismissed") {
      state.items = state.items.filter((item) => String(item.id) !== String(id));
    }
    state.needsReplyCount = state.items.filter(
      (item) => item.needs_reply && (item.status || "pending") === "pending",
    ).length;
    updateSubtitle();
    renderList();
    const label =
      status === "done"
        ? "Marked done (handled offline)"
        : status === "dismissed"
          ? "Dismissed (not actionable)"
          : status === "pending"
            ? "Reopened"
            : `Marked ${status}`;
    showToast(label);
  } catch (err) {
    showToast(err.message || "Status update failed", { error: true });
  }
}

async function sendDraft(id) {
  try {
    const data = await api.sendActDraft(id);
    const updated = data?.suggestion || data;
    const idx = state.items.findIndex((item) => String(item.id) === String(id));
    if (idx >= 0 && updated) {
      state.items[idx] = { ...state.items[idx], ...updated, status: "sent" };
    }
    renderList();
    showToast("Draft sent — marked sent");
  } catch (err) {
    showToast(err.message || "Send failed", { error: true });
  }
}

function applyDigestStatus(data) {
  const toggle = document.getElementById("digest-enabled");
  const sub = document.getElementById("digest-status-sub");
  if (toggle) toggle.checked = Boolean(data?.enabled);
  if (!sub) return;
  const parts = [];
  if (!data?.chat_id_configured) parts.push("set UNREAD_DIGEST_CHAT_ID");
  else if (!data?.bot_configured) parts.push("bot token missing");
  else if (data?.in_quiet_hours) parts.push("quiet hours");
  else if (data?.enabled) parts.push(`every ${data.interval_min || 180}m`);
  else parts.push("off — enable for schedule");
  if (data?.last_sent_at) parts.push(`last ${formatTime(data.last_sent_at)}`);
  sub.textContent = parts.join(" · ");
}

async function loadDigestStatus() {
  try {
    const data = await api.getDigest();
    applyDigestStatus(data);
  } catch {
    const sub = document.getElementById("digest-status-sub");
    if (sub) sub.textContent = "Digest status unavailable";
  }
}

async function toggleDigest(enabled) {
  try {
    const data = await api.setDigestEnabled(enabled);
    applyDigestStatus(data);
    showToast(enabled ? "Digest schedule on" : "Digest schedule off");
  } catch (err) {
    const toggle = document.getElementById("digest-enabled");
    if (toggle) toggle.checked = !enabled;
    showToast(err.message || "Failed to update digest", { error: true });
  }
}

async function sendDigestNow() {
  const btn = document.getElementById("digest-send-now");
  if (btn) btn.disabled = true;
  try {
    const data = await api.sendDigestNow();
    applyDigestStatus(data);
    const result = data?.result || {};
    if (result.sent) {
      showToast(
        `Digest sent (${result.provider || "ok"}, ${result.open_items_count || 0} threads)`,
      );
    } else {
      const reason = result.reason || "not sent";
      showToast(`Digest not sent: ${reason}`, { error: reason !== "empty" });
    }
  } catch (err) {
    showToast(err.message || "Digest send failed", { error: true });
  } finally {
    if (btn) btn.disabled = false;
  }
}

export async function mountAct() {
  renderShell();
  await Promise.all([loadAct(), loadDigestStatus()]);
}

export function refreshActIfVisible() {
  const el = root();
  if (el?.classList.contains("is-visible")) {
    return loadAct();
  }
  return Promise.resolve();
}
