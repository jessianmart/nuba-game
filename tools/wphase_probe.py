# -*- coding: utf-8 -*-
"""W-VFX-SEQ: valida os emissores por fase. Cast -> mede spawns extras no tempo,
pendingVfxPhases consumido, 0 console errors. Prints do W (puffs de clones)."""
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
    profile = tempfile.mkdtemp(prefix='nuba_wph_')
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

        for slot, wait in (('q', 0.9), ('w', 1.1), ('r', 1.4)):
            await ev(c, f"""
            (() => {{
              const p = window.units.find(u => u.isPlayer);
              window.units.forEach(u => {{ if (!u.isPlayer) {{ u.cds = {{ atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }}; u.chakra = 0; }} }});
              p.hitstun = 0; p.animTimer = 0; p.state = 'idle'; p.chakra = 100;
              p.cds = {{ atk: 0, q: 0, w: 0, e: 0, r: 0 }};
              window.cameraMode = 'free';
              window.camera.position.set(p.x - 2.5, 3.0, p.z + 7.0);
              window.camera.lookAt(p.x, 1.8, p.z - 1.5);
              window.executeSkill(p, '{slot}');
              return true;
            }})()
            """)
            if slot == 'w':
                await asyncio.sleep(0.25)
                d1 = await c.send('Page.captureScreenshot', {'format': 'png'})
                open(os.path.join(SHOTS, 'wphase_1nrt_w_mid.png'), 'wb').write(base64.b64decode(d1['data']))
                await asyncio.sleep(0.35)
            else:
                await asyncio.sleep(wait)
            r = await ev(c, """
            (() => {
              const p = window.units.find(u => u.isPlayer);
              return { pending: p.pendingVfxPhases ? p.pendingVfxPhases.length : 0,
                       state: p.state, animTimer: +p.animTimer.toFixed(2) };
            })()
            """)
            d2 = await c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(SHOTS, f'wphase_1nrt_{slot}.png'), 'wb').write(base64.b64decode(d2['data']))
            print(f"1nrt.{slot}: pending={r['pending']} state={r['state']} shot salvo")
            await asyncio.sleep(0.4)

        # bots: 1skr q (leg01), 1roc q (leaf_flurry), 1gar q (snd15)
        await ev(c, "(async () => { try { await window.startMatch('dm_legacy_5v5'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 10:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.0)
        for hid, slot in (('1skr', 'q'), ('1roc', 'q'), ('1gar', 'q')):
            await ev(c, f"""
            (() => {{
              const bot = window.units.find(u => u.heroId === '{hid}' && !u.isPlayer);
              if (!bot) return false;
              window.units.forEach(u => {{ if (u !== bot) {{ u.cds = {{ atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }}; u.chakra = 0; }} }});
              bot.hitstun = 0; bot.animTimer = 0; bot.state = 'idle'; bot.chakra = 100; bot.hp = bot.maxHp;
              bot.cds = {{ atk: 0, q: 0, w: 0, e: 0, r: 0 }};
              window.cameraMode = 'free';
              window.camera.position.set(bot.x - 2.0, 3.0, bot.z + 7.0);
              window.camera.lookAt(bot.x, 1.6, bot.z - 1.0);
              window.executeSkill(bot, '{slot}');
              return true;
            }})()
            """)
            await asyncio.sleep(1.1)
            r = await ev(c, f"""
            (() => {{
              const bot = window.units.find(u => u.heroId === '{hid}' && !u.isPlayer);
              return {{ pending: bot.pendingVfxPhases ? bot.pendingVfxPhases.length : 0, state: bot.state }};
            }})()
            """)
            d = await c.send('Page.captureScreenshot', {'format': 'png'})
            open(os.path.join(SHOTS, f'wphase_{hid}_{slot}.png'), 'wb').write(base64.b64decode(d['data']))
            print(f"{hid}.{slot}: pending={r['pending']} state={r['state']} shot salvo")

        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
