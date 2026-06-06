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

export const api = {
  getMetrics: () => request("/api/metrics"),
  getMessages: (limit = 50) => request(`/api/messages?limit=${limit}`),
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
