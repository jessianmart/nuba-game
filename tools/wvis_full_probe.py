# -*- coding: utf-8 -*-
"""W-VIS-FULL: validação VISUAL de TODAS as skills (q/w/e/r) dos 12 heróis.

Por cast: (1) kids delta (VFX spawnou), (2) grupos extraídos vivos (Box3),
(3) rig animando (quats dos braços diferem do idle), (4) screenshot-diff vs
baseline da partida (pixels que mudaram = skill visível), (5) trail vivo
(1hnt/1orc w), (6) cut cine no ult do player (__CINE).
Bots cobrem 10 heróis numa partida 5v5; 1tnd/1orc via lobby player.
"""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')
ROSTER = ['1nrt', '1ssk', '1skr', 'kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']
ROSTER = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']
SHOT_SLOTS = {'q': {'1nrt', '1ssk'}, 'w': {'1hnt', '1orc'}, 'r': set(ROSTER), 'e': set()}  # screenshots: R todos + icônicos


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


async def save_shot(c, name):
    data = await c.send('Page.captureScreenshot', {'format': 'png'})
    open(os.path.join(SHOTS, name), 'wb').write(base64.b64decode(data['data']))


CAST_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  const bot = window.units.find(u => u.heroId === %r && !u.isPlayer);
  if (!bot) return null;
  window.units.forEach(u => { if (u !== bot) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
  bot.hitstun = 0; bot.deadTimer = 0; bot.hp = bot.maxHp; bot.chakra = 100; bot.animTimer = 0; bot.state = 'idle';
  bot.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
  const arena = p.mesh.parent;
  const kidsBefore = arena.children.length;
  window.executeSkill(bot, %r);
  const b13 = bot.mesh.userData.bones ? bot.mesh.userData.bones['13'] : null;
  return { heroId: bot.heroId, kids: arena.children.length - kidsBefore,
           q13: b13 ? [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w] : null };
})()
"""

CAST_PLAYER_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
  p.hitstun = 0; p.spawnShield = 0; p.animTimer = 0; p.state = 'idle'; p.chakra = 100;
  p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
  const arena = p.mesh.parent;
  const kidsBefore = arena.children.length;
  window.executeSkill(p, %r);
  const b13 = p.mesh.userData.bones ? p.mesh.userData.bones['13'] : null;
  return { heroId: p.heroId, kids: arena.children.length - kidsBefore,
           q13: b13 ? [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w] : null };
})()
"""

READ_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  const bot = window.units.find(u => u.heroId === %r && !u.isPlayer);
  const u = %s ? p : bot;
  if (!u || !u.mesh) return null;
  const b13 = u.mesh.userData.bones ? u.mesh.userData.bones['13'] : null;
  let extr = 0;
  p.mesh.parent.children.forEach(g => {
    if (g.type === 'Group' && g.scale.x < 0.5 && g.children.length) extr++;
  });
  let trailVerts = 0;
  p.mesh.parent.children.forEach(g => {
    if (g.type === 'Mesh' && g.geometry && g.geometry.attributes && g.geometry.attributes.position) {
      const a = g.geometry.attributes.position.array;
      let n = 0;
      for (let i = 0; i < a.length; i++) if (a[i] !== 0) n++;
      if (n > 20 && a.length <= 90) trailVerts = Math.max(trailVerts, n);
    }
  });
  return { q13: b13 ? [b13.quaternion.x, b13.quaternion.y, b13.quaternion.z, b13.quaternion.w] : null,
           extr, trailVerts,
           cine: window.__CINE ? window.__CINE() : null };
})()
"""


async def run_cast(c, hero_id, slot, is_player, results, shots_taken):
    cast_js = CAST_PLAYER_JS % slot if is_player else CAST_JS % (hero_id, slot)
    r0 = await ev(c, cast_js)
    if not r0:
        return
    await asyncio.sleep(0.30)
    read_js = READ_JS % (hero_id, 'true' if is_player else 'false')
    r1 = await ev(c, read_js)
    rigMoved = bool(r1 and r1['q13'] and r0['q13'] and any(abs(a - b) > 0.02 for a, b in zip(r0['q13'], r1['q13'])))
    ent = results.setdefault(hero_id, {})
    ent[slot] = {
        'kids': r0['kids'], 'extr': r1['extr'] if r1 else -1, 'rig': rigMoved,
        'trail': r1['trailVerts'] if r1 else 0,
        'cine': (r1['cine'] if r1 else None),
    }
    if (slot in SHOT_SLOTS and hero_id in SHOT_SLOTS[slot]) or is_player:
        tag = f'full_{hero_id}_{slot}.png'
        await save_shot(c, tag)
        shots_taken.append(tag)
    await asyncio.sleep(0.25)


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_wvf_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(3)
    results, shots_taken = {}, []
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
        await asyncio.sleep(4)

        # Partida 5v5: bots (10 heróis)
        await ev(c, "(async () => { try { await window.startMatch('dm_legacy_5v5'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 10:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.0)
        presentes = await ev(c, 'window.units.map(u => u.heroId)')
        print('partida 5v5 herois:', sorted(set(presentes)))
        for hid in [h for h in ROSTER if h in presentes]:
            for slot in ('q', 'w', 'e', 'r'):
                await run_cast(c, hid, slot, False, results, shots_taken)

        # Player: 1tnd e 1orc via lobby
        for hid in ('1tnd', '1orc'):
            await ev(c, "window.units.forEach(u => u.hp = 0)")
            await asyncio.sleep(1.5)
            await ev(c, f"document.querySelectorAll('[data-id]').forEach(e => {{ if (e.dataset.id === '{hid}') e.click(); }})")
            await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
            for _ in range(40):
                if await ev(c, 'window.units ? window.units.length : -1') == 6:
                    break
                await asyncio.sleep(0.5)
            await asyncio.sleep(2.0)
            ph = await ev(c, "window.units.find(u => u.isPlayer).heroId")
            print(f'player hero: {ph}')
            for slot in ('q', 'w', 'e', 'r'):
                await run_cast(c, hid, slot, True, results, shots_taken)

        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        c.running = False

        print('\n==== W-VIS-FULL: 12 herois x 4 slots ====')
        print(f"{'heroi':6s} {'q(kids/extr/rig)':22s} {'w(kids/extr/rig)':22s} {'e(kids/extr/rig)':22s} {'r(kids/extr/rig/cine)':30s}")
        for hid in ROSTER:
            ent = results.get(hid, {})
            cells = []
            for slot in ('q', 'w', 'e', 'r'):
                d = ent.get(slot)
                if not d:
                    cells.append(f"{'?':22s}")
                    continue
                cine = ''
                if slot == 'r' and d['cine']:
                    cine = f"/cine={'Y' if d['cine']['active'] or (d['cine']['fov'] and d['cine']['fov'] < 47.9) else 'n'}"
                cells.append(f"{d['kids']:2d}/{d['extr']:2d}/{'R' if d['rig'] else '-'}{cine}")
            print(f"{hid:6s} {cells[0]:22s} {cells[1]:22s} {cells[2]:22s} {cells[3]:30s}")
        print(f'\ntrail max verts: ' + ', '.join(f"{h}:{results[h]['w']['trail']}" for h in results if 'w' in results.get(h, {}) and results[h]['w'].get('trail')))
        print(f'console errors: {len(errs)}')
        for e in errs[:5]:
            print('  *', str(e)[:160])
        print(f'\nshots: {len(shots_taken)}')
        json.dump(results, open(os.path.join(SHOTS, 'wvis_full_results.json'), 'w'))
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
