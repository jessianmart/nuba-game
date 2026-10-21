"""Probe PV3.2 — variante mobile da arena default sd00a.
Roda 2 sessoes no mesmo Edge (UA trocado + reload): mobile DEVE buscar
sd00a.mobile.json?v=10 (33 meshes) e renderizar menos triangulos; desktop DEVE
manter sd00a.json?v=10 (122 meshes).
Run: python tools/probe_pv3_2_arena.py   (cwd = repo root)
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


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_pv32_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=844,390', '--inprivate', f'--user-data-dir={PROFILE}', 'about:blank'
])
time.sleep(3)


async def session(c, ua, w, h, label):
    """navega + inicia 3v3 e devolve o que a arena pediu/renderizou."""
    # buffer de resource timing maior: o boot pede centenas de texturas/modelos e
    # o default (250) descarta as entradas ANTIGAS — a arena sai do buffer.
    await c.send("Page.addScriptToEvaluateOnNewDocument",
                 {"source": "performance.setResourceTimingBufferSize(3000);"})
    await c.send("Emulation.setUserAgentOverride", {"userAgent": ua})
    await c.send("Emulation.setDeviceMetricsOverride",
                 {"width": w, "height": h, "deviceScaleFactor": 1, "mobile": 'iPhone' in ua})
    await c.send("Page.navigate", {"url": f"http://localhost:8080/index.html?probe={label}"})
    for _ in range(40):
        if await ev(c, 'typeof window.startMatch') == 'function':
            break
        await asyncio.sleep(0.5)
    await ev(c, "document.body.classList.add('touch')")
    ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'{label} startMatch: {ok}'
    for _ in range(40):
        if await ev(c, 'window.units ? window.units.length : -1') == 6:
            break
        await asyncio.sleep(0.3)
    await asyncio.sleep(1.2)
    r = await ev(c, """(() => {
      const res = performance.getEntriesByType('resource').map(e => e.name);
      const arena = res.filter(n => /stage\\/arena\\/sd00a/.test(n));
      const snap = window.__PERF.snapshot();
      return { arenaReqs: arena, triangles: snap.triangles, drawCalls: snap.drawCalls,
               isMobile: !!(window.__DEVICE && window.__DEVICE.isMobile),
               vfxCap: window.__GOV ? window.__GOV.vfxCap : null };
    })()""")
    print(f"--- {label} ---")
    print(f"  requests da arena: {r['arenaReqs']}")
    print(f"  triangles={r['triangles']} drawCalls={r['drawCalls']} isMobile={r['isMobile']} vfxCap={r['vfxCap']}")
    return r


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

    mob = await session(c, IPHONE_UA, 844, 390, 'mobile')
    desk = await session(c, DESK_UA, 1280, 720, 'desktop')

    checks = {
        'mobile-pede-variante': any('sd00a.mobile.json?v=10' in u for u in mob['arenaReqs']),
        'mobile-nao-pede-full': not any(u.endswith('sd00a.json?v=10') for u in mob['arenaReqs']),
        'mobile-detectado': mob['isMobile'] is True,
        'desktop-pede-full': any(u.endswith('sd00a.json?v=10') for u in desk['arenaReqs']),
        'desktop-nao-pede-mobile': not any('sd00a.mobile.json' in u for u in desk['arenaReqs']),
        'desktop-nao-e-mobile': desk['isMobile'] is False,
        'mobile-renderiza-menos-tris': mob['triangles'] is not None and desk['triangles'] is not None and mob['triangles'] < desk['triangles'],
        'mobile-renderiza-menos-drawcalls': mob['drawCalls'] is not None and desk['drawCalls'] is not None and mob['drawCalls'] < desk['drawCalls'],
    }
    print('=== PV3.2 CHECKS ===')
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FALHA'} {k}")
    bad = [k for k, v in checks.items() if not v]
    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    print(f"  console errors (filtrado): {len(errs)}")
    assert not bad, f'PV3.2 falhou: {bad}'
    assert len(errs) == 0, f'console errors: {errs[:3]}'
    print('PV3.2 ARENA PROBE PASS')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    import shutil  # noqa: E402
    shutil.rmtree(PROFILE, ignore_errors=True)
