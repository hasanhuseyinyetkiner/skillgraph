// Run from any directory: node scripts/record-demo.mjs
// Requires frontend dependencies, backend/.venv, Playwright Chromium, and ffmpeg.
// Everything except the final GIF stays in a new temporary directory, which is
// deliberately retained for inspection; no existing database or server is reused.
import { spawn, spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { mkdtemp, writeFile, mkdir, copyFile } from 'node:fs/promises';
import net from 'node:net';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const frontend = path.join(root, 'frontend');
const backend = path.join(root, 'backend');
const require = createRequire(path.join(frontend, 'package.json'));
const { chromium, expect } = require('@playwright/test');
const tmp = await mkdtemp(path.join(os.tmpdir(), 'skillgraph-record-'));
const db = path.join(tmp, 'synthetic.sqlite').replaceAll('\\', '/');
const videoDir = path.join(tmp, 'video');
await mkdir(videoDir);

async function freePort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => server.once('error', reject).listen(0, '127.0.0.1', resolve));
  const port = server.address().port;
  await new Promise((resolve, reject) => server.close(err => err ? reject(err) : resolve()));
  return port;
}
const apiPort = await freePort();
let webPort = await freePort();
while (webPort === apiPort) webPort = await freePort();
const api = `http://127.0.0.1:${apiPort}`;
const web = `http://127.0.0.1:${webPort}`;
console.log(`Temporary run: ${tmp}\nAPI: ${api}\nUI: ${web}\nDatabase: ${db}`);

