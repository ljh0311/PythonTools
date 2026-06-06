const THEME_KEY = "telegram-dashboard-theme";

export function initTheme() {
  const saved = localStorage.getItem(THEME_KEY);
  const theme = saved === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);

  const toggle = document.getElementById("theme-toggle");
  if (!toggle) return;

  toggle.textContent = theme === "dark" ? "Light mode" : "Dark mode";
  toggle.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    localStorage.setItem(THEME_KEY, next);
    toggle.textContent = next === "dark" ? "Light mode" : "Dark mode";
  });
}
