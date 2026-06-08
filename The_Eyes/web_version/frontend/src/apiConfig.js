/**
 * Backend base URL.
 * - Development: defaults to http://127.0.0.1:8000 (browser talks to FastAPI directly;
 *   avoids CRA proxy ECONNREFUSED spam in the webpack terminal when the API is down).
 * - Override: REACT_APP_API_ORIGIN=https://host:port
 * - Production build: set REACT_APP_API_ORIGIN, or leave unset to use same-origin relative URLs.
 */
function stripSlash(s) {
  return s.replace(/\/$/, '');
}

const env = (process.env.REACT_APP_API_ORIGIN || '').trim();
const devDefault = 'http://127.0.0.1:8000';

export const apiOrigin = env
  ? stripSlash(env)
  : process.env.NODE_ENV === 'development'
    ? devDefault
    : '';

export function apiUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  return apiOrigin ? `${apiOrigin}${p}` : p;
}

export function wsUrl(path) {
  const p = path.startsWith('/') ? path : `/${path}`;
  if (apiOrigin) {
    try {
      const u = new URL(apiOrigin);
      const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${wsProto}//${u.host}${p}`;
    } catch {
      return `ws://127.0.0.1:8000${p}`;
    }
  }
  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProto}//${window.location.host}${p}`;
}

/** Parse fetch body as JSON; handle HTML error pages (e.g. old CRA proxy) gracefully. */
export async function readJson(response) {
  const text = await response.text();
  const trimmed = text.trim();
  const looksJson = trimmed.startsWith('{') || trimmed.startsWith('[');
  if (!looksJson) {
    if (/proxy error/i.test(text) || /DOCTYPE/i.test(text)) {
      throw new Error(
        'Backend not running on port 8000. From web_version/backend run: python main.py'
      );
    }
    throw new Error(`HTTP ${response.status}: ${trimmed.slice(0, 160) || '(empty body)'}`);
  }
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error(`Invalid JSON: ${e.message}`);
  }
}
