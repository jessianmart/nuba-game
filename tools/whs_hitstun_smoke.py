# -*- coding: utf-8 -*-
"""W-HS smoke — HITSTUN do APK Storm aplicado ao NUBA.
Valida end-to-end via CDP: (1) hit aplica hitstun; (2) cast BLOQUEADO durante
hitstun; (3) kawarimi (slot e, type kawarimi) LIBERADO (escape autentico);
(4) juggle: hit novo reseta; (5) morte nao e impedida; (6) decai em dt real.
Telemetria: window.__HITSTUN. Run: python tools/whs_hitstun_smoke.py
(cwd = repo root, :8080 dev server vivo)."""
import asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_whs_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


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

    # [1] boot-wait
    t = None
    for _ in range(40):
        t = await ev(c, 'typeof window.startMatch')
        if t == 'function':
            break
        await asyncio.sleep(0.5)
    assert t == 'function', f'boot incompleto: {t}'
    print('[1] boot game.js completo')

    # [2] partida 3v3 (menos bots = menos ruido) + silenciar IA (liicao M7)
    ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch dm_3v3: {ok}'
    n = -1
    for _ in range(40):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 6:
            break
        await asyncio.sleep(0.5)
    assert n == 6, f'unidades: {n}'
    print('[2] dm_3v3 ativa (6 units)')

    # [3] telemetria __HITSTUN
    cfg = await ev(c, 'window.__HITSTUN || null')
    assert cfg and abs(cfg['normal'] - 0.35) < 1e-6 and abs(cfg['heavy'] - 0.60) < 1e-6, f'__HITSTUN: {cfg}'
    print(f"[3] telemetria __HITSTUN = {{normal:{cfg['normal']}, heavy:{cfg['heavy']}}} (APK dmg0f 21f / hsta0 36f)")

    # [4] hit do player aplica hitstun no bot (cast+leitura NA MESMA expressao)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      if (!e) return { err: 'sem bot vivo' };
      // silencia IA: sem cds nem chakra (nao revida, nao reseta o timer do bot)
      window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
      e.spawnShield = 0;
      e.x = p.x + 1.5; e.z = p.z;
      e.hp = Math.max(e.hp, 400); // garante sobrevivencia (hitstun so se VIVO)
      p.cds.atk = 0;
      window.executeSkill(p, 'atk');
      return { hitstun: e.hitstun || 0, hp: e.hp, state: e.state };
    })()
    """)
    assert not r.get('err'), r
    assert r['hitstun'] >= 0.30, f'hitstun nao aplicado: {r}'
    print(f"[4] hit normal aplicou hitstun {r['hitstun']:.2f}s no bot (vivo, hp={r['hp']})")

    # [5] cast OFENSIVO bloqueado durante hitstun (mesma expressao = atomico)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      e.hitstun = 0.35; e.cds.q = 0; e.chakra = 100; e.spawnShield = 0;
      const ck = e.chakra;
      window.executeSkill(e, 'q');
      return { cdsQ: e.cds.q, chakraGasto: ck - e.chakra, hitstun: e.hitstun };
    })()
    """)
    assert r['cdsQ'] == 0 and r['chakraGasto'] == 0, f'cast Q nao foi bloqueado: {r}'
    print(f"[5] cast Q do bot BLOQUEADO no hitstun (cd continua 0, chakra intacto)")

    # [6] kawarimi LIBERADO durante hitstun (escape do Storm, custa chakra)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      e.hitstun = 0.35; e.cds.e = 0; e.chakra = 100;
      window.executeSkill(e, 'e');
      return { cdsE: e.cds.e, type: e.kit.e ? e.kit.e.type : null, hitstun: e.hitstun, pHitstun: p.hitstun || 0, pDist: Math.round(Math.hypot(e.x - p.x, e.z - p.z) * 10) / 10 };
    })()
    """)
    assert r['type'] == 'kawarimi', f'slot e nao e kawarimi neste kit: {r}'
    assert r['cdsE'] > 0, f'kawarimi bloqueado durante hitstun: {r}'
    print(f"[6] kawarimi LIBERADO no hitstun (cast passou, cd={r['cdsE']:.1f}s) — escape autentico")

    # [7] juggle: hit novo RESETA o timer (quase expirado -> full de novo)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      e.spawnShield = 0; e.hp = Math.max(e.hp, 400);
      e.x = p.x + 1.5; e.z = p.z;
      e.hitstun = 0.05; // quase expirado
      e.state = 'idle';
      p.comboStep = 0; p.comboResetTimer = 0; // forca attack1 (hit sincrono)
      p.hitstun = 0; p.spawnShield = 0; // isola: player limpo (kawarimi do [6] pode ter counter-hit)
      p.cds.atk = 0;
      window.executeSkill(p, 'atk');
      return { hitstun: e.hitstun || 0 };
    })()
    """)
    assert r['hitstun'] >= 0.30, f'juggle nao resetou: {r}'
    print(f"[7] juggle: hit novo resetou hitstun para {r['hitstun']:.2f}s (combo chain do Storm)")

    # [8] letal: morte NAO e impedida pelo hitstun (dealDamage -> down)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      e.spawnShield = 0; e.hitstun = 0.35; e.hp = 5;
      e.x = p.x + 1.5; e.z = p.z;
      e.state = 'idle';
      p.comboStep = 0; p.comboResetTimer = 0; // forca attack1 (hit sincrono)
      p.hitstun = 0; p.spawnShield = 0; // isola: player limpo
      p.cds.atk = 0;
      window.executeSkill(p, 'atk');
      return { deadTimer: e.deadTimer, state: e.state, hp: e.hp };
    })()
    """)
    assert r['deadTimer'] > 0 and r['state'] == 'down', f'morte nao processou: {r}'
    print(f"[8] hit letal matou normalmente apesar do hitstun (deadTimer={r['deadTimer']}, state=down)")

    # [9] decaimento em dt REAL: polling monotonicamente decrescente ate 0
    # (headless throttla rAF: relogio do jogo atrasa vs parede — nao usar sleep exato)
    r = await ev(c, """
    (() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
      if (!e) return { err: 'sem bot vivo' };
      e.hitstun = 0.30;
      return { id: e.id || e.heroId };
    })()
    """)
    assert not r.get('err'), r
    samples = []
    for _ in range(14):  # ate ~4.2s de parede
        await asyncio.sleep(0.3)
        v = await ev(c, """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          const e = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
          return e ? (e.hitstun || 0) : -1;
        })()
        """)
        samples.append(round(v, 4))
        if v <= 0:
            break
    mono = all(samples[i + 1] <= samples[i] + 1e-9 for i in range(len(samples) - 1))
    assert samples[0] < 0.30, f'nao iniciou decaimento: {samples}'
    assert mono, f'decaimento nao monotono: {samples}'
    assert samples[-1] == 0, f'hitstun nao expirou: {samples}'
    print(f"[9] hitstun decaiu monotonicamente em dt real e expirou: {samples}")

    # [10] console errors
    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    print(f'[10] console errors: {len(errs)}')
    for e in errs[:5]:
        print('   err:', e)
    assert len(errs) == 0, 'console errors inesperados'
    print('W-HS SMOKE PASS — HITSTUN DO APK FUNCIONAL (0.35s/0.60s, kawarimi livre, juggle)')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    shutil.rmtree(PROFILE, ignore_errors=True)
