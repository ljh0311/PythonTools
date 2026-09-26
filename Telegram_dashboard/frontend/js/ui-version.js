/** Shared Operator (v1) / Awareness (v2) UI preference. */
export const UI_VERSION_KEY = "telegram-dashboard-ui-version";

export function getUiVersion() {
  return localStorage.getItem(UI_VERSION_KEY) === "v2" ? "v2" : "v1";
}

export function setUiVersion(version) {
  const next = version === "v2" ? "v2" : "v1";
  localStorage.setItem(UI_VERSION_KEY, next);
  return next;
}

export function homePathForUi(version = getUiVersion()) {
  return version === "v2" ? "/v2" : "/";
}

export function switchToUi(version) {
  const next = setUiVersion(version);
  window.location.href = homePathForUi(next);
}
