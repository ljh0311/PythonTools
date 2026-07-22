import { api } from "./api.js";

let composeRecipients = [];

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function getComposeRecipients() {
  return composeRecipients;
}

export function renderComposeRecipients(recipients = []) {
  composeRecipients = Array.isArray(recipients) ? recipients : [];
  const datalist = document.getElementById("chat-recipient-list");
  if (!datalist) return;

  datalist.innerHTML = composeRecipients
    .map(
      (item) =>
        `<option value="${escapeHtml(item.label)}">${escapeHtml(item.label)} · ${item.chat_id}</option>`
    )
    .join("");
}

export function resolveChatTarget(input) {
  const raw = (input || "").trim();
  if (!raw) return null;

  if (/^-?\d+$/.test(raw)) return raw;

  const needle = raw.startsWith("@") ? raw.slice(1).toLowerCase() : raw.toLowerCase();

  for (const item of composeRecipients) {
    if (item.handle && item.handle.toLowerCase() === needle) {
      return String(item.chat_id);
    }
    const label = item.label || "";
    if (label.toLowerCase() === raw.toLowerCase()) {
      return String(item.chat_id);
    }
    if (label.startsWith("@") && label.slice(1).toLowerCase() === needle) {
      return String(item.chat_id);
    }
  }

  if (raw.startsWith("@")) {
    return raw;
  }

  return raw;
}

export function labelForChatId(chatId) {
  const match = composeRecipients.find((item) => String(item.chat_id) === String(chatId));
  return match?.label || String(chatId);
}

export function setComposeTarget(
  chatId,
  fieldIds = ["chat-id", "chat-id-tools", "chat-id-user", "dev-notify-chat-id"]
) {
  const display = labelForChatId(chatId);
  for (const id of fieldIds) {
    const field = document.getElementById(id);
    if (field) field.value = display;
  }
}

export async function loadComposeRecipients() {
  const recipients = await api.getComposeRecipients();
  renderComposeRecipients(recipients);
  return recipients;
}

export function readComposeTarget(fieldId = "chat-id") {
  const field = document.getElementById(fieldId);
  if (!field) return null;
  return resolveChatTarget(field.value);
}
