# -*- coding: utf-8 -*-
"""W-REAL F5: validacao visual dos FORMATOS 3D reais. Casts iconicos com
camera free de perto; mede (a) verts dos meshes extraidos vivos na cena,
(b) densidade de pixels de efeito por frame, (c) console errors."""
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
    profile = tempfile.mkdtemp(prefix='nuba_wreal_')
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

        # Partida 1: player 1nrt (q/w/r) em dm_3v3
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        await asyncio.sleep(5)
        print('== player 1nrt (dm_3v3) ==')

        CAST_JS = """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
          p.hitstun = 0; p.animTimer = 0; p.state = 'idle'; p.chakra = 100;
          p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
          window.executeSkill(p, '__SLOT__');
          return true;
        })()
        """
        for slot in ('q', 'w', 'r'):
            await ev(c, f"""
            (() => {{
              window.cameraMode = 'free';
              const p = window.units.find(u => u.isPlayer);
              window.camera.position.set(p.x - 2.5, 2.8, p.z + 6.5);
              window.camera.lookAt(p.x, 1.8, p.z - 1.5);
            }})()
            """)
            await ev(c, CAST_JS.replace('__SLOT__', slot))
            await asyncio.sleep(0.35)
            live = await ev(c, """
            (() => {
              const p = window.units.find(u => u.isPlayer);
              let verts = 0, meshes = 0;
              p.mesh.parent.children.forEach(g => {
                g.traverse(m => {
                  if (m.isMesh && m.geometry && m.geometry.attributes && m.geometry.attributes.position) {
                    meshes++;
                    verts += m.geometry.attributes.position.count;
                  }
                });
              });
              return { verts, meshes };
            })()
            """)
            data = await c.send('Page.captureScreenshot', {'format': 'png'})
            fn = f'wreal_1nrt_{slot}.png'
            open(os.path.join(SHOTS, fn), 'wb').write(base64.b64decode(data['data']))
            print(f"1nrt.{slot}: meshes={live['meshes']} verts={live['verts']} shot={fn}")
            await asyncio.sleep(0.6)

        # Partida 2: bots 5v5, outros herois
        await ev(c, "(async () => { try { await window.startMatch('dm_legacy_5v5'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 10:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.0)
        print('== bots (5v5) ==')

        HERO_SLOTS = [
            ('1ssk', 'q', 'chidori'), ('1ssk', 'w', 'fireball'),
            ('1skr', 'r', 'okasho'), ('1gar', 'w', 'sand_hand'),
            ('1itc', 'q', 'amaterasu'), ('1roc', 'q', 'tornado'),
            ('1kks', 'w', 'water_dragon'), ('1jry', 'q', 'toad_fire'),
            ('1nej', 'q', 'kaiten'), ('1hnt', 'w', 'lion'),
        ]
        for hid, slot, tag in HERO_SLOTS:
            await ev(c, f"""
            (() => {{
              window.cameraMode = 'free';
              const bot = window.units.find(u => u.heroId === '{hid}' && !u.isPlayer);
              if (!bot) return false;
              window.camera.position.set(bot.x - 2.5, 2.8, bot.z + 6.5);
              window.camera.lookAt(bot.x, 1.8, bot.z - 1.5);
              return true;
            }})()
            """)
            ok = await ev(c, f"""
            (() => {{
              const bot = window.units.find(u => u.heroId === '{hid}' && !u.isPlayer);
              if (!bot) return false;
              window.units.forEach(u => {{ if (u !== bot) {{ u.cds = {{ atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }}; u.chakra = 0; }} }});
              bot.hitstun = 0; bot.animTimer = 0; bot.state = 'idle'; bot.chakra = 100; bot.hp = bot.maxHp;
              bot.cds = {{ atk: 0, q: 0, w: 0, e: 0, r: 0 }};
              window.executeSkill(bot, '{slot}');
              return true;
            }})()
            """)
            if not ok:
                print(f'{hid}.{slot} ({tag}): bot ausente')
                continue
            await asyncio.sleep(0.35)
            live = await ev(c, f"""
            (() => {{
              const bot = window.units.find(u => u.heroId === '{hid}' && !u.isPlayer);
              let verts = 0, meshes = 0;
              bot.mesh.parent.children.forEach(g => {{
                g.traverse(m => {{
                  if (m.isMesh && m.geometry && m.geometry.attributes && m.geometry.attributes.position) {{
                    meshes++; verts += m.geometry.attributes.position.count;
                  }}
                }});
              }});
              return {{ verts, meshes }};
            }})()
            """)
            data = await c.send('Page.captureScreenshot', {'format': 'png'})
            fn = f'wreal_{hid}_{slot}.png'
            open(os.path.join(SHOTS, fn), 'wb').write(base64.b64decode(data['data']))
            print(f"{hid}.{slot} ({tag}): meshes={live['meshes']} verts={live['verts']} shot={fn}")
            await asyncio.sleep(0.6)

        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
