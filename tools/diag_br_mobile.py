"""Diag M08 mobile: reproduz a sequencia EXATA da suite sob emulacao iPhone
(M01 boot -> M03 3v3 -> M08 br_vila) cronometrando cada passo com timeout 90s.
Run: python tools/diag_br_mobile.py
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402

UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) '
      'AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1')

PROFILE = tempfile.mkdtemp(prefix='nuba_diagbrm_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', '--remote-debugging-port=9222', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'about:blank'
])
time.sleep(2.5)


def http_json(path):
    with urllib.request.urlopen(f'http://127.0.0.1:9222{path}', timeout=5) as r:
        return json.load(r)


async def main():
    for _ in range(20):
        try:
            tabs = http_json('/json')
            break
        except Exception:
            time.sleep(0.5)
    ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws)
    await c.connect()

    async def ev(expr, ap=False, timeout=30.0):
        if ap:
            res = await c.send("Runtime.evaluate", {
                "expression": expr, "returnByValue": True, "awaitPromise": True}, timeout=timeout)
            exc = res.get("exceptionDetails")
            if exc:
                return "JSERR:" + str((exc.get("exception") or {}).get("description") or exc.get("text"))[:160]
            return res.get("result", {}).get("value")
        return await c.eval_js(expr)

    # --- M01: emulacao mobile + reload ---
    await c.send("Emulation.setDeviceMetricsOverride",
                 {"width": 844, "height": 390, "deviceScaleFactor": 2, "mobile": True})
    await c.send("Emulation.setUserAgentOverride", {"userAgent": UA})
    for _ in range(10):
        if await ev("/iPhone/.test(navigator.userAgent)"):
            break
        await asyncio.sleep(0.3)
    t0 = time.time()
    await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
    for _ in range(40):
        if await ev("typeof window.startMatch") == 'function':
            break
        await asyncio.sleep(0.5)
    print(f"[M01] boot mobile: {time.time()-t0:.1f}s")
    await ev("document.body.classList.add('touch')")
    d = await ev("""(() => ({ isMobile: !!window.__DEVICE && window.__DEVICE.isMobile,
        dprCap: window.__GOV.dprCap, vfxCap: window.__GOV.vfxCap }))()""")
    print("[M01] governor:", d)
    t0 = time.time()
    while not await ev("!!window.__ARENA_LOADED"):
        await asyncio.sleep(0.5)
    print(f"[M02] arena: {await ev('window.__ARENA_LOADED.asset')} meshes={await ev('window.__ARENA_LOADED.meshes')} ({time.time()-t0:.1f}s)")

    # --- M03: 3v3 ---
    t0 = time.time()
    r = await ev("(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True, timeout=60)
    print(f"[M03] startMatch 3v3 -> {r} ({time.time()-t0:.1f}s)")
    t0 = time.time()
    while await ev('window.units ? window.units.length : -1') != 6:
        await asyncio.sleep(0.4)
    print(f"[M03] 6 units em {time.time()-t0:.1f}s")

    # --- M08: BR a partir do 3v3 ATIVO, mobile ---
    t0 = time.time()
    r = await ev("(async () => { try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True, timeout=90)
    dt = time.time() - t0
    print(f"[M08] startMatch br_vila -> {r}  ({dt:.1f}s)")
    t0 = time.time()
    n = -1
    for _ in range(60):
        n = await ev('window.units ? window.units.length : -1')
        if n == 10:
            break
        await asyncio.sleep(0.4)
    print(f"[M08] units: {n} ({time.time()-t0:.1f}s)")
    d = await ev("""(() => ({ br: window.__matchState.br ? {
            zoneR: window.__matchState.br.zoneR, zoneMin: window.__matchState.br.zoneMin,
            chests: window.__matchState.br.chests.length, alive: window.__matchState.br.alive,
            phase: window.__matchState.br.phase } : null,
        arena: window.__ARENA_LOADED ? window.__ARENA_LOADED.asset : null,
        hud: getComputedStyle(document.getElementById('br-hud')).display }))()""")
    print("[M08] br:", d)
    print(f"console errors: {len(c.console_errors)}")
    for e in c.console_errors[:4]:
        print('  ', str(e)[:170])
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
