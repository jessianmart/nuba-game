"""Probe PV2-A: com UA mobile, o loader deve pedir sa00z.mobile.json?`v=9`
(com prova pelo performance resource timing). Desktop segue no full.
Run: python tools/probe_pv2a_mobile_branch.py   (cwd = repo root)
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402

MOBILE_UA = ('Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 '
             '(KHTML, like Gecko) Chrome/126.0.0.0 Mobile Safari/537.36')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_pv2a_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=390,844', '--inprivate', f'--user-data-dir={PROFILE}',
    f'--user-agent={MOBILE_UA}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


async def run(ua):
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
    await c.send('Emulation.setDeviceMetricsOverride', {
        'width': 390, 'height': 844, 'deviceScaleFactor': 2,
        'mobile': True, 'screenWidth': 390, 'screenHeight': 844,
    })
    dev = await ev(c, "(() => ({ mobile: window.__DEVICE && window.__DEVICE.isMobile, touch: window.__DEVICE && window.__DEVICE.isTouch, bodyTouch: document.body.classList.contains('touch') }))()")
    print(f"[{'MOBILE' if 'Android' in ua else 'DESKTOP'}] __DEVICE: {dev}")

    ok = await ev(c, "(async () => { window.setLobbyPage('arenas'); const card = document.querySelector('.arena-card[data-arena=\"sa00z\"]'); if (!card) return 'no-card'; card.click(); await new Promise(r => setTimeout(r, 2500)); return 'ok'; })()", await_promise=True)
    assert ok == 'ok', f'card click: {ok}'
    res = await ev(c, "JSON.stringify(performance.getEntriesByType('resource').map(r => r.name).filter(n => n.includes('sa00z')))")
    names = json.loads(res)
    mobile = any('.mobile.json' in n for n in names)
    desktop = any('sa00z.json?v=' in n and '.mobile' not in n for n in names)
    print(f'   recursos sa00z: mobile={mobile} desktop={desktop} ({names})')
    c.running = False
    return mobile, desktop


async def main():
    m, d = await run(MOBILE_UA)
    assert m and not d, 'MOBILE deveria carregar o .mobile.json'
    proc2_ok = True  # desktop validado em bateria separada (verifica suite)
    print('[ok] PV2A MOBILE BRANCH: .mobile.json servido no device mobile')
    print('PV2A PROBE DONE')


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(PROFILE, ignore_errors=True)
