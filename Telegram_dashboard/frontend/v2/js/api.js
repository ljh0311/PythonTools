/** Auth + /api/v2 client — mirrors frontend/js/api.js patterns. */

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

function formatApiErrorDetail(detail) {
  if (detail == null || detail === "") return null;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          return item.msg || item.message || JSON.stringify(item);
        }
        return String(item);
      })
      .join("; ");
  }
  return String(detail);
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
    throw new Error(
      formatApiErrorDetail(error.detail) || `Request failed: ${response.status}`,
    );
  }

  if (response.status === 204) return null;

  const contentType = response.headers.get("Content-Type") || "";
  if (contentType.includes("text/markdown") || contentType.includes("text/plain")) {
    return response.text();
  }
  return response.json();
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
  getTalkThreads: (params = {}) =>
    request(`/api/v2/talk/threads${buildQuery(params)}`),
  getTalkMessages: (chatId, params = {}) =>
    request(`/api/v2/talk/threads/${encodeURIComponent(chatId)}/messages${buildQuery(params)}`),

  getAct: (params = {}) => request(`/api/v2/act${buildQuery(params)}`),
  refreshAct: () => request("/api/v2/act/refresh", { method: "POST" }),
  patchAct: (id, status) =>
    request(`/api/v2/act/${encodeURIComponent(id)}`, {
      method: "PATCH",
      body: JSON.stringify({ status }),
    }),
  sendActDraft: (id, text) =>
    request(`/api/v2/act/${encodeURIComponent(id)}/send`, {
      method: "POST",
      body: JSON.stringify(text ? { text } : {}),
    }),

  getProfiles: () => request("/api/v2/profiles"),
  getProfile: (chatId) =>
    request(`/api/v2/profiles/${encodeURIComponent(chatId)}`),
  saveProfile: (chatId, body) =>
    request(`/api/v2/profiles/${encodeURIComponent(chatId)}`, {
      method: "PUT",
      body: JSON.stringify(typeof body === "string" ? { markdown: body } : body),
    }),
  refreshProfile: (chatId) =>
    request(`/api/v2/profiles/${encodeURIComponent(chatId)}/refresh`, {
      method: "POST",
    }),
};
