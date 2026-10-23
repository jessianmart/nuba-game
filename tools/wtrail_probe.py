# -*- coding: utf-8 -*-
"""W-TRAIL probe: valida (1) janela de ult casada ao clip (1nrt r -> 1.15,
1orc r -> 1.8) e (2) trail ribbon do W do Orochimaru vivo (skillTrails count,
geometry com vértices nao-nulos) + screenshot. 0 console errors."""
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
    profile = tempfile.mkdtemp(prefix='nuba_wtr_')
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

        CAST = """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
          p.hitstun = 0; p.spawnShield = 0; p.chakra = 100;
          p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
          window.executeSkill(p, %r);
          return { st: p.state, dur: +(p.animDuration || 0).toFixed(3) };
        })()
        """
        # 1. janela do ult do 1nrt (clip 63f@60 -> clamp baixo 1.15)
        r0 = await ev(c, CAST % 'r')
        print(f"1nrt r: state={r0['st']} animDuration={r0['dur']} (esperado 1.15)")
        await asyncio.sleep(1.6)

        # 2. troca pro 1orc
        await ev(c, "window.units.forEach(u => u.hp = 0)")
        await asyncio.sleep(1.5)
        await ev(c, "document.querySelectorAll('[data-id]').forEach(e => { if (e.dataset.id === '1orc') e.click(); })")
        await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.0)

        # 3. W do 1orc: trail vivo
        r1 = await ev(c, CAST % 'w')
        await asyncio.sleep(0.30)
        tr = await ev(c, """
        (() => {
          // skillTrails é module-scope: mede via cena (ribbon meshes additive no arenaGroup)
          const p = window.units.find(u => u.isPlayer);
          const arr = p.mesh.parent.children;
          let found = 0, nz = 0;
          arr.forEach(g => {
            if (g.type === 'Mesh' && g.geometry && g.geometry.attributes && g.geometry.attributes.position) {
              const a = g.geometry.attributes.position.array;
              let n = 0;
              for (let i = 0; i < a.length; i++) if (a[i] !== 0) n++;
              if (n > 20) { found++; nz = Math.max(nz, n); }
            }
          });
          return { found, nz };
        })()
        """)
        print(f"1orc w: state={r1['st']} | trail candidates={tr['found']} maxNonZeroVerts={tr['nz']}")
        shot = None
        data = await c.send('Page.captureScreenshot', {'format': 'png'})
        shot = os.path.join(SHOTS, 'wtrail_orc_w.png')
        open(shot, 'wb').write(base64.b64decode(data['data']))
        print(f'  shot: wtrail_orc_w.png')
        await asyncio.sleep(1.5)

        # 4. ult do 1orc: janela 1.8 (clip 146f@60=2.43 -> clamp alto)
        r2 = await ev(c, CAST % 'r')
        print(f"1orc r: state={r2['st']} animDuration={r2['dur']} (esperado 1.8)")

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
