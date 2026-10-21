"""Diag responsividade — dump de rects do HUD top em 568x320 (SE-land).
Run: python tools/probe_resp_diag.py   (cwd = repo root)
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_respdiag_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=568,320', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json(PORT, '/json')
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()
    for _ in range(40):
        t = await c.eval_js('typeof window.startMatch')
        if t == 'function':
            break
        await asyncio.sleep(0.5)
    await c.eval_js("document.body.classList.add('touch')")
    await c.eval_js("(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    await asyncio.sleep(1.0)
    await c.send("Emulation.setDeviceMetricsOverride", {"width": 568, "height": 320, "deviceScaleFactor": 1, "mobile": True})
    await asyncio.sleep(0.4)
    r = await c.eval_js("""(() => {
      const out = [];
      const push = (sel) => { const el = document.querySelector(sel); if (!el) { out.push(sel + ': MISSING'); return; }
        const b = el.getBoundingClientRect();
        out.push(`${sel}: l=${Math.round(b.left)} r=${Math.round(b.right)} w=${Math.round(b.width)} h=${Math.round(b.height)} display=${getComputedStyle(el).display} overflowX=${el.scrollWidth > el.clientWidth ? 'SIM' : 'nao'}`); };
      push('.hud-top-bar');
      push('.team-group.blue');
      push('.team-group.red');
      push('.match-center-cluster');
      push('#hud-blue-icons');
      push('#hud-red-icons');
      push('.team-avatars-row');
      push('#match-timer');
      push('.match-goal-txt');
      push('.storm-vs-crest');
      push('#br-hud');
      push('#touch-cluster');
      const bs = [...document.querySelectorAll('.team-avatars-row .mini-p')].map(e => { const b = e.getBoundingClientRect(); return `${Math.round(b.width)}x${Math.round(b.height)}`; });
      out.push('mini-portraits: ' + bs.join(' '));
      return out.join('\\n');
    })()""")
    if isinstance(r, dict) and 'value' in r:
        r = r['value']
    print(f'=== RECTS 568x320 ===\n{r}\n=== innerW={await c.eval_js("window.innerWidth")} ===')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    import shutil  # noqa: E402
    shutil.rmtree(PROFILE, ignore_errors=True)
