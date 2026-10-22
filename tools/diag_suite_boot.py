"""Diag: reproduz o boot EXATO da suite (main() args + waits) e explica por que
o start_match_js falha. Run: python tools/diag_suite_boot.py  (cwd = repo root)
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

PROFILE = tempfile.mkdtemp(prefix='nuba_diag_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', '--remote-debugging-port=9222', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(2.5)


def http_json(path):
    with urllib.request.urlopen(f'http://127.0.0.1:9222{path}', timeout=5) as r:
        return json.load(r)


async def main():
    for _ in range(20):
        try:
            tabs = http_json('/json')
            break
        except Exception:
            time.sleep(0.5)
    print('tabs:', [(t.get('type'), t.get('url', '')[:60]) for t in tabs])
    ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws)
    await c.connect()
    await asyncio.sleep(3.5)

    async def ev(expr, ap=False):
        return await c.eval_js(expr, await_promise=ap)

    d = await ev("""(() => ({
        rs: document.readyState, title: document.title,
        startMatch: typeof window.startMatch,
        start5v5: typeof window.start5v5Match,
        matchActive: window.matchActive,
        units: window.units ? window.units.length : null,
        arena: window.__ARENA_LOADED ? window.__ARENA_LOADED.asset : null,
        bodyTouch: document.body.classList.contains('touch')
    }))()""")
    print('estado apos 6s:', d)

    r = await ev("""(async () => {
        if (!window.matchActive && typeof window.start5v5Match === 'function') {
            try { await window.start5v5Match(); } catch (e) { return 'ERR:' + e.message; }
        }
        for (let i = 0; i < 60; i++) {
            if (window.units && window.units.length === 10) return true;
            await new Promise(r => setTimeout(r, 100));
        }
        return false;
    })()""", ap=True)
    print('start_match_js ->', r)
    d2 = await ev("({ units: window.units ? window.units.length : null, matchActive: window.matchActive })")
    print('pos-tentativa:', d2)
    print(f'console errors: {len(c.console_errors)}')
    for e in c.console_errors[:8]:
        print('  ', str(e)[:200])
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
