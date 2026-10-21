"""Probe touch-shot — screenshot do 3v3 com os controles touch visiveis.
Simula o gate visual de mobile (body.touch) e captura o HUD em partida real.
Run: python tools/probe_touch_shot.py   (cwd = repo root)
"""
import asyncio
import base64
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
PROFILE = tempfile.mkdtemp(prefix='nuba_touchshot_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1600,900', '--inprivate', f'--user-data-dir={PROFILE}',
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
    # gate visual de mobile (mesma classe que __DEVICE.add('touch') setaria)
    await c.eval_js("document.body.classList.add('touch')")
    ok = await c.eval_js("(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    await asyncio.sleep(6)
    state = await c.eval_js("(() => { const tc = document.getElementById('touch-controls'); const joy = document.getElementById('touch-joystick'); const clu = document.getElementById('touch-cluster'); return { touchVisible: tc ? getComputedStyle(tc).display !== 'none' : false, joystick: joy ? getComputedStyle(joy).display !== 'none' : false, cluster: clu ? getComputedStyle(clu).display !== 'none' : false, units: window.units.length, goal: document.title.includes('x') } })()")
    print('estado touch-shot:', state)
    shot = await c.send("Page.captureScreenshot", {"format": "png"})
    img = base64.b64decode(shot.get("data") or shot.get("result", {}).get("data"))
    out = os.environ.get("TEMP", "/tmp") + "/nuba_touch_shot.png"
    open(out, "wb").write(img)
    print('screenshot salvo:', out, len(img), 'bytes')
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
