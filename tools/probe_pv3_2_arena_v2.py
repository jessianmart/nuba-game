"""Probe PV3.2 v2 — variante mobile da arena default sd00a.
Cada sessao roda em PROCESSO Edge INDEPENDENTE (o run anterior no mesmo processo
inv ertia os numeros — estado/ordem compartilhada). Fonte de verdade:
`window.__ARENA_LOADED` (asset + meshes) exposto pela instrumentacao do game.js.
Run: python tools/probe_pv3_2_arena_v2.py   (cwd = repo root)
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

IPHONE_UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
             'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')
DESK_UA = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
           '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')


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


async def session(ua, w, h, label):
    """processo Edge proprio -> sem estado compartilhado entre sessoes."""
    port = free_port()
    profile = tempfile.mkdtemp(prefix=f'nuba_pv32{label}_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        f'--window-size={w},{h}', '--inprivate', f'--user-data-dir={profile}', 'about:blank'
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
        ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws_url)
        await c.connect()
        await c.send("Emulation.setUserAgentOverride", {"userAgent": ua})
        await c.send("Emulation.setDeviceMetricsOverride",
                     {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": 'iPhone' in ua})
        await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
        for _ in range(40):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        # espera a ARENA carregar (telemetria) antes de medir
        for _ in range(40):
            if await ev(c, 'window.__ARENA_LOADED ? 1 : 0') == 1:
                break
            await asyncio.sleep(0.3)
        await ev(c, "document.body.classList.add('touch')")
        ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        assert ok == 'ok', f'{label} startMatch: {ok}'
        for _ in range(40):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.3)
        await asyncio.sleep(1.2)
        r = await ev(c, """(() => {
          const snap = window.__PERF.snapshot();
          return { arena: window.__ARENA_LOADED || null, triangles: snap.triangles,
                   drawCalls: snap.drawCalls, geometries: snap.geometries,
                   isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile),
                   vfxCap: window.__GOV ? window.__GOV.vfxCap : null };
        })()""")
        errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
        c.running = False
        r['errors'] = len(errs)
        print(f"--- {label} ---")
        print(f"  arena carregada: {r['arena']}")
        print(f"  triangles={r['triangles']} drawCalls={r['drawCalls']} geometries={r['geometries']} "
              f"isMobile={r['isMobile']} vfxCap={r['vfxCap']} errors={r['errors']}")
        return r
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        import shutil  # noqa: E402
        shutil.rmtree(profile, ignore_errors=True)


async def main():
    mob = await session(IPHONE_UA, 844, 390, 'mobile')
    desk = await session(DESK_UA, 1280, 720, 'desktop')

    a_m, a_d = mob['arena'], desk['arena']
    checks = {
        'mobile-carrega-variante': bool(a_m) and a_m['asset'].endswith('sd00a.mobile.json'),
        'mobile-meshes-33': bool(a_m) and a_m['meshes'] == 33,
        'mobile-detectado': mob['isMobile'] is True,
        'desktop-carrega-full': bool(a_d) and a_d['asset'].endswith('stage/arena/sd00a.json'),
        'desktop-meshes-122': bool(a_d) and a_d['meshes'] == 122,
        'desktop-nao-e-mobile': desk['isMobile'] is False,
        'mobile-renderiza-menos-tris': mob['triangles'] is not None and desk['triangles'] is not None and mob['triangles'] < desk['triangles'],
        'mobile-renderiza-menos-drawcalls': mob['drawCalls'] is not None and desk['drawCalls'] is not None and mob['drawCalls'] < desk['drawCalls'],
        'zero-console-errors': mob['errors'] == 0 and desk['errors'] == 0,
    }
    print('=== PV3.2 CHECKS ===')
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FALHA'} {k}")
    bad = [k for k, v in checks.items() if not v]
    assert not bad, f'PV3.2 falhou: {bad}'
    print(f"resumo: mobile {a_m['meshes'] if a_m else '?'} meshes / {mob['drawCalls']} draw calls  vs  "
          f"desktop {a_d['meshes'] if a_d else '?'} meshes / {desk['drawCalls']} draw calls")
    print('PV3.2 ARENA PROBE PASS')


asyncio.run(main())
