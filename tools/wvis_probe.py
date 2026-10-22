# -*- coding: utf-8 -*-
"""W-VIS probe: a animacao do personagem E o VFX da skill estao VISIVEIS
durante o casting? Mede em runtime (dm_3v3, bots silenciados):
  - state/animTimer do player durante o cast (clip segura?)
  - boneHash (pos+quaternion de TODOS os bones) entre amostras -> rig anima?
  - filhos do grupo da cena (VFX spawns novos + posicoes vs player)
  - __PERF vfx count + __activeVfxModel
  - screenshots no MEIO do cast (Q e R)
Dump cru de console errors ao final (diagnostico do verify EXIT 1)."""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_wvis_')
SHOTS = r'C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch'
os.makedirs(SHOTS, exist_ok=True)
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

SAMPLE_JS = """
(() => {
  const p = window.units ? window.units.find(u => u.isPlayer) : null;
  if (!p) return { err: 'sem player' };
  const bones = (p.mesh && p.mesh.userData && p.mesh.userData.bones) ? p.mesh.userData.bones : null;
  let bh = 0, bn = 0, qh = 0;
  if (bones) {
    bn = bones.length;
    for (let i = 0; i < bn; i++) {
      const b = bones[i];
      bh += Math.round((b.position.x + b.position.y + b.position.z) * 1000);
      qh += Math.round((b.quaternion.x + b.quaternion.y + b.quaternion.z) * 1000);
    }
  }
  const perf = (window.__PERF && window.__PERF.snapshot) ? window.__PERF.snapshot() : null;
  let parent = null;
  if (p.mesh && p.mesh.parent) parent = { type: p.mesh.parent.type, children: p.mesh.parent.children.length };
  return {
    t: Math.round(performance.now()), state: p.state,
    animTimer: Math.round((p.animTimer || 0) * 1000) / 1000, animDur: p.animDuration,
    boneN: bn, boneHash: bh, quatHash: qh,
    vfxCount: perf ? perf.vfx : -1, parent: parent,
    px: Math.round(p.x), pz: Math.round(p.z)
  };
})()
"""

CAST_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
  p.hitstun = 0; p.spawnShield = 0; p.animTimer = 0;
  p.cds[__SLOT__] = 0; p.chakra = 100;
  const before = p.mesh.parent ? p.mesh.parent.children.length : -1;
  window.executeSkill(p, __SLOT__);
  return { slot: __SLOT__, state: p.state, animTimer: p.animTimer, animDur: p.animDuration,
           vfxModel: (window.__activeVfxModel ? window.__activeVfxModel() : null),
           kidsBefore: before, kidsAfter: p.mesh.parent ? p.mesh.parent.children.length : -1 };
})()
"""

TAIL_JS = """
(() => {
  const p = window.units.find(u => u.isPlayer);
  const parent = p.mesh && p.mesh.parent;
  if (!parent) return { err: 'sem parent' };
  const kids = parent.children;
  const out = [];
  for (let i = Math.max(0, kids.length - 8); i < kids.length; i++) {
    const k = kids[i];
    const kx = k.position ? k.position.x : 0, ky = k.position ? k.position.y : 0, kz = k.position ? k.position.z : 0;
    out.push({ i: i, type: k.type, name: (k.name || '').slice(0, 18),
      x: Math.round(kx * 10) / 10, y: Math.round(ky * 10) / 10, z: Math.round(kz * 10) / 10,
      distPlayer: Math.round(Math.hypot(kx - p.x, kz - p.z) * 10) / 10,
      ud: k.userData ? Object.keys(k.userData).slice(0, 5) : null, vis: k.visible });
  }
  return { n: kids.length, tail: out };
})()
"""


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    tabs = None
    for _ in range(20):
        try:
            with urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json') as r:
                tabs = json.load(r)
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()
    t = None
    for _ in range(40):
        t = await ev(c, 'typeof window.startMatch')
        if t == 'function':
            break
        await asyncio.sleep(0.5)
    assert t == 'function', f'boot incompleto: {t}'
    ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    n = -1
    for _ in range(40):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 6:
            break
        await asyncio.sleep(0.5)
    assert n == 6, f'unidades: {n}'
    print('partida dm_3v3 ativa (6 units)')

    base = await ev(c, SAMPLE_JS)
    print('baseline:', base)

    for slot, shot in (('q', 'wvis_q_mid.png'), ('r', 'wvis_r_mid.png')):
        r = await ev(c, CAST_JS.replace('__SLOT__', f"'{slot}'"))
        print(f'\n== CAST {slot.upper()} ==')
        print('  imediato:', r)
        for i in range(10):
            await asyncio.sleep(0.12)
            s = await ev(c, SAMPLE_JS)
            print(f"  t+{(i + 1) * 0.12:.2f}s state={s.get('state')} animTimer={s.get('animTimer')} boneH={s.get('boneHash')} quatH={s.get('quatHash')} vfx={s.get('vfxCount')} kids={s.get('parent', {}).get('children') if s.get('parent') else None}")
            if i == 2:
                shot_res = await c.send('Page.captureScreenshot', {'format': 'png'})
                with open(os.path.join(SHOTS, shot), 'wb') as f:
                    f.write(base64.b64decode(shot_res['data']))
                print(f'  screenshot: {shot}')
                tail = await ev(c, TAIL_JS)
                print('  tail do grupo da cena:', json.dumps(tail)[:600])
        await asyncio.sleep(2.0)  # cast expira, VFX somem

    print(f'\nconsole errors crus ({len(c.console_errors)}):')
    for e in c.console_errors[:12]:
        print('  *', str(e)[:300])
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    shutil.rmtree(PROFILE, ignore_errors=True)
