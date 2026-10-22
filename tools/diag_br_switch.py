"""Diag M03/M08: o que __matchState realmente expoe, e o que acontece ao
startMatch('br_vila') a partir de um 3v3 ATIVO (caso da suite, diferente do
probe_pv2 que partia do lobby). Run: python tools/diag_br_switch.py
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

PROFILE = tempfile.mkdtemp(prefix='nuba_diagbr_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', '--remote-debugging-port=9222', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
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
                return "JSERR:" + str((exc.get("exception") or {}).get("description") or exc.get("text"))[:200]
            return res.get("result", {}).get("value")
        return await c.eval_js(expr)

    for _ in range(40):
        if await ev("typeof window.startMatch") == 'function':
            break
        await asyncio.sleep(0.5)

    r = await ev("(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True)
    print('[3v3] start ->', r)
    for _ in range(40):
        if await ev('window.units ? window.units.length : -1') == 6:
            break
        await asyncio.sleep(0.4)
    d = await ev("""(() => ({
        keys: window.__matchState ? Object.keys(window.__matchState) : null,
        mode: window.__matchState ? window.__matchState.mode : 'NO_STATE',
        cfg: window.__matchState && window.__matchState.cfg ? Object.keys(window.__matchState.cfg) : null,
        units: window.units.length, active: window.matchActive
    }))()""")
    print('[3v3] matchState:', d)

    t0 = time.time()
    r = await ev("(async () => { try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", ap=True, timeout=90)
    t1 = time.time()
    print(f"[br] startMatch a partir do 3v3 ATIVO -> {r}  ({t1-t0:.1f}s)")
    d2 = await ev("""(() => ({
        units: window.units ? window.units.length : null,
        active: window.matchActive,
        br: window.__matchState ? !!window.__matchState.br : null,
        brKeys: (window.__matchState && window.__matchState.br) ? Object.keys(window.__matchState.br) : null,
        arena: window.__ARENA_LOADED ? window.__ARENA_LOADED.asset : null
    }))()""")
    print('[br] estado:', d2)
    errs = len(c.console_errors)
    print(f'console errors: {errs}')
    for e in c.console_errors[:5]:
        print('  ', str(e)[:180])
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
