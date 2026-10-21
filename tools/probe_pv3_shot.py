"""Screenshot mobile com o governor ativo (dpr 1.25) + validacao numerica.
Run: python tools/probe_pv3_shot.py   (cwd = repo root)
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

IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')


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
PROFILE = tempfile.mkdtemp(prefix='nuba_pv3shot_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=844,390', '--inprivate', f'--user-data-dir={PROFILE}', 'about:blank'
])
time.sleep(3)
OUT = os.environ.get('TEMP', '/tmp') + '/nuba_pv3_mobile.png'


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
    await c.send("Emulation.setUserAgentOverride", {"userAgent": IPHONE_UA, "platform": "iPhone"})
    await c.send("Emulation.setDeviceMetricsOverride", {"width": 844, "height": 390, "deviceScaleFactor": 1, "mobile": True})
    await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
    for _ in range(40):
        if await ev(c, 'typeof window.startMatch') == 'function':
            break
        await asyncio.sleep(0.5)
    await ev(c, "document.body.classList.add('touch')")
    await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    for _ in range(30):
        if await ev(c, 'window.units ? window.units.length : -1') == 6:
            break
        await asyncio.sleep(0.3)
    await asyncio.sleep(1.2)
    shot = await c.send("Page.captureScreenshot", {"format": "png"})
    img = base64.b64decode(shot.get("data") or shot.get("result", {}).get("data"))
    open(OUT, 'wb').write(img)
    gov = await ev(c, "({ gov: window.__GOV, vfx: window.__PERF.snapshot().vfx, units: window.units.length })")
    print(f'frame: {OUT} ({len(img)} bytes)')
    print(f'estado: {gov}')
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

# validacao numerica (nao posso "ver" o frame): dimensoes + diversidade de cor
from PIL import Image  # noqa: E402
im = Image.open(OUT).convert('RGB')
small = im.resize((64, 32))
colors = len(set(small.getdata()))
print(f'validacao: {im.width}x{im.height} | cores unicas (64x32 downsample)={colors}')
assert im.width >= 800 and im.height >= 380, 'frame com dimensoes erradas'
assert colors > 200, f'frame suspeito (poucas cores: {colors}) — possivel tela preta'
print('PV3 SHOT OK')
