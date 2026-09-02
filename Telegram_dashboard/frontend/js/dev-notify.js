import { api } from "./api.js";
import { readComposeTarget } from "./compose.js";

const TELEGRAM_MAX = 4096;

function eodHeaderLine() {
  const date = new Date().toISOString().slice(0, 10);
  return `# End of Day — ${date}\n\n`;
}

function buildMessage(textarea, useEodHeader) {
  const raw = (textarea?.value || "").trim();
  if (!useEodHeader) return raw;
  return raw ? eodHeaderLine() + raw : eodHeaderLine().trimEnd();
}

function truncateForTelegram(text) {
  if (text.length <= TELEGRAM_MAX) return text;
  const note = "\n\n…truncated for Telegram (full content on disk).";
  return text.slice(0, TELEGRAM_MAX - note.length).trimEnd() + note;
}

export function bindDevNotify(showToast, refreshDashboard) {
  const form = document.getElementById("dev-notify-form");
  const textarea = document.getElementById("dev-notify-text");
  const charCount = document.getElementById("dev-notify-char-count");
  const fileInput = document.getElementById("dev-notify-file");
  const loadBtn = document.getElementById("dev-notify-load-file");
  const eodHeader = document.getElementById("dev-notify-eod-header");

  function updateCharCount() {
    if (!charCount) return;
    const len = buildMessage(textarea, eodHeader?.checked).length;
    charCount.textContent = `${len} / ${TELEGRAM_MAX}`;
    charCount.classList.toggle("dev-notify-over-limit", len > TELEGRAM_MAX);
  }

  textarea?.addEventListener("input", updateCharCount);
  eodHeader?.addEventListener("change", updateCharCount);

  loadBtn?.addEventListener("click", () => fileInput?.click());

  fileInput?.addEventListener("change", async () => {
    const file = fileInput.files?.[0];
    if (!file) return;
    try {
      textarea.value = await file.text();
      updateCharCount();
      showToast(`Loaded ${file.name}`);
    } catch {
      showToast("Could not read file.");
    }
    fileInput.value = "";
  });

  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const chatId = readComposeTarget("dev-notify-chat-id");
    if (!chatId) {
      showToast("Pick @username or a chat from the list.");
      return;
    }

    let text = buildMessage(textarea, eodHeader?.checked);
    if (!text) {
      showToast("Enter or load message text.");
      return;
    }

    text = truncateForTelegram(text);

    try {
      await api.sendMessage(chatId, text);
      showToast("Dev notify sent via bot.");
      await refreshDashboard?.();
    } catch (error) {
      showToast(error.message);
    }
  });

  updateCharCount();
}
