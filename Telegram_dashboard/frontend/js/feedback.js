import { api } from "./api.js";
import { initTheme } from "./theme.js";

function showToast(message) {
  const toast = document.getElementById("toast");
  if (!toast) return;
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2500);
}

function formatTime(iso) {
  if (!iso) return "";
  const date = new Date(iso.endsWith("Z") ? iso : `${iso}Z`);
  return date.toLocaleString();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function renderFeedback(items = []) {
  const feed = document.getElementById("feedback-feed");
  if (!items.length) {
    feed.innerHTML = `<li class="empty">No feedback submitted yet.</li>`;
    return;
  }
  feed.innerHTML = items
    .map(
      (item) => `
      <li>
        <div class="meta">
          <span>${escapeHtml(item.username || "Anonymous")} · ${item.rating}/5</span>
          <span>${formatTime(item.created_at)}</span>
        </div>
        <div>${escapeHtml(item.comment)}</div>
      </li>`
    )
    .join("");
}

async function refresh() {
  const items = await api.getFeedback();
  renderFeedback(items);
}

function bindForms() {
  document.getElementById("refresh-btn").addEventListener("click", () => {
    refresh().catch((error) => showToast(error.message));
  });

  document.getElementById("feedback-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const rating = Number(document.getElementById("feedback-rating").value);
    const comment = document.getElementById("feedback-comment").value.trim();
    try {
      await api.submitFeedback({ rating, comment, username: "dashboard_user" });
      document.getElementById("feedback-comment").value = "";
      showToast("Feedback submitted.");
      await refresh();
    } catch (error) {
      showToast(error.message);
    }
  });
}

initTheme();
bindForms();
refresh().catch((error) => showToast(error.message));
