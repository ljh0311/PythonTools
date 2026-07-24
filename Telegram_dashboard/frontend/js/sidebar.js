const MOBILE_QUERY = "(max-width: 899px)";

export function initSidebar() {
  const shell = document.querySelector(".app-shell");
  const sidebar = document.getElementById("sidebar");
  const toggle = document.getElementById("sidebar-toggle");
  const backdrop = document.getElementById("sidebar-backdrop");
  const media = window.matchMedia(MOBILE_QUERY);

  if (!shell || !sidebar || !toggle || !backdrop) {
    return { closeSidebar: () => {}, isOpen: () => false };
  }

  let open = false;

  function isMobile() {
    return media.matches;
  }

  function setOpen(next) {
    open = next;
    const mobileOpen = open && isMobile();
    shell.classList.toggle("sidebar-open", mobileOpen);
    toggle.setAttribute("aria-expanded", String(open));
    toggle.setAttribute("aria-label", open ? "Close navigation" : "Open navigation");
    backdrop.hidden = !mobileOpen;
    backdrop.setAttribute("aria-hidden", String(!mobileOpen));
    document.body.classList.toggle("sidebar-drawer-open", mobileOpen);
  }

  function closeSidebar() {
    if (!open) return;
    setOpen(false);
    toggle.focus();
  }

  function toggleSidebar() {
    if (!isMobile()) return;
    setOpen(!open);
  }

  function onViewportChange() {
    if (!isMobile()) {
      setOpen(false);
      backdrop.hidden = true;
      backdrop.setAttribute("aria-hidden", "true");
      document.body.classList.remove("sidebar-drawer-open");
      shell.classList.remove("sidebar-open");
      return;
    }
    backdrop.hidden = !open;
    backdrop.setAttribute("aria-hidden", String(!open));
    shell.classList.toggle("sidebar-open", open);
  }

  toggle.addEventListener("click", toggleSidebar);
  backdrop.addEventListener("click", closeSidebar);

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && open && isMobile()) {
      event.preventDefault();
      closeSidebar();
    }
  });

  sidebar.querySelectorAll("[data-view-target]").forEach((item) => {
    item.addEventListener("click", () => {
      if (isMobile()) closeSidebar();
    });
  });

  media.addEventListener("change", onViewportChange);

  return { closeSidebar, isOpen: () => open };
}
