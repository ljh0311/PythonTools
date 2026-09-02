// TODO: Attach Authorization header (Bearer token or session cookie) once login is implemented.
// TODO: Redirect to /login on 401 responses from protected API routes.

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

/** POST recording start/stop. Stop is idempotent; start may 404 if no frames yet. */
export async function postRecording(path) {
  const response = await fetch(apiUrl(path), { method: 'POST' });
  const data = await readJson(response);
  if (response.ok || data.status === 'success' || data.already_stopped) {
    return data;
  }
  if (response.status === 404 && path.includes('/api/recording/stop?')) {
    return { status: 'success', recording: false, already_stopped: true };
  }
  throw new Error(data.detail || `HTTP ${response.status}`);
}

/** GET JSON; returns null on 404 when optional is true. */
export async function fetchJson(path, { optional = false } = {}) {
  const response = await fetch(apiUrl(path));
  if (optional && response.status === 404) {
    return null;
  }
  const data = await readJson(response);
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

async function parseJsonResponse(response) {
  const data = await readJson(response);
  if (!response.ok) {
    throw new Error(data.detail || `HTTP ${response.status}`);
  }
  return data;
}

/** DELETE a media file by project-relative path. */
export async function deleteMediaFile(relativePath) {
  const response = await fetch(
    apiUrl(`/api/media/file?path=${encodeURIComponent(relativePath)}`),
    { method: 'DELETE' }
  );
  return parseJsonResponse(response);
}

/** DELETE a motion session (paired snapshots). */
export async function deleteMotionSession(sessionId, cameraId) {
  const response = await fetch(
    apiUrl(
      `/api/media/motion-sessions/${encodeURIComponent(sessionId)}?camera_id=${encodeURIComponent(cameraId)}`
    ),
    { method: 'DELETE' }
  );
  return parseJsonResponse(response);
}

/** Bulk delete media paths or by age. */
export async function deleteMediaBulk({ paths, olderThanDays, includeRecordings, includeSnapshots }) {
  const url = olderThanDays != null ? '/api/media/delete-older' : '/api/media/delete';
  const body =
    olderThanDays != null
      ? {
          older_than_days: olderThanDays,
          include_recordings: includeRecordings ?? true,
          include_snapshots: includeSnapshots ?? true,
        }
      : { paths };
  const response = await fetch(apiUrl(url), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return parseJsonResponse(response);
}
