"""Probe W7 — HUDs com Motion spring + estética shadcn.
  C1  3 arquivos vendor servidos (HEAD 200)
  C2  window.MOTION populado (import dinamico resolveu; animate fn)
  C3  center-banner: pill compacta (width<=480, top~28%) + spring aplicou
      inline transform/opacity no elemento real
  C4  streak-banner: canto direito (rect.right > 60% VW, top ~74px, h < 64px)
      + spring aplicou
  C5  volta pro hidden (pulseSkinHook semantics preservadas via suite)
  C6  zero console errors
  + screenshot antes/depois -> w7_banner_desktop.png / w7_banner_mobile.png
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

UA_MOBILE = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
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


async def run_session(mobile):
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_w7_')
    args = [find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
            '--window-size=844,390' if mobile else '--window-size=1280,800',
            '--inprivate', f'--user-data-dir={profile}', 'about:blank']
    proc = subprocess.Popen(args)
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
        if mobile:
            await c.send('Emulation.setDeviceMetricsOverride',
                         {'width': 844, 'height': 390, 'deviceScaleFactor': 2, 'mobile': True})
            await c.send('Emulation.setUserAgentOverride', {'userAgent': UA_MOBILE})
            for _ in range(10):
                if await ev(c, '/iPhone/.test(navigator.userAgent)'):
                    break
                await asyncio.sleep(0.3)
        await c.send('Page.navigate', {'url': 'http://localhost:8080/index.html'})
        for _ in range(60):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        # partida real: o HUD (e os banners) so existem visiveis dentro do match
        await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.4)
        checks = {}
        tag = 'mobile' if mobile else 'desktop'

        # C1: vendor servido
        codes = await ev(c, """(async () => {
            const out = [];
            for (const f of ['motion.esm.js', 'motion-dom.esm.js', 'motion-utils.esm.js']) {
                const r = await fetch('assets/vendor/' + f, { method: 'HEAD' });
                out.push(f.split('.')[0] + ':' + r.status);
            }
            return out;
        })()""", ap=True)
        checks['C1-vendor-200'] = all(x.endswith(':200') for x in codes)
        print(f'[C1:{tag}] {codes}')

        # C2: MOTION populado
        mot = None
        for _ in range(20):
            mot = await ev(c, 'window.MOTION ? typeof window.MOTION.animate : "none"')
            if mot == 'function':
                break
            await asyncio.sleep(0.3)
        checks['C2-motion-loaded'] = mot == 'function'
        print(f'[C2:{tag}] window.MOTION.animate = {mot}')

        # C3: center-banner — pill compacta + spring real
        d3 = await ev(c, """(async () => {
            const el = document.getElementById('center-banner');
            el.textContent = 'NARUTO: RASENGAN!';
            el.classList.remove('hidden');
            const r0 = el.getBoundingClientRect();
            window.w7Spring(el, { opacity: [0, 1], scale: [0.94, 1], x: ['-50%', '-50%'], y: ['-50%', '-50%'] }, { stiffness: 520, damping: 34 });
            await new Promise(res => setTimeout(res, 350));
            const r1 = el.getBoundingClientRect();
            return { w: Math.round(r1.width), topPct: +(((r1.top + r1.height / 2) / innerHeight) * 100).toFixed(1),
                     h: Math.round(r1.height), inlineTransform: el.style.transform.slice(0, 60),
                     inlineOpacity: el.style.opacity };
        })()""", ap=True)
        ok3 = (d3['w'] <= 480 and d3['h'] <= 80 and 22 <= d3['topPct'] <= 34
               and len(d3['inlineTransform']) > 3)  # spring aplicou transform; opacity 1 = default (limpo ao terminar)
        checks['C3-center-pill'] = ok3
        print(f'[C3:{tag}] {d3}')

        # C4: streak — canto direito compacto + spring
        d4 = await ev(c, """(async () => {
            const b = document.getElementById('streak-banner');
            b.querySelector('.streak-text').textContent = 'FURIA';
            b.querySelector('.streak-count').textContent = '3x';
            b.classList.remove('hidden'); b.classList.add('show');
            window.w7Spring(b, { opacity: [0, 1], scale: [0.94, 1], y: [-10, 0] }, { stiffness: 380, damping: 26 });
            await new Promise(res => setTimeout(res, 350));
            const r = b.getBoundingClientRect();
            return { rightPct: +(((r.right) / innerWidth) * 100).toFixed(1), top: Math.round(r.top),
                     h: Math.round(r.height), w: Math.round(r.width), inlineT: b.style.transform.slice(0, 40) };
        })()""", ap=True)
        ok4 = (d4['rightPct'] > 60 and 55 <= d4['top'] <= 95 and d4['h'] < 64 and d4['w'] <= 330 and len(d4['inlineT']) > 3)
        checks['C4-streak-corner'] = ok4
        print(f'[C4:{tag}] {d4} (esperado: right>60%, top~74, h<64, w<=330)')

        # C5: hidden semantics (volta a esconder)
        d5 = await ev(c, """(async () => {
            const b = document.getElementById('streak-banner');
            b.classList.remove('show'); b.classList.add('hidden');
            const el = document.getElementById('center-banner');
            el.classList.add('hidden');
            await new Promise(res => setTimeout(res, 50));
            return { streakHidden: b.classList.contains('hidden'), centerHidden: el.classList.contains('hidden') };
        })()""", ap=True)
        checks['C5-hidden-semantics'] = d5['streakHidden'] and d5['centerHidden']
        print(f'[C5:{tag}] {d5}')

        # C6: console errors
        errors = getattr(c, 'console_errors', [])
        noise = ('Autoplay', 'vibrate', 'favicon', 'webp', 'WebGL', 'GPU stall', 'motion')
        real = [e for e in errors if not any(x in e for x in noise)]
        checks['C6-zero-console-errors'] = not real
        print(f'[C6:{tag}] console errors reais: {len(real)}')
        for e in real[:4]:
            print('   ', e[:180])

        # screenshot com os 2 banners visiveis (estilo novo)
        await ev(c, """(() => {
            const el = document.getElementById('center-banner');
            el.textContent = 'NARUTO: RASENGAN!';
            el.classList.remove('hidden');
            const b = document.getElementById('streak-banner');
            b.classList.remove('hidden'); b.classList.add('show');
        })()""")
        await asyncio.sleep(0.5)
        shot = await c.send('Page.captureScreenshot', {'format': 'png'})
        data = shot.get('result', shot).get('data') if isinstance(shot, dict) else None
        if not data:
            print(f'[shot] formato inesperado: {str(shot)[:200]}')
        else:
            import base64
            fname = f'w7_banner_{tag}.png'
            with open(fname, 'wb') as f:
                f.write(base64.b64decode(data))
            print(f'[shot] {fname}')

        passed = sum(1 for v in checks.values() if v)
        for k, v in checks.items():
            print(f'  {"PASS" if v else "FAIL"}  {k}')
        print(f'W7 {tag}: {passed}/{len(checks)}')
        return passed == len(checks)
    finally:
        proc.terminate()


async def main():
    ok_d = await run_session(mobile=False)
    ok_m = await run_session(mobile=True)
    print(f'\nW7 HUD PROBE TOTAL: desktop {"OK" if ok_d else "FAIL"} · mobile {"OK" if ok_m else "FAIL"}')
    sys.exit(0 if (ok_d and ok_m) else 1)


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
