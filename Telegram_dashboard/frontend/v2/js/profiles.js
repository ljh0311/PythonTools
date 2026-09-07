import { api } from "./api.js";
import { asList, escapeHtml, formatTime, profileFields, showToast } from "./utils.js";

const state = {
  profiles: [],
  selectedChatId: null,
  content: "",
  name: "",
  dirty: false,
  loadingList: false,
  loadingDetail: false,
};

function root() {
  return document.getElementById("view-profiles");
}

function renderShell() {
  const el = root();
  el.innerHTML = `
    <div class="panel-grid">
      <aside class="panel">
        <div class="panel-header">
          <h2>Contacts</h2>
          <div class="panel-actions">
            <button type="button" class="btn btn-ghost" id="profiles-reload">Reload</button>
          </div>
        </div>
        <div class="panel-body" id="profiles-list"></div>
      </aside>
      <section class="panel">
        <div class="panel-header">
          <h2 id="profile-title">Profile</h2>
          <div class="panel-actions">
            <button type="button" class="btn btn-ghost" id="profile-refresh" disabled>Refresh from chat</button>
            <button type="button" class="btn btn-primary" id="profile-save" disabled>Save</button>
          </div>
        </div>
        <div class="panel-body" id="profile-pane">
          <p class="empty-state">Select a profile to preview and edit markdown.</p>
        </div>
      </section>
    </div>
  `;

  el.querySelector("#profiles-reload").addEventListener("click", () => loadProfiles());
  el.querySelector("#profile-refresh").addEventListener("click", () => refreshFromChat());
  el.querySelector("#profile-save").addEventListener("click", () => saveProfile());
}

function setActionEnabled(enabled) {
  const refresh = document.getElementById("profile-refresh");
  const save = document.getElementById("profile-save");
  if (refresh) refresh.disabled = !enabled;
  if (save) save.disabled = !enabled || !state.dirty;
}

function renderList() {
  const list = document.getElementById("profiles-list");
  if (!list) return;

  if (state.loadingList) {
    list.innerHTML = `<p class="loading-state">Loading profiles…</p>`;
    return;
  }

  if (!state.profiles.length) {
    list.innerHTML = `<p class="empty-state">No profiles yet. Refresh from a chat to create one.</p>`;
    return;
  }

  list.innerHTML = state.profiles
    .map((raw) => {
      const p = profileFields(raw);
      const active = String(p.chatId) === String(state.selectedChatId);
      return `
        <button type="button" class="list-item ${active ? "is-active" : ""}" data-chat-id="${escapeHtml(p.chatId)}">
          <p class="list-title">${escapeHtml(p.name)}</p>
          <p class="list-meta">${escapeHtml(p.relationship || "contact")} · ${escapeHtml(formatTime(p.updatedAt) || "—")}</p>
          <p class="list-preview">${escapeHtml(p.filename || `chat ${p.chatId}`)}</p>
        </button>
      `;
    })
    .join("");

  list.querySelectorAll("[data-chat-id]").forEach((btn) => {
    btn.addEventListener("click", () => selectProfile(btn.getAttribute("data-chat-id")));
  });
}

function renderEditor() {
  const pane = document.getElementById("profile-pane");
  const title = document.getElementById("profile-title");
  if (!pane || !title) return;

  if (!state.selectedChatId) {
    title.textContent = "Profile";
    pane.innerHTML = `<p class="empty-state">Select a profile to preview and edit markdown.</p>`;
    setActionEnabled(false);
    return;
  }

  title.textContent = state.name || `Chat ${state.selectedChatId}`;

  if (state.loadingDetail) {
    pane.innerHTML = `<p class="loading-state">Loading profile…</p>`;
    setActionEnabled(false);
    return;
  }

  pane.innerHTML = `
    <div class="profile-editor">
      <label class="sr-only" for="profile-md">Profile markdown</label>
      <textarea id="profile-md" spellcheck="true">${escapeHtml(state.content)}</textarea>
      <div>
        <p class="list-meta" style="margin:0 0 0.35rem">Preview</p>
        <pre class="profile-preview" id="profile-preview">${escapeHtml(state.content || "(empty)")}</pre>
      </div>
    </div>
  `;

  const textarea = pane.querySelector("#profile-md");
  const preview = pane.querySelector("#profile-preview");
  textarea.addEventListener("input", () => {
    state.content = textarea.value;
    state.dirty = true;
    preview.textContent = state.content || "(empty)";
    setActionEnabled(true);
  });

  setActionEnabled(true);
}

async function loadProfiles() {
  state.loadingList = true;
  renderList();
  try {
    const data = await api.getProfiles();
    state.profiles = asList(data, ["profiles", "items"]);
    renderList();
  } catch (err) {
    const list = document.getElementById("profiles-list");
    if (list) {
      list.innerHTML = `<p class="error-state">${escapeHtml(err.message || "Failed to load profiles")}</p>`;
    }
    showToast(err.message || "Failed to load profiles", { error: true });
  } finally {
    state.loadingList = false;
  }
}

async function selectProfile(chatId) {
  if (state.dirty) {
    const ok = window.confirm("Discard unsaved profile edits?");
    if (!ok) return;
  }
  state.selectedChatId = chatId;
  state.loadingDetail = true;
  state.dirty = false;
  renderList();
  renderEditor();
  try {
    const data = await api.getProfile(chatId);
    const fields = profileFields(data);
    state.name = fields.name;
    state.content = fields.content || "";
    renderEditor();
  } catch (err) {
    const pane = document.getElementById("profile-pane");
    if (pane) {
      pane.innerHTML = `<p class="error-state">${escapeHtml(err.message || "Failed to load profile")}</p>`;
    }
    showToast(err.message || "Failed to load profile", { error: true });
  } finally {
    state.loadingDetail = false;
  }
}

async function saveProfile() {
  if (!state.selectedChatId) return;
  const saveBtn = document.getElementById("profile-save");
  if (saveBtn) saveBtn.disabled = true;
  try {
    const data = await api.saveProfile(state.selectedChatId, {
      content: state.content,
      markdown: state.content,
    });
    const fields = profileFields(data);
    if (fields.content) state.content = fields.content;
    state.dirty = false;
    showToast("Profile saved");
    await loadProfiles();
    renderEditor();
  } catch (err) {
    showToast(err.message || "Save failed", { error: true });
    setActionEnabled(true);
  }
}

async function refreshFromChat() {
  if (!state.selectedChatId) return;
  if (state.dirty) {
    const ok = window.confirm("Refresh will overwrite the editor. Continue?");
    if (!ok) return;
  }
  const btn = document.getElementById("profile-refresh");
  if (btn) btn.disabled = true;
  try {
    const data = await api.refreshProfile(state.selectedChatId);
    const fields = profileFields(data);
    state.name = fields.name || state.name;
    state.content = fields.content || state.content;
    state.dirty = false;
    showToast("Profile refreshed from chat");
    await loadProfiles();
    renderEditor();
  } catch (err) {
    showToast(err.message || "Refresh failed", { error: true });
    setActionEnabled(true);
  }
}

export async function mountProfiles() {
  renderShell();
  await loadProfiles();
}

export function refreshProfilesIfVisible() {
  const el = root();
  if (el?.classList.contains("is-visible")) {
    return loadProfiles();
  }
  return Promise.resolve();
}
