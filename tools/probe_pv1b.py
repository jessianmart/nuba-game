"""Probe PV1-B — valida controles touch via CDP Input.dispatchTouchEvent.

Simula body.touch, inicia dm_3v3, testa joystick (vetor INPUT), botao ATK (fire hold),
skill Q (cooldown via executeSkill) e chakra hold. Requer :8080 LISTENING.
Run: python probe_pv1b.py   (cwd = repo root)
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
PROFILE = tempfile.mkdtemp(prefix='nuba_probe1b_')
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
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def touch(c, evtype, x, y, tid=1):
    await c.send('Input.dispatchTouchEvent', {
        'type': evtype,
        'touchPoints': [{'x': x, 'y': y, 'id': tid, 'force': 1.0}]
    })


async def wait_units(c, n, tries=60):
    got = -1
    for _ in range(tries):
        try:
            got = await ev(c, 'window.units ? window.units.length : -1')
        except RuntimeError:
            got = -1
        if got == n:
            return
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

    await ev(c, "document.body.classList.add('touch')")
    await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    await wait_units(c, 6)
    print('[1] dm_3v3 ativo com body.touch')

    # ---- visibilidade ----
    vis = await ev(c, """(() => {
        const tc = document.getElementById('touch-controls');
        const r = tc ? getComputedStyle(tc).display : 'missing';
        document.body.classList.remove('touch');
        const hidden = getComputedStyle(tc).display;
        document.body.classList.add('touch');
        return { shown: r, hidden };
    })()""")
    assert vis['shown'] == 'block', f'touch-controls deveria aparecer com body.touch: {vis}'
    assert vis['hidden'] == 'none', f'touch-controls deveria sumir sem body.touch: {vis}'
    print('[2] gate CSS ok: visivel so com body.touch')

    # ---- joystick ----
    await touch(c, 'touchStart', 250, 480)
    await asyncio.sleep(0.1)
    await touch(c, 'touchMove', 340, 400)
    await asyncio.sleep(0.1)
    j = await ev(c, '({ mx: window.INPUT.moveX, mz: window.INPUT.moveZ })')
    assert j['mx'] > 0.3, f'joystick deveria apontar a direita: {j}'
    assert j['mz'] > 0.3, f'joystick deveria apontar pra frente (moveZ+): {j}'
    px0 = await ev(c, 'window.units.find(u => u.isPlayer).x')
    await asyncio.sleep(0.8)
    px1 = await ev(c, 'window.units.find(u => u.isPlayer).x')
    assert px1 > px0 + 0.3, f'unidade deveria mover +X com joystick a direita: {px0} -> {px1}'
    await touch(c, 'touchEnd', 340, 400)
    await asyncio.sleep(0.15)
    j2 = await ev(c, '({ mx: window.INPUT.moveX, mz: window.INPUT.moveZ })')
    assert j2['mx'] == 0 and j2['mz'] == 0, f'INPUT deveria zerar ao soltar: {j2}'
    print(f'[3] joystick ok: vetor ({j["mx"]:.2f}, {j["mz"]:.2f}), player {px0:.1f}->{px1:.1f}, reset limpo')

    # ---- ATK hold ----
    atk = await ev(c, """(() => { const r = document.getElementById('tbtn-atk').getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()""")
    await touch(c, 'touchStart', atk['x'], atk['y'])
    await asyncio.sleep(0.1)
    fire = await ev(c, 'window.INPUT.fire')
    assert fire is True, f'ATK hold deveria setar INPUT.fire: {fire}'
    cd0 = await ev(c, 'window.units.find(u => u.isPlayer).cds.atk')
    await touch(c, 'touchEnd', atk['x'], atk['y'])
    fire2 = await ev(c, 'window.INPUT.fire')
    assert fire2 is False, f'soltar ATK deveria zerar fire: {fire2}'
    print(f'[4] ATK ok: fire hold true->false, cds.atk={cd0}')

    # ---- skill Q (tap = executeSkill) ----
    q = await ev(c, """(() => { const r = document.getElementById('tbtn-q').getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2, cd: window.units.find(u => u.isPlayer).cds.q }; })()""")
    assert q['cd'] <= 0, 'pre-condicao: cd.q zerado no spawn'
    await touch(c, 'touchStart', q['x'], q['y'])
    await touch(c, 'touchEnd', q['x'], q['y'])
    await asyncio.sleep(0.1)
    cdq = await ev(c, 'window.units.find(u => u.isPlayer).cds.q')
    assert cdq > 0, f'tap no Q deveria disparar executeSkill (cd): {cdq}'
    print(f'[5] skill Q ok: tap -> executeSkill, cd.q {q["cd"]} -> {cdq:.2f}')

    # ---- chakra hold ----
    cc = await ev(c, """(() => { const r = document.getElementById('tbtn-c').getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()""")
    await touch(c, 'touchStart', cc['x'], cc['y'])
    await asyncio.sleep(0.1)
    chk = await ev(c, 'window.INPUT.chakra')
    assert chk is True, f'hold chakra deveria setar INPUT.chakra: {chk}'
    ck0 = await ev(c, 'window.units.find(u => u.isPlayer).chakra')
    await asyncio.sleep(0.8)
    ck1 = await ev(c, 'window.units.find(u => u.isPlayer).chakra')
    await touch(c, 'touchEnd', cc['x'], cc['y'])
    chk2 = await ev(c, 'window.INPUT.chakra')
    assert chk2 is False, 'soltar chakra deveria zerar flag'
    assert ck1 > ck0, f'chakra deveria carregar segurando o botao: {ck0} -> {ck1}'
    print(f'[6] chakra ok: hold carrega ({ck0:.0f} -> {ck1:.0f}), release limpo')

    errs = list(c.console_errors)
    assert not errs, f'console errors: {errs[:5]}'
    print('PROBE PV1-B PASS — 0 erros de console')
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
