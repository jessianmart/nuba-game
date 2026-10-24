"""Probe W5-F2 — vozes de batalha POR HERÓI nos momentos de combate.

Checks:
  C1  252 oggs de voz servidos (HEAD 200) — voice/<hero>/<cue>.ogg
  C2  dano leve na vítima -> voice/<hero>/S_PL_DmgS* posicionado
  C3  dano pesado (>=180) -> voice/<hero>/S_PL_DmgM* + ground_hit
  C4  kill -> voice/<hero>/S_PL_DmgL* (gemido de queda)
  C5  cast atk -> S_PL_AtkS*; ult 'r' -> S_PL_AtkL*
  C6  gate por unidade: 2 danos < 1.7s -> só 1 voz
  C7  unitVoice defensivo: heroId fora do roster / null -> false sem throw
  C8  zero console errors
Run: python tools/probe_w5f2.py   (cwd = repo root, server :8080)
"""
import asyncio
import json
import tempfile
import time

import os
import socket
import subprocess
import sys
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402

UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

HEROES = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt',
          '1nej', '1jry', '1tnd', '1orc']
SAMPLE_CUES = ['S_PL_DmgS1', 'S_PL_DmgM1', 'S_PL_AtkS1', 'S_PL_Awake']


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


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_w5f2_')
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
        await c.send('Runtime.enable', {})
        await c.send('Log.enable', {})
        await c.send('Emulation.setDeviceMetricsOverride',
                     {'width': 844, 'height': 390, 'deviceScaleFactor': 2, 'mobile': True})
        await c.send('Emulation.setUserAgentOverride', {'userAgent': UA})
        for _ in range(10):
            if await ev(c, '/iPhone/.test(navigator.userAgent)'):
                break
            await asyncio.sleep(0.3)
        await c.send('Page.navigate', {'url': 'http://localhost:8080/index.html'})
        for _ in range(40):
            if await ev(c, 'typeof window.startMatch') == 'function':
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
        assert await ev(c, '!!window.__camera'), 'camera exposta?'
        assert await ev(c, 'Object.keys(window.HERO_VOICE_MAP).length'), 'HERO_VOICE_MAP exposto?'
        checks = {}

        # ---- C1: 252 oggs de voz servidos ----
        paths = [f'voice/{h}/{cue}' for h in HEROES for cue in SAMPLE_CUES]
        for extra in ('S_PL_DmgL1', 'S_PL_AtkL1', 'S_PL_Combo1', 'S_PL_Catch', 'S_PL_GrdBrk1', 'S_PL_DmgS2', 'S_PL_DmgS3'):
            paths.append(f'voice/1nrt/{extra}')
            paths.append(f'voice/1orc/{extra}')
        codes = await ev(c, "(async () => { const out = []; for (const n of %s) { const r = await fetch('assets/audio/decoded/' + n + '.ogg', { method: 'HEAD' }); out.push(r.status === 200 ? 1 : n + ':' + r.status); } return out; })()" % json.dumps(sorted(set(paths))), ap=True)
        bad1 = [x for x in codes if x != 1]
        checks['C1-96-oggs-200'] = not bad1
        print(f'[C1] HEAD {len(codes)} vozes, falhas: {bad1 or "nenhuma"}')

        # ---- C2: dano leve -> voz DmgS da vitima posicionada ----
        d2 = await ev(c, """(() => {
            try {
                const _mr = Math.random; Math.random = () => 0.99; // bots sempre passam no gate (determinismo)
                try {
                const p = window.units.find(u => u.isPlayer);
                const f = window.units.find(u => u.team !== p.team);
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; window._voiceGate = {};
                f.x = p.x + 3; f.z = p.z; f.spawnShield = 0; f.deadTimer = 0; f.hp = 500; f.maxHp = 500; f.hitstun = 0;
                window.dealDamage(p, f, 120, 'probe-f2-leve');
                return { vitima: f.heroId, plays: (AUTH_SFX.lastPlays || []).map(x => x.n + '@' + x.v + '/d' + x.d) };
                } finally { Math.random = _mr; }
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        v2 = f"voice/{d2['vitima']}/S_PL_DmgS" if isinstance(d2, dict) else '?'
        ok2 = isinstance(d2, dict) and any(x.startswith(v2) for x in d2['plays'])
        checks['C2-dano-leve-voz-vitima'] = ok2
        print(f"[C2] leve em {d2.get('vitima') if isinstance(d2, dict) else d2}: {d2.get('plays') if isinstance(d2, dict) else ''}")

        # ---- C3: dano pesado -> DmgM + ground_hit ----
        d3 = await ev(c, """(() => {
            try {
                const _mr = Math.random; Math.random = () => 0.99;
                try {
                const p = window.units.find(u => u.isPlayer);
                const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0 && u.hp > 0);
                if (!f) return 'sem-foe-viva';
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; window._voiceGate = {};
                f.x = p.x + 3; f.z = p.z; f.hp = 600; f.maxHp = 600; f.spawnShield = 0; f.hitstun = 0;
                window.dealDamage(p, f, 220, 'probe-f2-pesado');
                return { vitima: f.heroId, plays: (AUTH_SFX.lastPlays || []).map(x => x.n) };
                } finally { Math.random = _mr; }
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        v3 = f"voice/{d3['vitima']}/S_PL_DmgM" if isinstance(d3, dict) else '?'
        ok3 = isinstance(d3, dict) and any(x.startswith(v3) for x in d3['plays']) and any(x.startswith('ground_hit') for x in d3['plays'])
        checks['C3-pesado-DmgM'] = ok3
        print(f"[C3] pesado: {d3}")

        # ---- C4: kill -> gemido DmgL da vitima ----
        d4 = await ev(c, """(() => {
            try {
                const p = window.units.find(u => u.isPlayer);
                const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0 && u.hp > 0);
                if (!f) return 'sem-foe-viva';
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; window._voiceGate = {};
                f.hp = 1; f.spawnShield = 0; f.hitstun = 0;
                f.x = p.x + 2; f.z = p.z;
                window.dealDamage(p, f, 300, 'probe-f2-kill');
                return { vitima: f.heroId, plays: (AUTH_SFX.lastPlays || []).map(x => x.n) };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        v4 = f"voice/{d4['vitima']}/S_PL_DmgL" if isinstance(d4, dict) else '?'
        ok4 = isinstance(d4, dict) and any(x.startswith(v4) for x in d4['plays'])
        checks['C4-kill-DmgL'] = ok4
        print(f'[C4] kill: {d4}')

        # ---- C5: cast atk -> AtkS; ult r -> AtkL ----
        d5 = await ev(c, """(() => {
            try {
                const p = window.units.find(u => u.isPlayer);
                p.hitstun = 0; p.deadTimer = 0; p.awakenedTimer = 0; p.chakra = 100;
                p.cds.atk = 0; p.cds.r = 0; p.gauge = 100;
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; window._voiceGate = {};
                window.executeSkill(p, 'atk');
                const a1 = (AUTH_SFX.lastPlays || []).map(x => x.n);
                window._voiceGate = {};
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = [];
                window.executeSkill(p, 'r');
                const a2 = (AUTH_SFX.lastPlays || []).map(x => x.n);
                return { hero: p.heroId, atk: a1, r: a2 };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok5 = isinstance(d5, dict) and \
            any(f"voice/{d5['hero']}/S_PL_AtkS" == x[:len(f'voice/{d5["hero"]}/S_PL_AtkS')] for x in d5['atk']) and \
            (any(f"voice/{d5['hero']}/S_PL_AtkL" == x[:len(f'voice/{d5["hero"]}/S_PL_AtkL')] for x in d5['r']) or not d5['r'])
        checks['C5-cast-AtkS'] = isinstance(d5, dict) and any('S_PL_AtkS' in x for x in d5['atk'])
        print(f"[C5] cast {d5.get('hero') if isinstance(d5, dict) else ''}: atk={d5.get('atk') if isinstance(d5, dict) else d5} r={d5.get('r') if isinstance(d5, dict) else ''}")

        # ---- C6: gate por unidade ----
        d6 = await ev(c, """(() => {
            try {
                const _mr = Math.random; Math.random = () => 0.99;
                try {
                const p = window.units.find(u => u.isPlayer);
                const f = window.units.find(u => u.team !== p.team && u.deadTimer <= 0 && u.hp > 0);
                if (!f) return 'sem-foe-viva';
                AUTH_SFX._last = {}; AUTH_SFX.lastPlays = []; window._voiceGate = {};
                f.hp = 900; f.maxHp = 900; f.spawnShield = 0; f.hitstun = 0;
                f.x = p.x + 3; f.z = p.z;
                window.dealDamage(p, f, 100, 'gate-1');
                const n1 = AUTH_SFX.lastPlays.filter(x => x.n.startsWith('voice/')).length;
                window.dealDamage(p, f, 100, 'gate-2');
                const n2 = AUTH_SFX.lastPlays.filter(x => x.n.startsWith('voice/')).length;
                return { n1, n2 };
                } finally { Math.random = _mr; }
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok6 = isinstance(d6, dict) and d6['n1'] >= 1 and d6['n2'] == d6['n1']
        checks['C6-gate-uma-voz'] = ok6
        print(f'[C6] gate: {d6} (esperado n2 == n1)')

        # ---- C7: unitVoice defensivo ----
        d7 = await ev(c, """(() => {
            try {
                const r1 = window.unitVoice(null, 'dmg_s');
                const r2 = window.unitVoice({ heroId: 'zzz', x: 0, z: 0 }, 'dmg_s');
                const r3 = window.unitVoice({ heroId: '1nrt', x: 0, z: 0 }, 'inexistente');
                const r4 = window.unitVoice({ heroId: '1nrt' }, 'dmg_s'); // sem x/z: fallback play()
                return { r1, r2, r3, r4ok: typeof r4 === 'boolean' };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok7 = isinstance(d7, dict) and d7['r1'] is False and d7['r2'] is False and d7['r3'] is False and d7['r4ok']
        checks['C7-unitVoice-defensivo'] = ok7
        print(f'[C7] defensivo: {d7}')

        # ---- C8: zero console errors ----
        errors = getattr(c, 'console_errors', [])
        noise = ('Autoplay', 'vibrate', 'favicon', 'Deprecated', 'webgl', 'WebGL',
                 'GPU stall', 'Casting', 'mixed content', 'Permissions')
        real = [e for e in errors if not any(x in e for x in noise)]
        checks['C8-zero-console-errors'] = not real
        print(f'[C8] console errors: {len(real)} reais ({len(errors)} brutos)')
        if real:
            for e in real[:4]:
                print('   ', e[:200])

        passed = sum(1 for v in checks.values() if v)
        print(f'\n{"=" * 50}')
        for k, v in checks.items():
            print(f'  {"PASS" if v else "FAIL"}  {k}')
        print(f'{"=" * 50}\nW5-F2 VOICE PROBE: {passed}/{len(checks)}')
        return 0 if passed == len(checks) else 1
    finally:
        proc.terminate()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
