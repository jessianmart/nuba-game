"""Screenshot da vila MOBILE (sa00z.mobile.json) — intercepta o fetch no CDP
e serve o JSON otimizado na URL do original, sem tocar em disco.
Run: python tools/probe_vila_shot_mobile.py   (cwd = repo root)
"""
import asyncio
import base64
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

OUT = os.path.join(os.environ.get('TMPDIR', tempfile.gettempdir()), 'nuba_vila_mobile_shot.png')
MOBILE_JSON = os.path.join(os.getcwd(), 'public', 'assets', 'stage', 'arena', 'sa00z.mobile.json')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_vilam_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1600,900', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


def http_json(path):
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json('/json')
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()

    # intercepta o fetch do arena JSON e serve o mobile
    with open(MOBILE_JSON, 'rb') as f:
        body_b64 = base64.b64encode(f.read()).decode()
    await c.send('Fetch.enable', {
        'patterns': [{'urlPattern': '*sa00z.json*', 'requestStage': 'Request'}]
    })

    async def fulfil(evt):
        p = evt.get('params', {})
        if p.get('responseStatusCode') or p.get('responseErrorReason'):
            return
        try:
            await c.send('Fetch.fulfillRequest', {
                'requestId': p['requestId'],
                'responseCode': 200,
                'responseHeaders': [{'name': 'Content-Type', 'value': 'application/json'}],
                'body': body_b64,
            })
        except Exception as e:
            print('   fulfil fail:', e)

    c.on('Fetch.requestPaused', lambda evt: asyncio.ensure_future(fulfil(evt)))

    ok = await ev(c, "(async () => { window.setLobbyPage('arenas'); const card = document.querySelector('.arena-card[data-arena=\"sa00z\"]'); if (!card) return 'no-card'; card.click(); await new Promise(r => setTimeout(r, 3000)); return 'ok'; })()", await_promise=True)
    assert ok == 'ok', f'card click: {ok}'
    served = await ev(c, "(() => { try { const r = window.__lastStageMeshes; return r || 0; } catch (e) { return -1; } })()")
    print('[1] arena mobile servida via intercept; card ok')

    await ev(c, "(async () => { try { await window.start5v5Match(); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    n = -1
    for _ in range(80):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 10:
            break
        await asyncio.sleep(0.5)
    assert n == 10, f'unidades: {n}'
    await asyncio.sleep(4)

    shot = await c.send('Page.captureScreenshot', {'format': 'png'})
    with open(OUT, 'wb') as f:
        f.write(base64.b64decode(shot['data']))
    size_kb = os.path.getsize(OUT) // 1024
    errs = list(c.console_errors)
    print(f'[2] screenshot mobile: {OUT} ({size_kb} KB) — console errors: {len(errs)}')
    for e in errs[:4]:
        print('   err:', e)
    print('VILA MOBILE SHOT DONE')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(PROFILE, ignore_errors=True)
