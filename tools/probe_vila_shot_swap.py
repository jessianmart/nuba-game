"""Screenshot da vila MOBILE via swap em disco (restaura no finally, a prova de crash).
Backup: arena/sa00z.json.bak_desktop ; restauracao sempre ao fim.
Run: python tools/probe_vila_shot_swap.py   (cwd = repo root)
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

ROOT = os.getcwd()
DESKTOP = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sa00z.json')
MOBILE = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sa00z.mobile.json')
BAK = DESKTOP + '.bak_desktop'
OUT = os.path.join(os.environ.get('TMPDIR', tempfile.gettempdir()), 'nuba_vila_mobile_shot.png')


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


async def run_shot():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_vsw_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1600,900', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    try:
        time.sleep(3)
        tabs = None
        for _ in range(20):
            try:
                tabs = http_json(port, '/json')
                break
            except Exception:
                time.sleep(0.5)
        ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws_url)
        await c.connect()
        r = await ev(c, "(() => ({ n: (window.arenasCatalog||[]).length, has: !!(window.arenasCatalog||[]).find(a=>a.id==='sa00z') }) )()")
        assert r['has'] and r['n'] == 9, f'catalogo: {r}'
        await ev(c, "window.setLobbyPage('arenas')")
        await asyncio.sleep(0.4)
        ok = await ev(c, "(async () => { const card = document.querySelector('.arena-card[data-arena=\"sa00z\"]'); if (!card) return 'no-card'; card.click(); await new Promise(r => setTimeout(r, 2500)); return 'ok'; })()", await_promise=True)
        assert ok == 'ok', f'card click: {ok}'
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
        print(f'[mobile] screenshot: {OUT} ({os.path.getsize(OUT)//1024} KB) — console errors: {len(list(c.console_errors))}')
        for e in list(c.console_errors)[:4]:
            print('   err:', e)
        print('SWAP SHOT DONE')
        c.running = False
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        shutil.rmtree(profile, ignore_errors=True)


def main():
    if os.path.exists(BAK):
        # rodada anterior crashou antes de restaurar: recupera o desktop primeiro
        shutil.copy2(BAK, DESKTOP)
        os.remove(BAK)
        print('[swap] backup orfao de rodada anterior restaurado')
    shutil.copy2(DESKTOP, BAK)
    shutil.copy2(MOBILE, DESKTOP)
    print(f'[swap] desktop <- mobile ativo (backup em {os.path.basename(BAK)})')
    try:
        asyncio.run(run_shot())
    finally:
        shutil.copy2(BAK, DESKTOP)
        os.remove(BAK)
        print('[swap] desktop RESTAURADO')


if __name__ == '__main__':
    main()
