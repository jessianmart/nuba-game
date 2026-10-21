"""Probe BR-shot — screenshot do modo REALEZA NA VILA em andamento.
startMatch('br_vila') -> espera a batalha/rolar -> screenshot -> desliga.
Run: python tools/probe_br_shot.py   (cwd = repo root)
"""
import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time

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


import urllib.request  # noqa: E402

PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_brshot_')
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
    ok = await c.eval_js("(async () => { try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    # deixa a partida rolar: combate + zona + baús (curto: fim natural e' rapido no BR)
    await asyncio.sleep(12)
    import base64
    shot = await c.send("Page.captureScreenshot", {"format": "png"})
    data = shot.get("data") or shot.get("result", {}).get("data")
    img = base64.b64decode(data)
    out = os.environ.get("TEMP", "/tmp") + "/nuba_br_shot.png"
    open(out, "wb").write(img)
    print('screenshot salvo:', out, len(img), 'bytes')
    try:
        state = await c.eval_js("(() => { const br = window.__matchState.br; const p = window.units.find(u => u.isPlayer); return { alive: br.alive, phase: br.phase, zoneR: Math.round(br.zoneR * 10) / 10, hp: p.hp, taken: br.chests.filter(x => x.taken).length }; })()")
        print('estado BR:', state)
    except Exception as e:
        print('estado BR indisponivel (timeout CDP):', type(e).__name__)
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
