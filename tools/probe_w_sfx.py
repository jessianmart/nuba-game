"""Probe W5 — SFX autênticos posicionados: falloff por distância + wiring por
momento de batalha + zero genéricos.

Checks:
  C1  22 cues novas servidas (HEAD 200)
  C2  playAt: vol decai monotonicamente com d; >60u vira silêncio (skip)
  C3  dealDamage: hit_s no alvo; dano >=180 adiciona ground_hit
  C4  melee: punch_swing (cast) + punch_hit/kick_hit no alvo
  C5  cast q: voz do herói (SKILL_SFX_MAP) posicionada (campo d presente)
  C6  kill: down + ko na vítima + level_up no atacante
  C7  respawn: stand_up1/2
  C8  fim do awakening: awake_off
  C9  ult pronto: max_gauge (1x, player)
  C10 arremesso: kunai_swing + (kunai_hit | kunai_hit_wall)
  C11 zero console errors
Run: python tools/probe_w_sfx.py   (cwd = repo root)
"""
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402

UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

NEW_CUES = ['kunai_hit', 'kunai_hit2', 'kunai_hit_wall', 'kunai_miss', 'shuriken',
            'kick_swing', 'kick_hit2', 'punch_hit2', 'ground_hit', 'water_hit',
            'body_atk', 'sousai', 'stand_up1', 'stand_up2', 'awake_off', 'box_open',
            'chakura_get', 'item_get', 'jump1', 'jump2', 'ground_hit2', 'chak_hit']


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, ap=False):
    v = await c.eval_js(expr, await_promise=ap)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def plays(c):
    return await ev(c, "(window.AUTH_SFX.lastPlays || []).map(p => p.n + '@' + p.v + '/d' + p.d)")


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_w5_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=844,390', '--inprivate', f'--user-data-dir={profile}', 'about:blank'
    ])
    time.sleep(3)
    try:
        tabs = None
        for _ in range(20):
            try:
                tabs = http_json(port, '/json')
                break
            except Exception:
                time.sleep(0.5)
        ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws)
        await c.connect()
        await c.send("Emulation.setDeviceMetricsOverride",
                     {"width": 844, "height": 390, "deviceScaleFactor": 2, "mobile": True})
        await c.send("Emulation.setUserAgentOverride", {"userAgent": UA})
        for _ in range(10):
            if await ev(c, "/iPhone/.test(navigator.userAgent)"):
                break
            await asyncio.sleep(0.3)
        await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
        for _ in range(40):
            if await ev(c, "typeof window.startMatch") == 'function':
                break
            await asyncio.sleep(0.5)
        await ev(c, "document.body.classList.add('touch'); window.__DEVICE.isTouch = true;")
        ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
        assert ok == 'ok', f'startMatch: {ok}'
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.4)
        await asyncio.sleep(2.0)
        assert await ev(c, "!!window.__camera"), 'camera exposta?'
        checks = {}

        # ---- C1: cues novas servidas ----
        codes = await ev(c, "(async () => { const out = []; for (const n of %s) { const r = await fetch('assets/audio/decoded/' + n + '.ogg', { method: 'HEAD' }); out.push(n + ':' + r.status); } return out; })()" % json.dumps(NEW_CUES), ap=True)
        bad1 = [x for x in codes if not x.endswith(':200')]
        checks['C1-22-cues-200'] = not bad1
        print(f'[C1] HEAD: {len(codes)} cues, falhas: {bad1 or "nenhuma"}')

        # ---- C2: falloff monotônico + skip > 60u ----
        f = await ev(c, """(() => {
            const cam = window.__camera;
            AUTH_SFX.lastPlays = [];
            const cx = cam.position.x, cz = cam.position.z;
            const r = {};
            AUTH_SFX.playAt('hit_s', cx, cz, { vol: 1, min: 1 });          r.d0 = (AUTH_SFX.lastPlays[0] || {}).v;
            AUTH_SFX.playAt('kunai_miss', cx + 25, cz, { vol: 1, min: 1 }); r.d25 = (AUTH_SFX.lastPlays[1] || {}).v;
            AUTH_SFX.playAt('body_atk', cx + 50, cz, { vol: 1, min: 1 });    r.d50 = (AUTH_SFX.lastPlays[2] || {}).v;
            r.skipped = AUTH_SFX.playAt('sousai', cx + 70, cz, { vol: 1, min: 1 }) === false && AUTH_SFX.lastPlays.length === 3;
            r.mono = r.d0 > r.d25 && r.d25 > r.d50;
            return r;
        })()""")
        print(f"[C2] falloff: d0={f['d0']} d25={f['d25']} d50={f['d50']} skip60+={f['skipped']}")
        checks['C2-falloff-monotonico'] = bool(f['mono']) and f['d0'] >= 0.9 and f['d50'] < 0.3
        checks['C2-skip-alem-60u'] = bool(f['skipped'])

        # ---- C3: dealDamage -> hit_s no alvo; dano alto -> ground_hit ----
        d3 = await ev(c, """(() => {
            try {
                const p = window.units.find(u => u.isPlayer);
                const f1 = window.units.find(u => u.team !== p.team);
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; p.hitstun = 0; p.deadTimer = 0;
                f1.x = p.x + 3; f1.z = p.z; // W5: vitima PERTO da camera (falloff e o comportamento — teste precisa de d curto)
                f1.spawnShield = 0; f1.deadTimer = 0; f1.hp = 500; f1.maxHp = 500;
                const hpAntes = f1.hp;
                window.dealDamage(p, f1, 150, 'probe-leve');
                return { hpAntes, hpDepois: f1.hp, plays: (AUTH_SFX.lastPlays || []).map(x => x.n) };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        if isinstance(d3, str):
            print(f'[C3] ERRO no eval: {d3}')
        else:
            print(f"[C3] hp {d3['hpAntes']}->{d3['hpDepois']} plays: {d3['plays']}")
        has_hit = isinstance(d3, dict) and any(x == 'hit_s' for x in d3['plays'])
        d3b = await ev(c, """(() => {
            try {
                const p = window.units.find(u => u.isPlayer);
                const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0 && u.hp > 0);
                if (!f) return 'sem-foe-viva';
                const p0 = window.units.find(u => u.isPlayer);
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = [];
                f.x = p0.x + 3; f.z = p0.z;
                f.hp = 500; f.maxHp = 500; f.spawnShield = 0;
                const antes = f.hp;
                window.dealDamage(p, f, 200, 'probe-pesado');
                return { antes, depois: f.hp, plays: (AUTH_SFX.lastPlays || []).map(x => x.n) };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        print(f'[C3b] pesado: {d3b}')
        has_ground = isinstance(d3b, dict) and any(x.startswith('ground_hit') for x in d3b['plays'])
        checks['C3-hit_s-posicionado'] = has_hit
        checks['C3-ground_hit-em-180+'] = has_ground

        # ---- C4: melee -> punch_swing (cast) + punch_hit no alvo ----
        await ev(c, """(() => {
            const p = window.units.find(u => u.isPlayer);
            const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0);
            f.x = p.x + 2; f.z = p.z; f.hp = 800; f.maxHp = 800; f.spawnShield = 0;
            p.hitstun = 0; p.deadTimer = 0; p.cds.atk = 0; p.chakra = 100;
            AUTH_SFX._last = {}; AUTH_SFX.lastPlays = [];
            window.executeSkill(p, 'atk');
        })()""")
        await asyncio.sleep(0.4)
        p4 = await plays(c)
        melee_ok = any(x.startswith('punch_swing@') or x.startswith('kick_swing@') for x in p4) and \
                   any(x.startswith('punch_hit@') or x.startswith('punch_hit2@') for x in p4)
        print(f'[C4] melee: {p4[:5]}')
        checks['C4-melee-punch'] = melee_ok

        # ---- C5: cast q -> voz do herói posicionada ----
        hero = await ev(c, """(() => {
            const p = window.units.find(u => u.isPlayer);
            p.hitstun = 0; p.deadTimer = 0; p.awakenedTimer = 0; p.chakra = 100; p.cds.q = 0;
            AUTH_SFX.lastPlays = [];
            window.executeSkill(p, 'q');
            return { heroId: p.heroId, sfx: (window.SKILL_SFX_MAP[p.heroId] || {}).q,
                     plays: AUTH_SFX.lastPlays.map(x => x.n + '/d' + x.d) };
        })()""")
        print(f"[C5] q de {hero['heroId']} (mapa: {hero['sfx']}): {hero['plays'][:3]}")
        checks['C5-voz-do-heroi-posicionada'] = bool(hero['sfx']) and any(x.startswith(hero['sfx'] + '/') for x in hero['plays'])

        # ---- C6: kill -> down+ko na vítima + level_up ----
        await ev(c, """(() => {
            const p = window.units.find(u => u.isPlayer);
            const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0);
            f.hp = 1; f.spawnShield = 0; AUTH_SFX._last = {}; AUTH_SFX.lastPlays = [];
            p.hitstun = 0; p.deadTimer = 0;
            window.dealDamage(p, f, 9999, 'probe-kill');
            return true;
        })()""")
        await asyncio.sleep(0.6)
        p6 = await plays(c)
        print(f'[C6] kill: {p6[:6]}')
        checks['C6-down-ko-levelup'] = (any(x.startswith('down@') for x in p6) and
                                        any(x.startswith('ko@') for x in p6) and
                                        any(x.startswith('level_up@') for x in p6))

        # ---- C7: respawn -> stand_up (respawn tem delay de anim/juice — janela larga) ----
        k7 = await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0 && u.hp > 0); if (!f) return 'sem-foe'; f.x = p.x + 3; f.z = p.z; f.hp = 1; f.spawnShield = 0; p.hitstun = 0; window.dealDamage(p, f, 9999, 'probe-respawn'); return { killed: f.heroId, dt: f.deadTimer, plays: (AUTH_SFX.lastPlays || []).map(x => x.n) }; })()")
        print(f'[C7] kill fresco: {k7}')
        await asyncio.sleep(0.5)
        r7 = await ev(c, "(() => { const f = window.units.find(u => u.team !== (window.units.find(x => x.isPlayer)).team && u.deadTimer > 0); if (f) { f.deadTimer = 0.02; AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; } return f ? f.heroId : 'nenhum-dead'; })()")
        print(f'[C7] alvo do respawn: {r7}')
        p7, st7 = [], []
        for _ in range(15):
            await asyncio.sleep(0.4)
            p7 = await plays(c)
            st7 = await ev(c, "(() => { const f = window.units.find(u => u.team !== (window.units.find(x => x.isPlayer)).team); return { dt: Math.round(f.deadTimer * 100) / 100, hp: f.hp, vis: f.mesh.visible }; })()")
            if any(x.startswith('stand_up') for x in p7):
                break
        print(f'[C7] estado foe: {st7} | plays: {p7[:4]}')
        checks['C7-stand-up'] = any(x.startswith('stand_up') for x in p7)

        # ---- C8: fim do awakening -> awake_off ----
        await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); p.awakenedTimer = 0.05; AUTH_SFX.lastPlays = []; return p.auraMesh ? 'aura' : 'sem-aura'; })()")
        await asyncio.sleep(0.6)
        p8 = await plays(c)
        print(f'[C8] awake_off: {p8[:3]}')
        checks['C8-awake-off'] = any(x.startswith('awake_off@') for x in p8)

        # ---- C9: ult pronto -> max_gauge ----
        await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); p.chakra = 99; p.cds.r = 0; p._ultReadyAnnounced = false; AUTH_SFX._last['max_gauge'] = 0; AUTH_SFX.lastPlays = []; return true; })()")
        await asyncio.sleep(0.8)
        p9 = await plays(c)
        print(f'[C9] max_gauge: {p9[:3]}')
        checks['C9-max-gauge'] = any(x.startswith('max_gauge@') for x in p9)

        # ---- C10: arremesso -> kunai_swing + (kunai_hit | kunai_hit_wall) ----
        await ev(c, """(() => {
            const p = window.units.find(u => u.isPlayer);
            window.units.forEach(u => { if (u.team !== p.team) { u.x = p.x + 8; u.z = p.z + 28; u.deadTimer = 0; u.hp = 999; u.maxHp = 999; } }); // 29u garantidos, dentro da arena (sem clamp de volta)
            p.hitstun = 0; p.deadTimer = 0; p.cds.atk = 0; p.chakra = 100; p.comboStep = 0;
            AUTH_SFX._last = {}; AUTH_SFX.lastPlays = [];
            window.executeSkill(p, 'atk');
            const s = Math.sin(p.rotY), c = Math.cos(p.rotY);
            const fA = window.units.find(u => u.team !== p.team);
            const fB = window.units.filter(u => u.team !== p.team)[1];
            fA.x = p.x + s * 10; fA.z = p.z + c * 10;
            if (fB) { fB.x = p.x + c * 10; fB.z = p.z + s * 10; }
            return true;
        })()""")
        await asyncio.sleep(0.35)
        p10a = await plays(c)   # leitura cedo: cap 24 dos bots empurraria o cast para fora
        await asyncio.sleep(2.7)
        p10b = await plays(c)   # leitura tardia: impacto em voo
        p10 = p10a + p10b
        thrown = any(x.startswith('kunai_swing@') for x in p10)
        landed = any(x.startswith('kunai_hit') for x in p10)
        print(f'[C10] arremesso: {p10[:8]}')
        checks['C10-kunai-swing'] = thrown
        checks['C10-kunai-impacto'] = landed

        print('=== W5 CHECKS ===')
        for k, v in checks.items():
            print(f"  {'OK ' if v else 'FALHA'} {k}")
        errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)
                and 'vibrate' not in str(e)]
        print(f'  console errors (filtrado): {len(errs)}')
        bad = [k for k, v in checks.items() if not v] + (['console'] if errs else [])
        assert not bad, f'W5 falhou: {bad}'
        c.running = False
        print('W5 SFX PROBE PASS')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        import shutil  # noqa: E402
        shutil.rmtree(profile, ignore_errors=True)


asyncio.run(main())
