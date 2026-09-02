/**
 * Start FastAPI from web_version/backend, preferring web_version/venv Python if present.
 * Run from web_version/frontend via: npm run api
 */
const { spawn, execSync } = require('child_process');
const http = require('http');
const path = require('path');
const fs = require('fs');

const webVersionRoot = path.resolve(__dirname, '..', '..');
const backendDir = path.join(webVersionRoot, 'backend');
const mainPy = path.join(backendDir, 'main.py');
const API_PORT = 8000;

function getPortOwner(port) {
  try {
    const out = execSync(`netstat -ano | findstr ":${port}"`, { encoding: 'utf8', shell: true });
    const listening = out
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l.includes('LISTENING') && l.includes(`:${port}`));
    if (!listening.length) return null;
    const parts = listening[0].split(/\s+/);
    const pid = parseInt(parts[parts.length - 1], 10);
    return Number.isFinite(pid) ? pid : null;
  } catch {
    return null;
  }
}

function checkHealth(port) {
  return new Promise((resolve) => {
    const req = http.get(`http://127.0.0.1:${port}/health`, (res) => {
      let body = '';
      res.on('data', (c) => {
        body += c;
      });
      res.on('end', () => {
        try {
          const json = JSON.parse(body);
          resolve({ ok: res.statusCode === 200, json });
        } catch {
          resolve({ ok: false, json: null });
        }
      });
    });
    req.on('error', () => resolve({ ok: false, json: null }));
    req.setTimeout(3000, () => {
      req.destroy();
      resolve({ ok: false, json: null });
    });
  });
}

function isCurrentApi(health) {
  return (
    health.ok &&
    health.json?.status === 'healthy' &&
    health.json?.media_api === true &&
    health.json?.analytics_api === true &&
    health.json?.faces_api === true &&
    health.json?.rtsp_api === true &&
    health.json?.recording_stop_all_api === true
  );
}

function isStaleApi(health) {
  if (!health.ok || health.json?.status !== 'healthy') return false;
  return (
    !health.json?.media_api ||
    !health.json?.analytics_api ||
    !health.json?.faces_api ||
    !health.json?.rtsp_api ||
    !health.json?.recording_stop_all_api
  );
}

function killPid(pid) {
  try {
    if (process.platform === 'win32') {
      execSync(`taskkill /PID ${pid} /F`, { stdio: 'ignore', shell: true });
    } else {
      process.kill(pid, 'SIGTERM');
    }
    return true;
  } catch {
    return false;
  }
}

async function waitForPortFree(port, attempts = 30) {
  for (let i = 0; i < attempts; i += 1) {
    if (getPortOwner(port) === null) return true;
    await new Promise((resolve) => setImmediate(resolve));
  }
  return getPortOwner(port) === null;
}

function spawnApi() {
  console.log('[api]', fs.existsSync(venvPython) ? 'Using venv Python' : 'Using system python:', python);
  const child = spawn(python, ['main.py'], {
    cwd: backendDir,
    stdio: 'inherit',
    shell: win,
    env: { ...process.env },
  });

  child.on('exit', (code, signal) => {
    if (signal) process.kill(process.pid, signal);
    process.exit(code === null ? 1 : code);
  });
}

if (!fs.existsSync(mainPy)) {
  console.error('Backend not found:', mainPy);
  process.exit(1);
}

const win = process.platform === 'win32';
const venvPython = win
  ? path.join(webVersionRoot, 'venv', 'Scripts', 'python.exe')
  : path.join(webVersionRoot, 'venv', 'bin', 'python');

const python = fs.existsSync(venvPython) ? venvPython : process.env.PYTHON || 'python';

async function main() {
  let portOwner = getPortOwner(API_PORT);

  if (portOwner !== null) {
    const health = await checkHealth(API_PORT);

    if (isCurrentApi(health)) {
      console.log(
        `[api] Port ${API_PORT} already in use by PID ${portOwner} — reusing current API.`
      );
      setInterval(() => {}, 60_000);
      return;
    }

    if (isStaleApi(health)) {
      const missing = [];
      if (!health.json?.media_api) missing.push('media_api');
      if (!health.json?.analytics_api) missing.push('analytics_api');
      if (!health.json?.faces_api) missing.push('faces_api');
      if (!health.json?.rtsp_api) missing.push('rtsp_api');
      if (!health.json?.recording_stop_all_api) missing.push('recording_stop_all_api');
      console.log(
        `[api] Stale API on port ${API_PORT} (PID ${portOwner}) — missing ${missing.join(', ')}. Restarting…`
      );
      killPid(portOwner);
      const freed = await waitForPortFree(API_PORT);
      if (!freed) {
        console.error(`[api] Could not free port ${API_PORT}. Run: taskkill /PID ${portOwner} /F`);
        process.exit(1);
      }
      portOwner = null;
    } else if (portOwner !== null) {
      console.error(
        `[api] Port ${API_PORT} is in use (PID ${portOwner}) but /health did not respond correctly.`
      );
      console.error('[api] Stop the other process, then run npm run start:all again.');
      console.error(`[api] On Windows: taskkill /PID ${portOwner} /F`);
      process.exit(1);
    }
  }

  spawnApi();
}

main().catch((err) => {
  console.error('[api] Startup failed:', err);
  process.exit(1);
});
