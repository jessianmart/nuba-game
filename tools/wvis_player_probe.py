# -*- coding: utf-8 -*-
"""W-VIS-ALL player probe: cobre 1tnd e 1orc via selecao de lobby (click na
collection-card) + cast do PLAYER. Mede kids/handVfx/extents + screenshot do
1orc q (modelo novo extraido)."""
import asyncio, base64, io as _io, json, os, shutil, socket, subprocess, sys, tempfile, time
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
    profile = tempfile.mkdtemp(prefix='nuba_wvp_')
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
        # aquecimento anti-Defender
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        await asyncio.sleep(4)

        for hid in ('1tnd', '1orc'):
            await ev(c, "window.units && window.units.forEach(u => u.hp = 0)")  # força fim
            await asyncio.sleep(1.0)
            await ev(c, f"document.querySelectorAll('[data-id]').forEach(e => {{ if (e.dataset.id === '{hid}') e.click(); }})")
            sel = await ev(c, 'window.selectedHeroId')
            print(f'{hid}: selectedHeroId = {sel}')
            ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
            assert ok == 'ok', ok
            for _ in range(40):
                n = await ev(c, 'window.units ? window.units.length : -1')
                if n == 6:
                    break
                await asyncio.sleep(0.5)
            await asyncio.sleep(2.0)
            ph = await ev(c, "window.units.find(u => u.isPlayer) ? window.units.find(u => u.isPlayer).heroId : null")
            print(f'{hid}: player heroId = {ph}')
            for slot in ('q', 'w', 'r'):
                r0 = await ev(c, f"""
                (() => {{
                  const p = window.units.find(u => u.isPlayer);
                  window.units.forEach(u => {{ if (!u.isPlayer) {{ u.cds = {{ atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }}; u.chakra = 0; }} }});
                  p.hitstun = 0; p.spawnShield = 0; p.animTimer = 0; p.chakra = 100;
                  p.cds = {{ atk: 0, q: 0, w: 0, e: 0, r: 0 }};
                  const kb = p.mesh.parent.children.length;
                  window.executeSkill(p, '{slot}');
                  return {{ kb, ka: p.mesh.parent.children.length, hand: window.__HAND_VFX ? window.__HAND_VFX() : -1 }};
                }})()
                """)
                await asyncio.sleep(0.18)
                ext = await ev(c, """
                (() => {
                  const p = window.units.find(u => u.isPlayer);
                  const out = [];
                  p.mesh.parent.children.forEach(g => {
                    if (g.type === 'Group' && g.scale.x < 0.5 && g.children.length) {
                      const b = new THREE.Box3().setFromObject(g);
                      out.push({ s: +g.scale.x.toFixed(4), ext: [+(b.max.x-b.min.x).toFixed(2), +(b.max.y-b.min.y).toFixed(2), +(b.max.z-b.min.z).toFixed(2)] });
                    }
                  });
                  return { n: out.length, groups: out };
                })()
                """)
                print(f"  {hid}.{slot}: kids=+{r0['ka']-r0['kb']} hand={r0['hand']} extGroups={ext['n']} {json.dumps(ext['groups'][:4])}")
                if hid == '1orc' and slot == 'q':
                    data = await c.send('Page.captureScreenshot', {'format': 'png'})
                    shot = os.path.join(SHOTS, 'wva_orc_q.png')
                    _io.open(shot, 'wb').write(base64.b64decode(data['data']))
                    print(f'  shot: wva_orc_q.png')
        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors (nao-webp): {len(errs)}')
        for e in errs[:4]:
            print('  *', str(e)[:180])
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
