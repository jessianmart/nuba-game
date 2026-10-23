# -*- coding: utf-8 -*-
"""W-VIS-FULL fix: castar 1nrt como PLAYER (default lobby) q/w/e/r + re-amostrar
1skr r (rig) com 2 instantes. Completa a grade 12x4."""
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
    profile = tempfile.mkdtemp(prefix='nuba_wvfx_')
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
        print('player hero:', await ev(c, "window.units.find(u => u.isPlayer).heroId"))

        # 1nrt como player: q/w/e/r
        for slot in ('q', 'w', 'e', 'r'):
            r0 = await ev(c, f"""
            (() => {{
              const p = window.units.find(u => u.isPlayer);
              window.units.forEach(u => {{ if (!u.isPlayer) {{ u.cds = {{ atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }}; u.chakra = 0; }} }});
              p.hitstun = 0; p.spawnShield = 0; p.animTimer = 0; p.state = 'idle'; p.chakra = 100;
              p.cds = {{ atk: 0, q: 0, w: 0, e: 0, r: 0 }};
              const kb = p.mesh.parent.children.length;
              const b13 = p.mesh.userData.bones['13'];
              window.executeSkill(p, '{slot}');
              return {{ kids: p.mesh.parent.children.length - kb, q13: [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w] }};
            }})()
            """)
            await asyncio.sleep(0.30)
            r1 = await ev(c, """
            (() => {
              const p = window.units.find(u => u.isPlayer);
              let extr = 0;
              p.mesh.parent.children.forEach(g => { if (g.type === 'Group' && g.scale.x < 0.5 && g.children.length) extr++; });
              const b13 = p.mesh.userData.bones['13'];
              return { extr, q13: [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w], cine: window.__CINE() };
            })()
            """)
            rig = any(abs(a - b) > 0.02 for a, b in zip(r0['q13'], r1['q13']))
            print(f"1nrt.{slot}: kids={r0['kids']} extr={r1['extr']} rig={'R' if rig else '-'} cine={'Y' if slot=='r' and (r1['cine']['active'] or r1['cine']['fov']<47.9) else 'n'}")
            if slot == 'r':
                data = await c.send('Page.captureScreenshot', {'format': 'png'})
                open(os.path.join(SHOTS, 'full_1nrt_r.png'), 'wb').write(base64.b64decode(data['data']))
                print('  shot: full_1nrt_r.png')
            await asyncio.sleep(0.3)

        # 1skr r re-amostra (2 instantes)
        await ev(c, "(async () => { try { await window.startMatch('dm_legacy_5v5'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 10:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.0)
        r0 = await ev(c, """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          const bot = window.units.find(u => u.heroId === '1skr' && !u.isPlayer);
          window.units.forEach(u => { if (u !== bot) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
          bot.hitstun = 0; bot.animTimer = 0; bot.state = 'idle'; bot.chakra = 100; bot.hp = bot.maxHp;
          bot.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
          const kb = p.mesh.parent.children.length;
          const b13 = bot.mesh.userData.bones['13'];
          window.executeSkill(bot, 'r');
          return { kids: p.mesh.parent.children.length - kb, q13: [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w] };
        })()
        """)
        s1 = await ev(c, """
        (() => { const b = window.units.find(u => u.heroId === '1skr' && !u.isPlayer).mesh.userData.bones['13'];
          return [b.quaternion.x, b.quaternion.y, b.quaternion.z, b.quaternion.w]; })()
        """)
        await asyncio.sleep(0.35)
        s2 = await ev(c, """
        (() => { const b = window.units.find(u => u.heroId === '1skr' && !u.isPlayer).mesh.userData.bones['13'];
          return [b.quaternion.x, b.quaternion.y, b.quaternion.z, b.quaternion.w]; })()
        """)
        rig1 = any(abs(a - b) > 0.02 for a, b in zip(r0['q13'], s1))
        rig2 = any(abs(a - b) > 0.02 for a, b in zip(s1, s2))
        print(f"1skr.r (re): kids={r0['kids']} rig@0.30={'R' if rig1 else '-'} rig@0.65={'R' if rig2 else '-'}")
        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
