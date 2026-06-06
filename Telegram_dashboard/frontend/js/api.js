function authHeaders() {
  const session = sessionStorage.getItem("dashboard-token");
  if (session) {
    return { Authorization: `Bearer ${session}` };
  }
  const apiKey = localStorage.getItem("dashboard-api-key");
  if (apiKey) {
    return { "X-API-Key": apiKey };
  }
  return { "X-API-Key": "dev-dashboard-key" };
}

const baseHeaders = {
  "Content-Type": "application/json",
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...baseHeaders, ...authHeaders(), ...(options.headers || {}) },
  });

  if (response.status === 401 && !path.includes("/auth/")) {
    sessionStorage.removeItem("dashboard-token");
    if (!window.location.pathname.includes("login")) {
      window.location.href = "/login";
    }
    throw new Error("Session expired. Please sign in again.");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("text/csv")) {
    return response.text();
  }
  return response.json();
}

function buildQuery(params = {}) {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      search.set(key, value);
    }
  });
  const query = search.toString();
  return query ? `?${query}` : "";
}

export async function ensureAuthenticated() {
  const status = await fetch("/api/auth/status").then((r) => r.json());
  const token = sessionStorage.getItem("dashboard-token");
  if (status.password_login_enabled) {
    if (!token) {
      window.location.href = "/login";
      return false;
    }
    try {
      await request("/api/auth/me");
      return true;
    } catch {
      window.location.href = "/login";
      return false;
    }
  }
  return true;
}

export const api = {
  getMetrics: () => request("/api/metrics"),
  getUsers: () => request("/api/users"),
  getMessages: (params = {}) => request(`/api/messages${buildQuery(params)}`),
  getInboxThreads: (params = {}) => request(`/api/inbox/threads${buildQuery(params)}`),
  exportMessages: (params = {}) => request(`/api/export/messages${buildQuery(params)}`),
  getPresets: () => request("/api/presets"),
  savePreset: (name, filters) =>
    request("/api/presets", { method: "POST", body: JSON.stringify({ name, filters }) }),
  deletePreset: (id) => request(`/api/presets/${id}`, { method: "DELETE" }),
  summarizeThread: (chatId, messageIds) =>
    request("/api/ai/summarize-thread", {
      method: "POST",
      body: JSON.stringify({ chat_id: chatId, message_ids: messageIds }),
    }),
  summarize: (payload) =>
    request("/api/ai/summarize", { method: "POST", body: JSON.stringify(payload) }),
  suggestActions: (payload) =>
    request("/api/ai/suggest-actions", { method: "POST", body: JSON.stringify(payload) }),
  getEvents: (limit = 50) => request(`/api/events?limit=${limit}`),
  getAnalytics: (days = 7) => request(`/api/analytics/commands?days=${days}`),
  getQuickActions: () => request("/api/quick-actions"),
  saveQuickActions: (actions) =>
    request("/api/quick-actions", {
      method: "PUT",
      body: JSON.stringify({ actions }),
    }),
  getFeedback: () => request("/api/feedback"),
  submitFeedback: (payload) =>
    request("/api/feedback", { method: "POST", body: JSON.stringify(payload) }),
  sendMessage: (chatId, text) =>
    request("/api/send", {
      method: "POST",
      body: JSON.stringify({ chat_id: chatId, text }),
    }),
  getBotStatus: () => request("/api/bot/status"),
  getReplyMode: () => request("/api/settings/reply-mode"),
  setReplyMode: (mode) =>
    request("/api/settings/reply-mode", {
      method: "PUT",
      body: JSON.stringify({ mode }),
    }),
  getChatSettings: (chatId) => request(`/api/settings/chat-replies/${chatId}`),
  updateChatSettings: (chatId, payload) =>
    request(`/api/settings/chat-replies/${chatId}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  regenerateChatRelationship: (chatId) =>
    request(`/api/settings/chat-replies/${chatId}/regenerate-relationship`, {
      method: "POST",
    }),
  getTopicMode: () => request("/api/settings/topic-mode"),
  setTopicMode: (mode) =>
    request("/api/settings/topic-mode", {
      method: "PUT",
      body: JSON.stringify({ mode }),
    }),
  getTopics: () => request("/api/topics"),
  addMessageTopics: (messageId, topics) =>
    request(`/api/messages/${messageId}/topics`, {
      method: "POST",
      body: JSON.stringify({ topics }),
    }),
  removeMessageTopic: (messageId, topicName) =>
    request(`/api/messages/${messageId}/topics/${encodeURIComponent(topicName)}`, {
      method: "DELETE",
    }),
  updateSuggestionStatus: (suggestionId, status) =>
    request(`/api/suggestions/${suggestionId}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  logout: () => request("/api/auth/logout", { method: "POST" }),
};

export function connectWebSocket(onMessage) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const token = sessionStorage.getItem("dashboard-token");
  const apiKey = localStorage.getItem("dashboard-api-key") || "dev-dashboard-key";
  const query = token
    ? `token=${encodeURIComponent(token)}`
    : `api_key=${encodeURIComponent(apiKey)}`;
  const ws = new WebSocket(`${protocol}://${window.location.host}/api/ws?${query}`);

  ws.onmessage = (event) => {
    try {
      onMessage(JSON.parse(event.data));
    } catch {
      /* ignore malformed payloads */
    }
  };

  ws.onclose = () => {
    setTimeout(() => connectWebSocket(onMessage), 3000);
  };

  return ws;
}