// Resolve plugins from the existing frontend install, but keep Vite's cache and
// configuration in the temporary directory and use no project webServer config.
const react = pathToFileURL(require.resolve('@vitejs/plugin-react')).href;
const tailwind = pathToFileURL(require.resolve('@tailwindcss/vite')).href;
const config = path.join(tmp, 'vite.config.mjs');
await writeFile(config, `import react from ${JSON.stringify(react)};\nimport tailwind from ${JSON.stringify(tailwind)};\nexport default { root: ${JSON.stringify(frontend)}, cacheDir: ${JSON.stringify(path.join(tmp, 'vite-cache'))}, plugins: [react(), tailwind()], server: { host: '127.0.0.1', port: ${webPort}, strictPort: true } };\n`);
const processes = [];
function start(label, executable, args, options) {
  const child = spawn(executable, args, { ...options, windowsHide: true, stdio: ['ignore', 'pipe', 'pipe'] });
  child.output = '';
  child.stdout.on('data', data => { child.output += data; process.stdout.write(`[${label}] ${data}`); });
  child.stderr.on('data', data => { child.output += data; process.stderr.write(`[${label}] ${data}`); });
  child.on('error', error => console.error(`[${label}] ${error.message}`));
  processes.push(child);
  return child;
}
async function ready(url, child, label, listeningMarker) {
  const end = Date.now() + 90000;
  while (Date.now() < end) {
    if (child.exitCode !== null || child.signalCode !== null) throw new Error(`${label} exited before readiness`);
    try { if (child.output.includes(listeningMarker) && (await fetch(url, { signal: AbortSignal.timeout(1000) })).ok) return; } catch {}
    await new Promise(resolve => setTimeout(resolve, 300));
  }
  throw new Error(`${label} did not become ready`);
}
let browser;
try {
  const python = process.platform === 'win32' ? path.join(backend, '.venv', 'Scripts', 'python.exe') : path.join(backend, '.venv', 'bin', 'python');
  // Alembic may disable Uvicorn's loggers, so announce readiness only after
  // Uvicorn itself reports that it has successfully bound its socket.
  const runner = `import asyncio, uvicorn\nfrom app.main import app\nfrom app.settings import assert_bind_allowed\nasync def run():\n s = app.state.settings\n assert_bind_allowed(s.host, s.allow_network_bind)\n server = uvicorn.Server(uvicorn.Config(app, host=s.host, port=s.port))\n task = asyncio.create_task(server.serve())\n while not server.started and not task.done(): await asyncio.sleep(0.1)\n if server.started: print('OWN_API_BOUND', flush=True)\n await task\nasyncio.run(run())\n`;
  const apiProcess = start('api', python, ['-c', runner], { cwd: backend, env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1', APP_ENV: 'demo', HOST: '127.0.0.1', PORT: String(apiPort), ALLOW_NETWORK_BIND: 'false', DATABASE_URL: `sqlite:///${db}`, AUTO_SEED: 'true', RUN_MIGRATIONS: 'true', EMBEDDINGS_ENABLED: 'false', CORS_ORIGINS: web } });
  await ready(`${api}/ready`, apiProcess, 'API', 'OWN_API_BOUND');
  const vite = path.join(path.dirname(require.resolve('vite/package.json')), 'bin', 'vite.js');
  const uiProcess = start('ui', process.execPath, [vite, '--config', config], { cwd: frontend, env: { ...process.env, VITE_API_BASE: api } });
  await ready(web, uiProcess, 'UI', web);
  browser = await chromium.launch({ headless: true });
  // Warm Vite's dependency optimizer before starting the actual recording.
  const warmup = await browser.newPage();
  await warmup.goto(web);
  await expect(warmup.getByRole('heading', { name: /Avery Chen/i })).toBeVisible({ timeout: 30000 });
  await warmup.close();
  const context = await browser.newContext({ viewport: { width: 1024, height: 768 }, recordVideo: { dir: videoDir, size: { width: 1024, height: 768 } } });
  await context.addInitScript(() => localStorage.setItem('skillgraph-theme', 'light'));
  const page = await context.newPage();
  page.on('pageerror', error => console.error(`Page error: ${error.message}`));
  const pause = ms => page.waitForTimeout(ms);
  const choose = async (id, name) => {
    const select = page.getByTestId(id);
    await expect(select.locator('option').filter({ hasText: name }).first()).toHaveCount(1);
    await select.selectOption({ label: await select.locator('option').filter({ hasText: name }).first().textContent() });
  };
  await page.goto(web);
  await expect(page.getByTestId('demo-banner')).toContainText('Local demo');
  await expect(page.getByRole('heading', { name: /Avery Chen/i })).toBeVisible();
  await pause(1600);
  await page.getByRole('link', { name: 'Graph' }).click();
  await expect(page.getByTestId('cytoscape-canvas')).toBeVisible();
  await expect(page.getByText(/Graph v\d+ · \d+ nodes · \d+ edges/)).toBeVisible({ timeout: 30000 });
  await page.getByTestId('cytoscape-canvas').scrollIntoViewIfNeeded();
  await pause(2500);
  await page.getByRole('link', { name: 'Roles' }).click();
  await expect(page.getByRole('heading', { name: 'Role Explorer' })).toBeVisible();
  await choose('role-select', 'Analytics Engineer');
  await pause(700);
  await page.getByTestId('compute-fit').click();
  await expect(page.getByTestId('fit-index')).toBeVisible();
  await page.getByTestId('fit-index').scrollIntoViewIfNeeded();
  await pause(2400);
  await page.getByRole('link', { name: 'Paths' }).click();
  await expect(page.getByRole('heading', { name: 'Path Builder' })).toBeVisible();
  await choose('path-role-select', 'Analytics Engineer');
  await pause(700);
  await page.getByTestId('build-path').click();
  await expect(page.getByText(/Cycle-free:\s*yes/i)).toBeVisible();
  await expect(page.getByTestId('path-steps').locator('li').first()).toBeVisible();
  await page.getByTestId('path-steps').scrollIntoViewIfNeeded();
  await pause(2800);
  const video = page.video();
  await context.close();
  const videoPath = await video.path();
  await browser.close();
  browser = undefined;
  const gif = path.join(tmp, 'demo.gif');
  const result = spawnSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-i', videoPath, '-filter_complex', 'fps=6,scale=1000:-2:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=diff[p];[b][p]paletteuse=dither=sierra2_4a:diff_mode=rectangle', '-loop', '0', gif], { stdio: 'inherit' });
  if (result.error || result.status !== 0) throw result.error || new Error(`ffmpeg exited ${result.status}`);
  await mkdir(path.join(root, 'docs', 'assets'), { recursive: true });
  await copyFile(gif, path.join(root, 'docs', 'assets', 'demo.gif'));
  console.log(`Validated profile → graph → Analytics Engineer fit → learning path.\nRecording: ${videoPath}\nGIF: ${path.join(root, 'docs', 'assets', 'demo.gif')}`);
} finally {
  if (browser) await browser.close();
  for (const child of processes.reverse()) {
    if (child.exitCode !== null || child.signalCode !== null) continue;
    const exited = new Promise(resolve => child.once('exit', resolve));
    if (process.platform === 'win32') spawnSync('taskkill', ['/pid', String(child.pid), '/t', '/f'], { stdio: 'ignore', windowsHide: true });
    else child.kill();
    await Promise.race([exited, new Promise(resolve => setTimeout(resolve, 5000))]);
  }
}
