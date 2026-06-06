const VIEW_KEY = "telegram-dashboard-view";

export function initNavigation(onChange) {
  const links = document.querySelectorAll("[data-view-target]");
  const saved = localStorage.getItem(VIEW_KEY) || "inbox";

  function showView(name) {
    document.querySelectorAll(".app-view").forEach((el) => {
      el.hidden = el.dataset.view !== name;
    });
    links.forEach((link) => {
      const active = link.dataset.viewTarget === name;
      link.classList.toggle("active", active);
      if (active) link.setAttribute("aria-current", "page");
      else link.removeAttribute("aria-current");
    });
    localStorage.setItem(VIEW_KEY, name);
    onChange?.(name);
  }

  links.forEach((link) => {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      showView(link.dataset.viewTarget);
    });
  });

  showView(saved);
  return { showView };
}
