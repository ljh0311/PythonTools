import { ensureAuthenticated } from "./api.js";
import { mountTalk, openTalkChat } from "./talk.js";
import { mountAct } from "./act.js";
import { mountProfiles } from "./profiles.js";

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
  if (view === "talk" && chatId != null && chatId !== "") {
    return `#talk?chat=${encodeURIComponent(chatId)}`;
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
    const next = hashFor(name, name === "talk" ? chatId : null);
    if (window.location.hash !== next) {
      history.replaceState(null, "", next);
    }
  }

  return ensureMounted(name).then(() => {
    if (name === "talk" && chatId != null && chatId !== "") {
      return openTalkChat(chatId);
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
      sessionStorage.setItem("v2-talk-chat", String(chatId));
    }
    showView(view, { chatId, replaceHash: false });
  });
}

async function boot() {
  const ok = await ensureAuthenticated();
  if (!ok) return;
  bindNav();
  const { view, chatId } = parseHash();
  const stored =
    chatId || sessionStorage.getItem("v2-talk-chat") || null;
  if (stored) {
    sessionStorage.setItem("v2-talk-chat", String(stored));
  }
  await showView(view, { chatId: view === "talk" ? stored : null });
}

boot().catch((err) => {
  console.error(err);
  const main = document.querySelector(".v2-main");
  if (main) {
    main.innerHTML = `<p class="error-state" style="padding:1rem">${String(err.message || err)}</p>`;
  }
});
