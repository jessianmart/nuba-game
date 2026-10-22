"""Probe PV4.2 v2 — banners leves no touch + zoom afastado.
Correcoes vs v1 (aprendidas do traceback):
  - game.js e MODULO: showBanner/showStreakBanner nao estao no window. Banners
    sao disparados pelo CAMINHO REAL: window.dealDamage (exposto) -> kill ->
    streak (SEQUENCIA) + center-banner ("VOCE ELIMINOU...").
  - Headless nao expoe maxTouchPoints -> __DEVICE.isTouch=false e a camera
    ficava em MODO MOBA (38 alto + 32 atras = ~49.6 de distancia, medido).
    No device real isTouch=true liga o thirdperson no startMatch (L1790). O probe
    seta __DEVICE.isTouch=true ANTES do startMatch para reproduzir o device.
  - Estilos computados (font-size/padding/min-width) sao o alvo duro do patch e
    podem ser lidos mesmo com banner oculto; visibilidade/rect sao bonus.
Run: python tools/probe_pv4_2_v2.py   (cwd = repo root)
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
    profile = tempfile.mkdtemp(prefix='nuba_pv42_')
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
        # device real: isMobile (UA) E isTouch -> thirdperson no startMatch
        await ev(c, "document.body.classList.add('touch'); window.__DEVICE.isTouch = true;")
        ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
        assert ok == 'ok', f'startMatch: {ok}'
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.4)
        await asyncio.sleep(2.2)  # intro/camera converge

        # ---- [1] zoom: distancia camera<->player no modo thirdperson ----
        d = await ev(c, """(() => {
            const cam = window.__camera, p = window.units.find(u => u.isPlayer);
            if (!cam || !p) return null;
            const m = p.mesh ? p.mesh.position : { x: p.x, y: 1.6, z: p.z };
            return Math.hypot(cam.position.x - m.x, cam.position.y - m.y, cam.position.z - m.z);
        })()""")
        mode = await ev(c, "window.__camera ? (window.__camera.position.y > 20 ? 'moba?' : 'tp') : 'sem cam'")
        print(f'[1] distancia camera<->player: {d} ({mode})')

        # ---- [2] banners pelo CAMINHO REAL: 2 kills -> streak + center-banner ----
        await ev(c, """(() => {
            const p = window.units.find(u => u.isPlayer);
            const foes = window.units.filter(u => u.team !== p.team).slice(0, 2);
            for (const f of foes) { f.spawnShield = 0; window.dealDamage(p, f, 99999, 'probe'); }
            return foes.length;
        })()""")
        await asyncio.sleep(0.8)
        b = await ev(c, """(() => {
            const el = document.getElementById('center-banner');
            const cs = getComputedStyle(el), r = el.getBoundingClientRect();
            return { fs: cs.fontSize, padX: cs.paddingLeft, bw: cs.borderTopWidth,
                     visible: !el.classList.contains('hidden'),
                     top: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height),
                     inView: r.left >= 0 && r.right <= window.innerWidth,
                     txt: el.textContent.slice(0, 24) };
        })()""")
        print(f'[2] center-banner: {b}')
        s = await ev(c, """(() => {
            const el = document.getElementById('streak-banner');
            const k = getComputedStyle(el.querySelector('.streak-kanji'));
            const t = getComputedStyle(el.querySelector('.streak-text'));
            const n = getComputedStyle(el.querySelector('.streak-count'));
            const cs = getComputedStyle(el), r = el.getBoundingClientRect();
            return { kanji: k.fontSize, txt: t.fontSize, count: n.fontSize,
                     minW: cs.minWidth, padX: cs.paddingLeft, bw: cs.borderTopWidth,
                     visible: !el.classList.contains('hidden'),
                     w: Math.round(r.width), label: el.querySelector('.streak-text').textContent };
        })()""")
        print(f'[3] streak-banner: {s}')

        shot = await c.send("Page.captureScreenshot", {"format": "png"})
        open(os.path.join(os.environ.get('TEMP', '.'), 'nuba_pv42_banners.png'), 'wb').write(
            base64.b64decode(shot['data']))

        def px(v):
            try:
                return float(str(v).replace('px', ''))
            except Exception:
                return -1

        checks = {
            'camera-exposta': d is not None,
            'zoom-afastado-16': d is not None and 14.5 <= d <= 18.5,
            'ult-fonte-leve': px(b['fs']) <= 16,
            'ult-padding-leve': px(b['padX']) <= 26,
            'ult-moldura-fina': px(b['bw']) <= 9,
            'seq-kanji-leve': px(s['kanji']) <= 20,
            'seq-texto-leve': px(s['txt']) <= 14,
            'seq-contador-leve': px(s['count']) <= 28,
            'seq-caixa-leve': px(s['minW']) <= 240 and px(s['padX']) <= 26,
            'seq-moldura-fina': px(s['bw']) <= 9,
        }
        # bonus (nao derrubam): banners visiveis pelo caminho real
        if b['visible']:
            checks['ult-visivel-e-dentro'] = b['inView'] is True
            print(f"    (ult visivel: '{b['txt']}')")
        else:
            print('    (ult oculto no instante da leitura — estilos computados valem)')
        if s['visible']:
            print(f"    (sequencia visivel: '{s['label']}' w={s['w']}px)")
        print('=== PV4.2 CHECKS ===')
        for k, v in checks.items():
            print(f"  {'OK ' if v else 'FALHA'} {k}")
        errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)
                and 'vibrate' not in str(e)]  # vibrate sem user-gesture e bloqueio headless (PV3.3 correto)
        print(f'  console errors (filtrado): {len(errs)}')
        bad = [k for k, v in checks.items() if not v] + (['console'] if errs else [])
        assert not bad, f'PV4.2 falhou: {bad}'
        c.running = False
        print('PV4.2 PROBE PASS')
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        import shutil  # noqa: E402
        shutil.rmtree(profile, ignore_errors=True)


asyncio.run(main())
