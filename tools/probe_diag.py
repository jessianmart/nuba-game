"""Diag PV1-B — quem recebe o touch sintetico? elementFromPoint + log de eventos + emulacao."""
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
PROFILE = tempfile.mkdtemp(prefix='nuba_diag_')
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


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json('/json')
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()

    await ev(c, "document.body.classList.add('touch')")
    await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    for _ in range(60):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 6:
            break
        await asyncio.sleep(0.5)

    # 1) quem esta no topo em (250,480)?
    top = await ev(c, """(() => {
        const el = document.elementFromPoint(250, 480);
        const joy = document.getElementById('touch-joystick').getBoundingClientRect();
        return {
            topTag: el ? el.tagName : null,
            topId: el ? (el.id || '') : '',
            topCls: el ? (typeof el.className === 'string' ? el.className : '').slice(0, 60) : '',
            joyRect: { l: joy.left, t: joy.top, w: joy.width, h: joy.height },
            joyDisplay: getComputedStyle(document.getElementById('touch-joystick')).display,
            joyPointerEvents: getComputedStyle(document.getElementById('touch-joystick')).pointerEvents
        };
    })()""")
    print('[top]', json.dumps(top))

    # 2) log de eventos no document (captura tudo)
    await ev(c, """(() => {
        window.__evts = [];
        const name = (t) => (t.id ? '#' + t.id : (typeof t.className === 'string' && t.className) ? '.' + t.className.split(' ')[0] : t.tagName);
        ['pointerdown','pointermove','pointerup','touchstart','touchmove','touchend'].forEach(k => {
            document.addEventListener(k, (e) => {
                window.__evts.push([k, name(e.target), Math.round(e.clientX || 0), Math.round(e.clientY || 0)]);
            }, { capture: true, passive: false });
        });
        return 'armed';
    })()""")

    # 3) tenta SEM emulacao
    await c.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': 250, 'y': 480, 'id': 1}]})
    await asyncio.sleep(0.15)
    await c.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': 340, 'y': 400, 'id': 1}]})
    await asyncio.sleep(0.15)
    await c.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    await asyncio.sleep(0.2)
    raw = await ev(c, 'window.__evts')
    print('[sem emulacao]', json.dumps(raw)[:400])

    # 4) tenta COM emulacao
    await ev(c, 'window.__evts.length = 0')
    await c.send('Emulation.setTouchEmulationEnabled', {'enabled': True, 'maxTouchPoints': 5})
    await c.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': 250, 'y': 480, 'id': 1}]})
    await asyncio.sleep(0.15)
    await c.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': 340, 'y': 400, 'id': 1}]})
    await asyncio.sleep(0.15)
    await c.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    await asyncio.sleep(0.2)
    raw2 = await ev(c, 'window.__evts')
    print('[com emulacao]', json.dumps(raw2)[:400])
    inp = await ev(c, '({ mx: window.INPUT.moveX, mz: window.INPUT.moveZ })')
    print('[INPUT pos-move]', json.dumps(inp))
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
