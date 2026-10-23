# -*- coding: utf-8 -*-
"""W-CINE probe: valida o cut cinematográfico do ult do player (1nrt).
Mede __CINE durante o cast (active/b/fov/camY), screenshot no meio do cut,
retorno ao normal após o fim. 0 console errors."""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_wci_')
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
        for _ in range(40):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        await asyncio.sleep(5)

        # camera em modo MOBA: baseline
        base = await ev(c, 'window.__CINE ? window.__CINE() : null')
        print('baseline camera:', base)

        # cast do ult do player
        st = await ev(c, """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
          p.hitstun = 0; p.spawnShield = 0; p.chakra = 100;
          p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
          window.executeSkill(p, 'r');
          return p.state;
        })()
        """)
        await asyncio.sleep(0.45)
        mid = await ev(c, 'window.__CINE()')
        print(f'cast r: state={st} | meio do cut: {mid}')
        data = await c.send('Page.captureScreenshot', {'format': 'png'})
        shot = os.path.join(SHOTS, 'wcine_orc_mid.png')
        open(shot, 'wb').write(base64.b64decode(data['data']))
        print(f'  shot: wcine_orc_mid.png')
        await asyncio.sleep(0.4)
        late = await ev(c, 'window.__CINE()')
        print(f'tardia (blend decaindo): {late}')
        await asyncio.sleep(1.6)
        end = await ev(c, 'window.__CINE()')
        print(f'apos o ult: {end}')
        print('PASS' if (mid['active'] and mid['camY'] < 10 and mid['fov'] < 47.5 and end['fov'] >= 47.9 and not end['active']) else 'CHECK')
        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        for e in errs[:5]:
            print('  *', str(e)[:180])
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
