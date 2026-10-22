# -*- coding: utf-8 -*-
"""W-SKL probe: valida as coreografias completas das skills em runtime.

Player 1nrt (default) casta Q/W/R; depois troca pra 1orc via lobby e casta W/R.
Em cada cast: amostra quats do brao direito (bone 13) em 2 instantes do
animTimer -> se difere, o clip anima (nao congela). 0 console errors exigido.
"""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path


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


RIG_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  if (!p || !p.mesh || !p.mesh.userData.bones) return null;
  const b13 = p.mesh.userData.bones['13'];
  const b9 = p.mesh.userData.bones['9'];
  return { st: p.state, at: +(p.animTimer || 0).toFixed(3),
           q13: b13 ? [+b13.quaternion.x.toFixed(4), +b13.quaternion.y.toFixed(4), +b13.quaternion.z.toFixed(4), +b13.quaternion.w.toFixed(4)] : null,
           q9: b9 ? [+b9.quaternion.x.toFixed(4), +b9.quaternion.y.toFixed(4), +b9.quaternion.z.toFixed(4), +b9.quaternion.w.toFixed(4)] : null };
})()
"""

CAST_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
  p.hitstun = 0; p.spawnShield = 0; p.chakra = 100;
  p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
  window.executeSkill(p, %r);
  return p.state;
})()
"""


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_wskl_')
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

        for hid in ('1nrt', '1orc'):
            if hid != '1nrt':
                await ev(c, "window.units && window.units.forEach(u => u.hp = 0)")
                await asyncio.sleep(1.5)
                await ev(c, f"document.querySelectorAll('[data-id]').forEach(e => {{ if (e.dataset.id === '{hid}') e.click(); }})")
                await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
                for _ in range(40):
                    if await ev(c, 'window.units ? window.units.length : -1') == 6:
                        break
                    await asyncio.sleep(0.5)
                await asyncio.sleep(2.0)
            slots = ('q', 'w', 'r') if hid == '1nrt' else ('w', 'r')
            for slot in slots:
                st = await ev(c, CAST_JS % slot)
                a = await ev(c, RIG_JS)
                await asyncio.sleep(0.30)
                b = await ev(c, RIG_JS)
                anima = a and b and (a['q13'] != b['q13'] or a['q9'] != b['q9'])
                # segunda amostra mais tarde pra clips longos
                await asyncio.sleep(0.35)
                d = await ev(c, RIG_JS)
                anima2 = b and d and (b['q13'] != d['q13'] or b['q9'] != d['q9'])
                print(f"{hid}.{slot}: state={st} | anima(braço)={'SIM' if anima else 'NAO'} (e depois: {'SIM' if anima2 else 'NAO'})")
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
