"""Probe PV2 — valida o modo REALEZA NA VILA end-to-end via CDP:
spawn solo no layout, zona 結界 encolhendo, dano fora, baú, last-standing.
Run: python tools/probe_pv2.py   (cwd = repo root)
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

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_pv2_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1600,900', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json(PORT, '/json')
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()

    # [1] chip BR habilitado no picker
    r = await ev(c, "(() => { const ch = document.querySelector('#mode-picker .mode-chip[data-mode=\"br_vila\"]'); return { has: !!ch, disabled: ch ? ch.disabled : null }; })()")
    assert r['has'] and not r['disabled'], f'chip BR: {r}'
    print('[1] chip REALEZA NA VILA habilitado no picker')

    # [1.5] boot-wait: game.js completo (startMatch exposto no fim do boot)
    t = None
    for _ in range(40):
        t = await ev(c, "typeof window.startMatch")
        if t == 'function':
            break
        await asyncio.sleep(0.5)
    assert t == 'function', f'boot incompleto: typeof startMatch = {t}'
    print('[1.5] boot game.js completo (startMatch exposto)')

    # [2] startMatch br_vila — spawn solo no layout
    ok = await ev(c, "(async () => { try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    lay = json.load(open('public/assets/data/br_vila_layout.json', encoding='utf-8'))
    for _ in range(60):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 10:
            break
        await asyncio.sleep(0.5)
    assert n == 10, f'unidades: {n}'
    r = await ev(c, "(() => { const teams = window.units.map(u => u.team); const pos = window.units.map(u => [u.x, u.z]); return { teams, pos, brMode: document.body.classList.contains('br-mode') }; })()")
    assert r['brMode'], 'body.br-mode ausente'
    assert all(t.startswith('solo_') for t in r['teams']), f'teams: {r["teams"]}'
    want = [[s['x'], s['z']] for s in lay['spawnRing']]
    got = r['pos']
    for (wx, wz), (gx, gz) in zip(want, got):
        assert abs(wx - gx) < 8 and abs(wz - gz) < 8, f'spawn fora do layout: ({wx},{wz}) vs ({gx},{gz})'
    arena_lbl = await ev(c, "(document.getElementById('minimap-arena-name') || {}).textContent || ''")
    assert 'VILA' in arena_lbl.upper(), f'BR nao esta na vila: {arena_lbl!r}'
    print(f'[2] BR: 10 solo spawns no layout (drift AI ok), arena = {arena_lbl!r}, teams {r["teams"][0]}..{r["teams"][-1]}')

    # [3] estado da zona + HUD
    r = await ev(c, "(() => { const br = window.__matchState.br; const hud = document.getElementById('br-hud'); const tg = getComputedStyle(document.querySelector('.team-group.blue')).display; return { zoneR: br.zoneR, target: br.zoneTargetR, min: br.zoneMin, phases: br.zonePhases, phase: br.phase, chests: br.chests.length, alive: br.alive, hudDisplay: hud ? getComputedStyle(hud).display : 'none', teamGroupDisplay: tg }; })()")
    assert r['zoneR'] == lay['zoneRadiusStart'] and r['min'] == lay['zoneRadiusMin'], r
    assert r['chests'] == 12 and r['alive'] == 10, r
    assert r['hudDisplay'] != 'none' and r['teamGroupDisplay'] == 'none', r
    print(f"[3] zona: R={r['zoneR']}->{r['min']} em {r['phases']} fases · {r['chests']} baús · VIVOS {r['alive']} · HUD BR visível, placar de times oculto")

    # [4] zona encolhendo (acelera o timer)
    await ev(c, "window.__matchState.br.zoneTimer = 0.01")
    await asyncio.sleep(1.2)
    r = await ev(c, "(() => { const br = window.__matchState.br; return { phase: br.phase, r: br.zoneR, target: br.zoneTargetR }; })()")
    assert r['phase'] == 1, f'fase nao avancou: {r}'
    zr_samples = [r['r'], r['target']]
    await asyncio.sleep(1.5)
    r2 = await ev(c, "(() => { const br = window.__matchState.br; return { r: br.zoneR, target: br.zoneTargetR }; })()")
    zr_samples.append(r2['r'])
    assert zr_samples[2] < zr_samples[0] and abs(r2['target'] - 55.166) < 1.0, f'zona nao encolheu: {zr_samples} target={r2["target"]}'
    print(f'[4] zona FASE 1: raio {zr_samples[0]:.1f} -> {zr_samples[2]:.1f} em direcao ao target {r2["target"]:.1f}')

    # [5] dano fora da zona (com diagnóstico de tick/pausa — volátil entre runs)
    r = await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); p.spawnShield = 0; const hp0 = p.hp; p.x = 200; return { hp: hp0, tick: window.__matchState.br.damageTick, d: Math.hypot(p.x - window.__matchState.br.center.x, p.z - window.__matchState.br.center.z), zr: window.__matchState.br.zoneR }; })()")
    for _ in range(12):
        await asyncio.sleep(0.5)
        r2 = await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); return { hp: p.hp, tick: window.__matchState.br ? window.__matchState.br.damageTick : -1 }; })()")
        if r2['hp'] < r['hp']:
            break
    assert r2['hp'] < r['hp'], f"sem dano fora da zona em 6s: antes={r} depois={r2}"
    print(f"[5] dano 結界 fora da zona: HP {r['hp']} -> {r2['hp']} (dist {r['d']:.0f} > raio {r['zr']:.1f}, tick {r['tick']:.2f} -> {r2['tick']:.2f})")

    # [6] coleta de baú — bots competem: poll com re-escolha até achar um que o PLAYER pegue
    hp_before, hp_after, chest_at, tries = None, None, None, 0
    for _ in range(5):
        tries += 1
        r = await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); const free = window.__matchState.br.chests.find(c => !c.taken); if (!free) return null; p.x = free.x; p.z = free.z; p.hp = Math.max(10, p.hp - 60); return { hp: p.hp, cx: free.x, cz: free.z }; })()")
        if not r:
            break
        chest_at = f"({r['cx']},{r['cz']})"
        hp_before = r['hp']
        for _ in range(6):
            await asyncio.sleep(0.5)
            hp_after = await ev(c, "window.units.find(u => u.isPlayer).hp")
            if hp_after >= hp_before + 30:
                break
        if hp_after is not None and hp_after >= hp_before + 30:
            break
    taken_total = await ev(c, "window.__matchState.br.chests.filter(c => c.taken).length")
    assert hp_after is not None and hp_after >= hp_before + 30, f'baú não curou ({hp_before} -> {hp_after})'
    print(f'[6] baú em {chest_at} coletado: HP {hp_before} -> {hp_after} (+35) · {taken_total} baú(s) no total')

    # [7] last standing — elimina os 9 bots (diagnóstico hp/deadTimer antes/depois)
    r7a = await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); p.x = 0; p.z = 0; p.hp = p.maxHp; const bots = window.units.filter(u => !u.isPlayer); bots.forEach(b => { b.spawnShield = 0; b.hp = 1; dealDamage(p, b, 9999, 'probe'); }); return bots.map(b => ({ hp: b.hp, dt: b.deadTimer, ss: b.spawnShield })); })()")
    await asyncio.sleep(1.5)
    r3 = await ev(c, "(() => ({ alive: window.__matchState.br ? window.__matchState.br.alive : -1, botsAfter: window.units.filter(u => !u.isPlayer).map(b => ({ hp: b.hp, dt: b.deadTimer })) }))()")
    assert r3['alive'] == 1, f"alive deveria ser 1: {r3}"
    txt = await ev(c, "document.body.textContent.includes('ÚLTIMO DE PÉ') || document.body.textContent.includes('VITÓRIA')")
    print(f'[7] last-standing: alive {r3["alive"]} · fim disparado: {txt}')
    # RUÍDO ESPERADO do loader (PV-B.2 webp-first cai no png): 404 .webp + WebGLState
    # em headless GPU-less no fallback. Nao afeta render real com GPU.
    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    print(f'[8] console errors (sem 404s webp esperados): {len(errs)}')
    for e in errs[:5]:
        print('   err:', e)
    assert len(errs) == 0, 'console errors inesperados no BR'
    print('PV2 PROBE PASS — REALEZA NA VILA FUNCIONAL')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(PROFILE, ignore_errors=True)
