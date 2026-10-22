# -*- coding: utf-8 -*-
"""W-VIS-ALL probe: valida os VFX extraidos de TODOS os heróis do roster.

Para cada herói (bots de partidas dm_legacy_5v5, re-roll até cobrir os 12):
  cast q/w/r -> kids delta (grupo spawnou?) + extent WORLD dos grupos
  extraidos (Box3) + __HAND_VFX (binds) + console errors.
Screenshots dos casos criticos: 1orc q (modelo novo), 1ssk q (chidori mao),
1itc q (amaterasu chao), 1nej r (kaiten caster).
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')
ROSTER = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']
CRIT_SHOTS = {('1orc', 'q'): 'wva_orc_q.png', ('1ssk', 'q'): 'wva_ssk_q.png', ('1itc', 'q'): 'wva_itc_q.png', ('1nej', 'r'): 'wva_nej_r.png'}


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


CAST_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  const bot = window.units.find(u => u.heroId === %r && !u.isPlayer);
  if (!bot) return null;
  window.units.forEach(u => { if (u !== bot) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
  bot.hitstun = 0; bot.deadTimer = 0; bot.hp = bot.maxHp; bot.chakra = 100;
  bot.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
  const kidsBefore = p.mesh.parent.children.length;
  window.executeSkill(bot, %r);
  return { heroId: bot.heroId, slot: %r, kidsBefore, kidsAfter: p.mesh.parent.children.length,
           handVfx: (window.__HAND_VFX ? window.__HAND_VFX() : -1) };
})()
"""

EXTENT_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  const out = [];
  p.mesh.parent.children.forEach(g => {
    if (g.type === 'Group' && g.scale.x < 0.5 && g.children.length) {
      const b = new THREE.Box3().setFromObject(g);
      out.push({ s: +g.scale.x.toFixed(4),
                ext: [+(b.max.x - b.min.x).toFixed(2), +(b.max.y - b.min.y).toFixed(2), +(b.max.z - b.min.z).toFixed(2)],
                pos: [+g.position.x.toFixed(1), +g.position.y.toFixed(1), +g.position.z.toFixed(1)] });
    }
  });
  return { n: out.length, groups: out };
})()
"""


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_wva_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(3)
    results = {}
    errors_total = []
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
        # aquecimento anti-Defender: 1 partida curta descartada
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        await asyncio.sleep(4)

        for rodada in range(4):
            faltando = [h for h in ROSTER if h not in results]
            if not faltando:
                break
            ok = await ev(c, "(async () => { try { await window.startMatch('dm_legacy_5v5'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
            assert ok == 'ok', ok
            for _ in range(40):
                n = await ev(c, 'window.units ? window.units.length : -1')
                if n == 10:
                    break
                await asyncio.sleep(0.5)
            await asyncio.sleep(2.0)
            presentes = await ev(c, 'window.units.map(u => u.heroId)')
            print(f'--- partida {rodada + 1}: herois {sorted(set(presentes))} ---')
            for hid in [h for h in faltando if h in presentes]:
                for slot in ('q', 'w', 'r'):
                    r0 = await ev(c, CAST_JS % (hid, slot, slot))
                    if not r0:
                        continue
                    await asyncio.sleep(0.18)
                    ext = await ev(c, EXTENT_JS)
                    new_groups = [g for g in ext['groups'] if g not in []]
                    results.setdefault(hid, {})[slot] = {
                        'kids': r0['kidsAfter'] - r0['kidsBefore'],
                        'handVfx': r0['handVfx'],
                        'extN': ext['n'],
                    }
                    key = (hid, slot)
                    if key in CRIT_SHOTS:
                        data = await c.send('Page.captureScreenshot', {'format': 'png'})
                        import base64
                        shot = os.path.join(SHOTS, CRIT_SHOTS[key])
                        io = open(shot, 'wb')
                        io.write(base64.b64decode(data['data']))
                        io.close()
                        print(f'  shot: {CRIT_SHOTS[key]}')
                errs = list(getattr(c, 'console_errors', []))
                errors_total.extend(errs[-3:] if errs else [])
        c.running = False
        print('\n==== W-VIS-ALL PROBE RESULTS ====')
        for hid in ROSTER:
            r = results.get(hid)
            if not r:
                print(f'{hid}: NAO COBERTO')
                continue
            line = f"{hid}: "
            for slot in ('q', 'w', 'r'):
                d = r.get(slot)
                line += f"{slot}(kids={d['kids']},hand={d['handVfx']},ext={d['extN']}) " if d else f'{slot}=? '
            print(line)
        print(f'console errors novos (amostra): {len(errors_total)}')
        for e in errors_total[:6]:
            print('  *', str(e)[:200])
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
