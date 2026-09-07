export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

export function formatTime(iso) {
  if (!iso) return "";
  const raw = String(iso);
  const date = new Date(raw.endsWith("Z") || raw.includes("+") ? raw : `${raw}Z`);
  if (Number.isNaN(date.getTime())) return raw;
  return date.toLocaleString();
}

export function showToast(message, { error = false } = {}) {
  const el = document.getElementById("v2-toast");
  if (!el) return;
  el.textContent = message;
  el.hidden = false;
  el.classList.toggle("is-error", Boolean(error));
  clearTimeout(showToast._timer);
  showToast._timer = setTimeout(() => {
    el.hidden = true;
  }, 3200);
}

export function asList(payload, keys = ["items", "threads", "messages", "profiles", "suggestions"]) {
  if (Array.isArray(payload)) return payload;
  if (!payload || typeof payload !== "object") return [];
  for (const key of keys) {
    if (Array.isArray(payload[key])) return payload[key];
  }
  return [];
}

export function threadTitle(thread) {
  if (!thread) return "Chat";
  if (thread.chat_type === "group" || thread.chat_type === "channel") {
    return thread.chat_title || `Chat ${thread.chat_id}`;
  }
  if (thread.title || thread.name) return thread.title || thread.name;
  if (thread.chat_title) return thread.chat_title;
  const first = Array.isArray(thread.messages) ? thread.messages[0] : null;
  if (first?.username) return `@${first.username}`;
  if (first?.user_id != null) return `User ${first.user_id}`;
  return thread.chat_id != null ? `Chat ${thread.chat_id}` : "Chat";
}

export function suggestionFields(item) {
  const payload = item?.payload && typeof item.payload === "object" ? item.payload : {};
  return {
    id: item?.id ?? payload.id,
    status: item?.status || "pending",
    type: item?.type || payload.type || "next_action",
    priority: item?.priority || payload.priority || "medium",
    chatId: item?.chat_id ?? payload.chat_id,
    user: item?.user || payload.user || "",
    draft: item?.draft || payload.draft || "",
    action: item?.action || payload.action || "",
    dueHint: item?.due_hint || payload.due_hint || "",
    confidence: item?.confidence ?? payload.confidence,
    createdAt: item?.created_at || payload.created_at,
  };
}

export function profileFields(item) {
  if (typeof item === "string") {
    return { chatId: item, name: item, content: "", updatedAt: "" };
  }
  const front = item?.frontmatter && typeof item.frontmatter === "object" ? item.frontmatter : {};
  return {
    chatId: item?.chat_id ?? front.chat_id ?? item?.id,
    name: item?.name || front.name || item?.title || `Chat ${item?.chat_id ?? ""}`,
    filename: item?.filename || item?.path || "",
    relationship: item?.relationship || front.relationship || "",
    updatedAt: item?.updated_at || front.updated_at || "",
    content: item?.content ?? item?.markdown ?? item?.body ?? "",
  };
}
