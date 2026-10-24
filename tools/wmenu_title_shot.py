# -*- coding: utf-8 -*-
"""W-MENU T1b: screenshot da tela-titulo no estado boot (revisao estetica)."""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_titleshot_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(3)
    try:
        tabs = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json') as r:
                    tabs = json.load(r)
                break
            except Exception:
                time.sleep(0.5)
        ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws)
        await c.connect()
        for _ in range(60):
            if await c.eval_js('typeof window.__TITLE_DISMISSED') == 'undefined' and await c.eval_js('window.__ajustesReady === true'):
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.2)  # animacoes de entrada acomodando
        d = await c.send('Page.captureScreenshot', {'format': 'png'})
        fp = os.path.join(SHOTS, 'wmenu_title_boot.png')
        open(fp, 'wb').write(base64.b64decode(d['data']))
        r = await c.eval_js("(() => ({ active: document.getElementById('title-screen').classList.contains('active') }))()")
        print('shot salvo | title ativo:', r['active'], '|', fp)
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
