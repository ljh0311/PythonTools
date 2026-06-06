const API_KEY = localStorage.getItem("dashboard-api-key") || "dev-dashboard-key";

const headers = {
  "Content-Type": "application/json",
  "X-API-Key": API_KEY,
};

async function request(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { ...headers, ...(options.headers || {}) },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
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

export const api = {
  getMetrics: () => request("/api/metrics"),
  getUsers: () => request("/api/users"),
  getMessages: (params = {}) => request(`/api/messages${buildQuery(params)}`),
  getInboxThreads: (params = {}) => request(`/api/inbox/threads${buildQuery(params)}`),
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
  setChatAutoReply: (chatId, enabled) =>
    request(`/api/settings/chat-replies/${chatId}`, {
      method: "PUT",
      body: JSON.stringify({ enabled }),
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
};

export function connectWebSocket(onMessage) {
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(
    `${protocol}://${window.location.host}/api/ws?api_key=${encodeURIComponent(API_KEY)}`
  );

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
