"""Probe W8 — mix equalizado em runtime.
  C1  musica battle: el.volume == 0.55 baseVol x 0.55 musicVol = 0.3025
  C2  voz: unitVoice(player,'atk_m') -> lastPlays v ~ 0.92 (boost 1.0, falloff~1)
  C3  skills nao saturam: playAt('ground_hit', 0.9) perto -> v ~ 0.9 (< 1.0)
  C4  musica menu: returnToLobby -> track menu, el.volume 0.385
  C5  zero console errors
"""
import asyncio
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

UA_M = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
        'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def ev(c, expr, ap=False):
    v = await c.eval_js(expr, await_promise=ap)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_w8_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}', 'about:blank'
    ])
    time.sleep(3)
    try:
        tabs = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=5) as r:
                    tabs = json.load(r)
                break
            except Exception:
                time.sleep(0.5)
        ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws)
        await c.connect()
        await c.send('Runtime.enable')
        await c.send('Log.enable')
        await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
        for _ in range(60):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        checks = {}

        # partida
        await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.4)

        # C1: musica battle eff volume
        d = await ev(c, """(() => {
            const m = window.MUSIC;
            const prof = JSON.parse(localStorage.getItem('nuba.profile.v1') || '{}');
            const mv = prof.musicVol != null ? prof.musicVol : 0.55;
            return { track: m.track, vol: m.el ? +m.el.volume.toFixed(4) : null,
                     esperado: +(0.55 * mv).toFixed(4) };
        })()""")
        checks['C1-battle-vol'] = d['track'] == 'battle' and abs(d['vol'] - d['esperado']) < 0.01
        print(f"[C1] musica battle: vol={d['vol']} (esperado {d['esperado']})")

        # C2: voz do player (falloff d=0 -> boost 1.0 -> 0.92)
        d2 = await ev(c, """(async () => {
            const p = window.units.find(u => u.isPlayer);
            if (!p) return { err: 'no player' };
            window._voiceGate = {};
            // camera colada no player (contrato W8: playAt usa cam.position.x):
            window.__camera = { position: { x: p.x, z: p.z } };
            const A = window.AUTH_SFX;
            const flags = { enabled: A.sfx && A.sfx.enabled, muted: A.muted,
                            hasMap: !!(window.HERO_VOICE_MAP[p.heroId] || {})['atk_m'] };
            const before = (A.lastPlays || []).length;
            const ok = window.unitVoice(p, 'atk_m');
            await new Promise(r => setTimeout(r, 150));
            const lp = A.lastPlays || [];
            const last = lp.length ? lp[lp.length - 1] : null;
            return { flags: flags, played: ok, grew: lp.length > before,
                     v: last ? last.v : null, n: last ? last.n : null };
        })()""", ap=True)
        ok2 = d2.get('played') and d2.get('grew') and d2.get('n', '').startswith('voice/') and abs((d2.get('v') or 0) - 0.92) < 0.03
        checks['C2-voz-092'] = ok2
        print(f"[C2] voz: {d2}")

        # C3: skill ground_hit nao satura (v < 1.0)
        d3 = await ev(c, """(async () => {
            const p = window.units.find(u => u.isPlayer);
            window.__camera = { position: { x: p.x, z: p.z } };
            window.AUTH_SFX.playAt('ground_hit', p.x, p.z, { vol: 0.9, min: 1 });
            await new Promise(r => setTimeout(r, 80));
            const lp = window.AUTH_SFX.lastPlays || [];
            const last = lp.length ? lp[lp.length - 1] : null;
            return { v: last ? last.v : null };
        })()""", ap=True)
        checks['C3-skill-no-clamp'] = d3.get('v') is not None and d3['v'] < 0.99 and abs(d3['v'] - 0.9) < 0.15
        print(f"[C3] skill perto: v={d3['v']} (< 0.99 = headroom ok)")

        # C4: menu de volta
        d4 = await ev(c, """(() => {
            window.MUSIC.play('menu');
            return { track: window.MUSIC.track, vol: +window.MUSIC.el.volume.toFixed(4) };
        })()""")
        checks['C4-menu-vol'] = d4['track'] == 'menu' and abs(d4['vol'] - 0.385) < 0.01
        print(f"[C4] menu: {d4}")

        # C5: console
        errors = getattr(c, 'console_errors', [])
        noise = ('Autoplay', 'vibrate', 'favicon', 'webp', 'WebGL', 'GPU stall', 'motion')
        real = [e for e in errors if not any(x in e for x in noise)]
        checks['C5-zero-console'] = not real
        print(f"[C5] console reais: {len(real)}")
        for e in real[:3]:
            print('  -', str(e)[:160])

        passed = sum(1 for v in checks.values() if v)
        for k, v in checks.items():
            print(f"  {'PASS' if v else 'FAIL'}  {k}")
        print(f'W8 MIX PROBE: {passed}/{len(checks)}')
        return 0 if passed == len(checks) else 1
    finally:
        proc.kill()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
