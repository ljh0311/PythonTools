/**
 * Start FastAPI from web_version/backend, preferring web_version/venv Python if present.
 * Run from web_version/frontend via: npm run api
 */
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const webVersionRoot = path.resolve(__dirname, '..', '..');
const backendDir = path.join(webVersionRoot, 'backend');
const mainPy = path.join(backendDir, 'main.py');

if (!fs.existsSync(mainPy)) {
  console.error('Backend not found:', mainPy);
  process.exit(1);
}

const win = process.platform === 'win32';
const venvPython = win
  ? path.join(webVersionRoot, 'venv', 'Scripts', 'python.exe')
  : path.join(webVersionRoot, 'venv', 'bin', 'python');

const python = fs.existsSync(venvPython) ? venvPython : process.env.PYTHON || 'python';
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
