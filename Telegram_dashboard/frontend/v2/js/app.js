import { ensureAuthenticated } from "./api.js";
import { mountTalk, openTalkChat } from "./talk.js";
import { mountAct } from "./act.js";
import { mountProfiles, openProfileChat, refreshProfilesIfVisible } from "./profiles.js";
import { setUiVersion } from "/static/js/ui-version.js";

const VIEWS = ["talk", "act", "profiles"];
const mounted = {
  talk: false,
  act: false,
  profiles: false,
};

function parseHash() {
  const raw = (window.location.hash || "#talk").replace(/^#/, "") || "talk";
  const [viewPart, queryPart = ""] = raw.split("?");
  const view = (viewPart || "talk").split("/")[0];
  const params = new URLSearchParams(queryPart);
  const chatFromQuery = params.get("chat");
  const chatFromPath = viewPart.includes("/") ? viewPart.split("/")[1] : null;
  return {
    view: VIEWS.includes(view) ? view : "talk",
    chatId: chatFromQuery || chatFromPath || null,
  };
}

function hashFor(view, chatId = null) {
  if ((view === "talk" || view === "profiles") && chatId != null && chatId !== "") {
    return `#${view}?chat=${encodeURIComponent(chatId)}`;
  }
  return `#${view}`;
}

function showView(name, { chatId = null, replaceHash = true } = {}) {
  if (!VIEWS.includes(name)) name = "talk";

  VIEWS.forEach((view) => {
    const section = document.getElementById(`view-${view}`);
    const btn = document.querySelector(`.v2-nav-btn[data-view="${view}"]`);
    const active = view === name;
    if (section) {
      section.hidden = !active;
      section.classList.toggle("is-visible", active);
    }
    if (btn) {
      btn.classList.toggle("is-active", active);
      if (active) btn.setAttribute("aria-current", "page");
      else btn.removeAttribute("aria-current");
    }
  });

  if (replaceHash) {
    const next = hashFor(
      name,
      name === "talk" || name === "profiles" ? chatId : null,
    );
    if (window.location.hash !== next) {
      history.replaceState(null, "", next);
    }
  }

  return ensureMounted(name).then(async () => {
    if (name === "talk" && chatId != null && chatId !== "") {
      return openTalkChat(chatId);
    }
    if (name === "profiles") {
      const pending =
        chatId || sessionStorage.getItem("v2-profiles-chat") || null;
      if (pending) {
        sessionStorage.removeItem("v2-profiles-chat");
        return openProfileChat(pending, { forceReload: true });
      }
      // Returning to Profiles without a chat target — refresh list
      return refreshProfilesIfVisible();
    }
    return undefined;
  });
}

async function ensureMounted(name) {
  if (mounted[name]) return;
  if (name === "talk") await mountTalk();
  if (name === "act") await mountAct();
  if (name === "profiles") await mountProfiles();
  mounted[name] = true;
}

function bindNav() {
  document.querySelectorAll(".v2-nav-btn[data-view]").forEach((btn) => {
    btn.addEventListener("click", () => {
      showView(btn.getAttribute("data-view"));
    });
  });

  window.addEventListener("hashchange", () => {
    const { view, chatId } = parseHash();
    if (chatId) {
      if (view === "talk") sessionStorage.setItem("v2-talk-chat", String(chatId));
      if (view === "profiles") {
        sessionStorage.setItem("v2-profiles-chat", String(chatId));
      }
    }
    showView(view, { chatId, replaceHash: false });
  });

  const toV1 = document.getElementById("switch-to-v1");
  if (toV1) {
    toV1.addEventListener("click", (event) => {
      event.preventDefault();
      setUiVersion("v1");
      window.location.href = "/";
    });
  }
}

async function boot() {
  const ok = await ensureAuthenticated();
  if (!ok) return;
  setUiVersion("v2");
  bindNav();
  const { view, chatId } = parseHash();
  let stored = chatId;
  if (!stored && view === "talk") {
    stored = sessionStorage.getItem("v2-talk-chat");
  }
  if (!stored && view === "profiles") {
    stored = sessionStorage.getItem("v2-profiles-chat");
  }
  if (stored) {
    if (view === "talk") sessionStorage.setItem("v2-talk-chat", String(stored));
    if (view === "profiles") {
      sessionStorage.setItem("v2-profiles-chat", String(stored));
    }
  }
  await showView(view, {
    chatId: view === "talk" || view === "profiles" ? stored : null,
  });
}

boot().catch((err) => {
  console.error(err);
  const main = document.querySelector(".v2-main");
  if (main) {
    main.innerHTML = `<p class="error-state" style="padding:1rem">${String(err.message || err)}</p>`;
  }
});
