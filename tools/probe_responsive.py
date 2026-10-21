"""Probe responsividade (PV3) — viewport mobile real via CDP DeviceMetrics.
Cobre: rotate overlay portrait, overflow horizontal, HUD top bar <52px,
touch controls dentro da tela + sem overlap + tap targets >=44px, BR-hud.
Run: python tools/probe_responsive.py   (cwd = repo root)
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


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_resp_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=390,844', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

# viewports landscape (telefones reusados por emulacao)
LANDS = [
    ('SE-land',    568, 320),   # iPhone SE 1a geracao landscape
    ('iPhone8',    667, 375),   # iPhone 8 landscape
    ('iPhone12',   844, 390),   # iPhone 12/13 landscape
    ('iPhone11',   896, 414),   # iPhone 11 Pro Max landscape
    ('GalaxyS',    740, 360),   # Galaxy S8 landscape
]
PORTS = [('iPhone12-portrait', 390, 844), ('iPhone8-portrait', 375, 667)]


async def set_vp(c, w, h, mobile=True):
    await c.send("Emulation.setDeviceMetricsOverride", {
        "width": w, "height": h, "deviceScaleFactor": 2, "mobile": mobile
    })
    await asyncio.sleep(0.25)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


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
    for _ in range(40):
        t = await ev(c, 'typeof window.startMatch')
        if t == 'function':
            break
        await asyncio.sleep(0.5)
    await ev(c, "document.body.classList.add('touch')")

    # ---------- [P] PORTRAIT: overlay de rotacao obrigatorio ----------
    for name, w, h in PORTS:
        await set_vp(c, w, h)
        r = await ev(c, "(() => { const o = document.getElementById('rotate-overlay'); return o ? getComputedStyle(o).display : 'MISSING'; })()")
        assert r == 'flex', f'{name}: rotate overlay deveria estar flex, veio {r}'
        print(f'[P] {name} ({w}x{h} portrait): overlay "gire o dispositivo" ATIVO')

    # ---------- [L] LANDSCAPE: partida jogavel ----------
    await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    for _ in range(30):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 6:
            break
        await asyncio.sleep(0.3)

    results = []
    for name, w, h in LANDS:
        await set_vp(c, w, h)
        r = await ev(c, """(() => {
          const de = document.documentElement;
          const bar = document.querySelector('.hud-top-bar') || document.querySelector('.hud-top');
          const bh = bar ? bar.getBoundingClientRect() : null;
          const grpB = document.querySelector('.team-group.blue');
          const grpR = document.querySelector('.team-group.red');
          const ctr = document.querySelector('.match-center-cluster');
          const joy = document.getElementById('touch-joystick');
          const clu = document.getElementById('touch-cluster');
          const overlay = document.getElementById('rotate-overlay');
          const rects = {};
          for (const [k, el] of Object.entries({ grpB, grpR, ctr, joy, clu })) {
            if (!el) continue;
            const b = el.getBoundingClientRect();
            rects[k] = { l: Math.round(b.left), r: Math.round(b.right), b: Math.round(b.bottom), t: Math.round(b.top),
                         vis: getComputedStyle(el).display !== 'none' && b.width > 0 && b.height > 0 };
          }
          const btns = [...document.querySelectorAll('.tbtn')].map(b => {
            const bb = b.getBoundingClientRect();
            return { w: Math.round(bb.width), h: Math.round(bb.height) };
          });
          return {
            scrollW: de.scrollWidth, clientW: de.clientWidth, innerW: window.innerWidth, innerH: window.innerHeight,
            barH: bh ? Math.round(bh.height * 100) / 100 : null,
            rects, btns,
            overlayDisplay: overlay ? getComputedStyle(overlay).display : 'MISSING'
          };
        })()""")
        def _in(k):
            rr = r['rects'].get(k)
            return rr is not None and rr.get('vis') and rr['r'] <= r['innerW'] + 1 and rr['l'] >= -1
        checks = {
            'no-h-overflow': r['scrollW'] <= r['innerW'] + 1,
            'bar<52px': r['barH'] is not None and r['barH'] < 52,
            'overlay-hidden': r['overlayDisplay'] == 'none',
            # PV4: team-groups ficam ocultos por design no touch — escondido = OK;
            # se visiveis, precisam estar nos bounds. Centro (timer/BR) DEVE aparecer.
            'hud-hidden-or-bounded': all(
                (not r['rects'].get(k, {}).get('vis')) or (
                    r['rects'][k]['r'] <= r['innerW'] + 1 and r['rects'][k]['l'] >= -1)
                for k in ('grpB', 'grpR') if k in r['rects']),
            'center-timer-visible': _in('ctr'),
            'touch-in-bounds': all(
                r['rects'].get(k, {}).get('vis') and r['rects'][k]['r'] <= r['innerW'] + 1 and r['rects'][k]['b'] <= r['innerH'] + 1
                for k in ('joy', 'clu') if k in r['rects']),
            'no-joy-cluster-overlap': 'joy' in r['rects'] and 'clu' in r['rects'] and r['rects']['joy']['r'] <= r['rects']['clu']['l'] + 1,
            'tap-targets>=44': len(r['btns']) == 6 and all(b['w'] >= 44 and b['h'] >= 44 for b in r['btns']),
        }
        bad = [k for k, v in checks.items() if not v]
        status = 'OK ' if not bad else 'FALHA: ' + ','.join(bad)
        results.append((name, status))
        print(f"[L] {name} ({w}x{h}): {status} | bar={r['barH']}px scrollW={r['scrollW']}/{r['innerW']} botoes={[(b['w'], b['h']) for b in r['btns']]}")

    # ---------- [BR] modo BR no 390x844 ----------
    await set_vp(c, 844, 390)
    ok = await ev(c, "(async () => { try { await window.startMatch('br_vila'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'BR startMatch: {ok}'
    r = await ev(c, """(() => {
      const de = document.documentElement;
      const hud = document.getElementById('br-hud');
      const hb = hud ? hud.getBoundingClientRect() : null;
      return { scrollW: de.scrollWidth, innerW: window.innerWidth, brHudVisible: hud ? getComputedStyle(hud).display !== 'none' : false, brHudRight: hb ? Math.round(hb.right) : null };
    })()""")
    okbr = r['scrollW'] <= r['innerW'] + 1 and r['brHudVisible'] and (r['brHudRight'] or 0) <= r['innerW'] + 1
    print(f"[BR] 390x844 landscape: HUD VIVOS/FASE visivel={r['brHudVisible']} right={r['brHudRight']}/{r['innerW']} scrollW={r['scrollW']} -> {'OK' if okbr else 'FALHA'}")

    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    print(f'console errors (filtrado): {len(errs)}')
    fails = 0
    for name, status in results:
        if status != 'OK ':
            fails += 1
    print(f'RESUMO: {len(LANDS) - fails}/{len(LANDS)} viewports landscape OK, BR {"OK" if okbr else "FALHA"}')
    if fails or not okbr:
        raise AssertionError('responsividade com falhas — ver acima')
    print('PV3 RESPONSIVE PROBE PASS')
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
