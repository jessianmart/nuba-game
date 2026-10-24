"""Probe W6 — música de fundo + settings funcionais.
  C1  2 trilhas servidas (HEAD 200)
  C2  boot: MUSIC.track='menu', src=menu_modeslct.ogg, loop=true, volume=0.7*0.55
  C3  startMatch: track='battle', src=battle_stage00.ogg, volume=0.38*0.55 (leve)
  C4  toggle música OFF -> paused; ON -> retoma (estado, autoplay à parte)
  C5  slider música 100 -> volume = base*1.0; slider SFX 20 -> AUTH_SFX.volume=0.2
  C6  persistência: music=false / musicVol=1 / sfxVol=0.2 no loadProfileData
  C7  zero console errors
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

UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')


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
    profile = tempfile.mkdtemp(prefix='nuba_w6_')
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
        for _ in range(60):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        checks = {}

        # ---- C1: trilhas servidas ----
        codes = await ev(c, "(async () => { const out = []; for (const n of ['menu_modeslct', 'battle_stage00']) { const r = await fetch('assets/audio/music/' + n + '.ogg', { method: 'HEAD' }); out.push(n + ':' + r.status); } return out; })()", ap=True)
        bad1 = [x for x in codes if not x.endswith(':200')]
        checks['C1-trilhas-200'] = not bad1
        print(f'[C1] HEAD: {codes}')

        # ---- C2: boot -> menu ----
        d2 = await ev(c, """(() => {
            try {
                const m = window.MUSIC;
                return { track: m.track, src: (m.el || {}).src || '', loop: !!(m.el || {}).loop,
                         vol: (m.el || {}).volume, paused: (m.el || {}).paused };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok2 = isinstance(d2, dict) and d2['track'] == 'menu' and 'menu_modeslct' in d2['src'] and d2['loop'] and abs(d2['vol'] - 0.7 * 0.55) < 0.02
        checks['C2-boot-menu'] = ok2
        print(f'[C2] boot: {d2}')

        # ---- C3: startMatch -> battle leve ----
        await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.4)
        d3 = await ev(c, """(() => {
            try {
                const m = window.MUSIC;
                return { track: m.track, src: (m.el || {}).src || '', vol: (m.el || {}).volume };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok3 = isinstance(d3, dict) and d3['track'] == 'battle' and 'battle_stage00' in d3['src'] and abs(d3['vol'] - 0.38 * 0.55) < 0.02
        checks['C3-battle-leve'] = ok3
        print(f'[C3] battle: {d3} (esperado vol ~0.209)')

        # ---- C4: toggle música off/on ----
        d4 = await ev(c, """(() => {
            try {
                const t = document.getElementById('pref-music');
                t.checked = false; t.dispatchEvent(new Event('change'));
                const pausedOff = window.MUSIC.el.paused;
                t.checked = true; t.dispatchEvent(new Event('change'));
                return { pausedOff, afterOn: { paused: window.MUSIC.el.paused, vol: window.MUSIC.el.volume } };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok4 = isinstance(d4, dict) and d4['pausedOff'] is True
        checks['C4-toggle-musica'] = ok4
        print(f'[C4] toggle: {d4}')

        # ---- C5: sliders live ----
        d5 = await ev(c, """(() => {
            try {
                const mv = document.getElementById('pref-music-vol');
                mv.value = 100; mv.dispatchEvent(new Event('input'));
                const volMus = window.MUSIC.el.volume;
                const sv = document.getElementById('pref-sfx-vol');
                sv.value = 20; sv.dispatchEvent(new Event('input'));
                return { volMus, volSfx: window.AUTH_SFX.volume };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok5 = isinstance(d5, dict) and abs(d5['volMus'] - 0.38) < 0.02 and abs(d5['volSfx'] - 0.2) < 0.01
        checks['C5-sliders-live'] = ok5
        print(f'[C5] sliders: {d5} (esperado volMus ~0.38, volSfx 0.2)')

        # ---- C6: persistência ----
        d6 = await ev(c, """(() => {
            try {
                const raw = localStorage.getItem('nuba.profile.v1');
                const d = JSON.parse(raw || '{}');
                return { music: d.music, musicVol: d.musicVol, sfxVol: d.sfxVol };
            } catch (e) { return 'ERR:' + e.message; }
        })()""")
        ok6 = isinstance(d6, dict) and d6['music'] is not False and abs(d6['musicVol'] - 1.0) < 0.01 and abs(d6['sfxVol'] - 0.2) < 0.01
        checks['C6-persistencia'] = ok6
        print(f'[C6] perfil: {d6}')

        # ---- C7: zero console errors ----
        errors = getattr(c, 'console_errors', [])
        noise = ('Autoplay', 'vibrate', 'favicon', 'webp', 'WebGL', 'GPU stall')
        real = [e for e in errors if not any(x in e for x in noise)]
        checks['C7-zero-console-errors'] = not real
        print(f'[C7] console errors: {len(real)} reais ({len(errors)} brutos)')
        for e in real[:4]:
            print('   ', e[:180])

        passed = sum(1 for v in checks.values() if v)
        print(f'\n{"=" * 50}')
        for k, v in checks.items():
            print(f'  {"PASS" if v else "FAIL"}  {k}')
        print(f'{"=" * 50}\nW6 MUSIC PROBE: {passed}/{len(checks)}')
        return 0 if passed == len(checks) else 1
    finally:
        proc.terminate()


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
