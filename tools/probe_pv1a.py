"""Probe PV1-A — valida dm_3v3 vs dm_legacy_5v5 sem rodar a suite inteira.

Requer :8080 LISTENING. Lanca Edge headless proprio (porta livre), usa CDPClient da suite.
Run: python probe_pv1a.py   (cwd = repo root)
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_probe_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(2.5)


def http_json(path):
    with urllib.request.urlopen(f'http://127.0.0.1:{PORT}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:  # defesa contra formato raw
        v = v['value']
    if v == {} or v is None:
        raise RuntimeError(f'eval devolveu vazio (provavel exceptionDetails): {expr[:80]}')
    return v


async def wait_units(c, n, tries=60):
    got = -1
    for _ in range(tries):
        try:
            got = await ev(c, "window.units ? window.units.length : -1")
        except RuntimeError:
            got = -1
        if got == n:
            return n
        await asyncio.sleep(0.5)
    raise AssertionError(f'esperava {n} unidades, ultima leitura: {got}')


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json('/json')
            break
        except Exception:
            time.sleep(0.5)
    assert tabs, 'Edge /json nao respondeu'
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()

    r = await ev(c, "typeof window.startMatch === 'function' && typeof window.start5v5Match === 'function' && typeof window.INPUT === 'object' && !!window.__DEVICE")
    assert r is True, f'API por modo / PV0 hooks ausentes: {r}'
    print('[1] hooks ok: startMatch + alias legacy + INPUT + __DEVICE')

    # ---- dm_3v3 ----
    await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    await wait_units(c, 6)
    d = await ev(c, """(() => ({
        b: document.querySelectorAll('#hud-blue-icons .mini-p').length,
        r: document.querySelectorAll('#hud-red-icons .mini-p').length,
        goal: (document.querySelector('.match-goal-txt')||{}).textContent || '',
        mtime: (window.__matchState ? window.__matchState.time : -1),
        blue: window.units.filter(u=>u.team==='blue').length,
        red: window.units.filter(u=>u.team==='red').length
    }))()""")
    assert d['b'] == 3 and d['r'] == 3, f'retratos 3v3 errados: {d}'
    assert d['blue'] == 3 and d['red'] == 3, f'times 3v3 errados: {d}'
    assert 'META: 15' in d['goal'], f'goal 3v3: {d["goal"]!r}'
    assert 174 <= d['mtime'] <= 181, f'tempo 3v3: {d["mtime"]!r}'
    print(f'[2] dm_3v3 OK: retratos 3+3, unidades 3+3, goal={d["goal"]!r}, tempo={d["mtime"]:.0f}s')

    # ---- legacy 5v5 (contrato E2E) ----
    await ev(c, "(async () => { try { await window.start5v5Match(); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    await wait_units(c, 10)
    d2 = await ev(c, """(() => ({
        b: document.querySelectorAll('#hud-blue-icons .mini-p').length,
        r: document.querySelectorAll('#hud-red-icons .mini-p').length,
        goal: (document.querySelector('.match-goal-txt')||{}).textContent || '',
        mtime: (window.__matchState ? window.__matchState.time : -1)
    }))()""")
    assert d2['b'] == 5 and d2['r'] == 5, f'retratos legacy errados: {d2}'
    assert 'META: 30' in d2['goal'], f'goal legacy: {d2["goal"]!r}'
    assert 294 <= d2['mtime'] <= 301, f'tempo legacy: {d2["mtime"]!r}'
    print(f'[3] legacy 5v5 OK (contrato E2E preservado): 5+5, goal={d2["goal"]!r}, tempo={d2["mtime"]:.0f}s')

    # ---- seletor de modo no lobby ----
    d3 = await ev(c, """(() => {
        const chips = document.querySelectorAll('#mode-picker .mode-chip');
        const sel = document.querySelector('#mode-picker .mode-chip.selected');
        return { n: chips.length, selMode: sel ? sel.dataset.mode : null,
                 brDisabled: !!document.querySelector('#mode-picker .mode-chip[data-mode="br_vila"]').disabled };
    })()""")
    assert d3['n'] == 3 and d3['selMode'] == 'dm_3v3' and d3['brDisabled'], f'mode picker: {d3}'
    print('[4] #mode-picker OK: 3 chips, dm_3v3 selecionado, BR desabilitado')

    errs = list(c.console_errors)
    assert not errs, f'console errors: {errs[:5]}'
    print('PROBE PV1-A PASS — 0 erros de console')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(PROFILE, ignore_errors=True)
