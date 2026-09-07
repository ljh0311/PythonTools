import { ensureAuthenticated } from "./api.js";
import { mountTalk } from "./talk.js";
import { mountAct } from "./act.js";
import { mountProfiles } from "./profiles.js";

const VIEWS = ["talk", "act", "profiles"];
const mounted = {
  talk: false,
  act: false,
  profiles: false,
};

function showView(name) {
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

  if (window.location.hash !== `#${name}`) {
    history.replaceState(null, "", `#${name}`);
  }

  return ensureMounted(name);
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
    const hash = window.location.hash.replace(/^#/, "") || "talk";
    showView(hash);
  });
}

async function boot() {
  const ok = await ensureAuthenticated();
  if (!ok) return;
  bindNav();
  const initial = window.location.hash.replace(/^#/, "") || "talk";
  await showView(initial);
}

boot().catch((err) => {
  console.error(err);
  const main = document.querySelector(".v2-main");
  if (main) {
    main.innerHTML = `<p class="error-state" style="padding:1rem">${String(err.message || err)}</p>`;
  }
});
