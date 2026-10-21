"""Probe PV4 — valida o TOUCH HUD V2: mapa no topo, HP/chakra cada um de um
lado, base so joystick+skills, CD visivel nos botoes, banners discretos.
Run: python tools/probe_pv4_hud.py   (cwd = repo root)
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
PROFILE = tempfile.mkdtemp(prefix='nuba_pv4_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=390,844', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)


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
    await c.send("Emulation.setDeviceMetricsOverride", {"width": 844, "height": 390, "deviceScaleFactor": 2, "mobile": True})
    ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    for _ in range(30):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 6:
            break
        await asyncio.sleep(0.3)
    await asyncio.sleep(1.0)

    r = await ev(c, """(() => {
      const R = (sel) => { const el = document.querySelector(sel); if (!el) return null;
        const cs = getComputedStyle(el); if (cs.display === 'none') return { hidden: true };
        const b = el.getBoundingClientRect();
        return { l: Math.round(b.left), r: Math.round(b.right), t: Math.round(b.top), bt: Math.round(b.bottom), w: Math.round(b.width), h: Math.round(b.height) }; };
      return {
        innerW: window.innerWidth, innerH: window.innerHeight,
        minimap: R('.minimap-bezel'),
        hp: R('.hp-gauge'), ck: R('.chakra-gauge'),
        avatar: R('.player-avatar-ring'),
        ribbon: R('.abilities-ribbon'),
        brand: R('.hud-brand-pill'),
        team: R('.team-group.blue'),
        joy: R('#touch-joystick'), clu: R('#touch-cluster'),
        btnQ: R('#tbtn-q'), btnAtk: R('#tbtn-atk'),
        kda: R('.sub-status-line'),
        goal: R('.match-goal-txt')
      };
    })()""")
    W, H = r['innerW'], r['innerH']
    m, hp, ck = r['minimap'], r['hp'], r['ck']
    checks = {
        'mapa-no-topo': m and not m.get('hidden') and m['t'] < 100,
        'hp-lado-esquerdo': hp and not hp.get('hidden') and hp['l'] < W / 2,
        'chakra-lado-direito': ck and not ck.get('hidden') and ck['r'] > W / 2,
        'hp-chakra-mesma-faixa': hp and ck and abs(hp['t'] - ck['t']) < 30,
        'sem-avatar-no-touch': r['avatar'] and r['avatar'].get('hidden'),
        'sem-ribbon-desktop': r['ribbon'] and r['ribbon'].get('hidden'),
        'sem-brand-pill': r['brand'] and r['brand'].get('hidden'),
        'sem-team-groups': r['team'] and r['team'].get('hidden'),
        'sem-kda': r['kda'] and r['kda'].get('hidden'),
        'sem-goal-txt': r['goal'] and r['goal'].get('hidden'),
        'joystick-base-esq': r['joy'] and r['joy']['l'] < W / 3,
        'cluster-base-dir': r['clu'] and r['clu']['r'] > 2 * W / 3,
        'botoes-visiveis': r['btnQ'] and r['btnAtk'] and not r['btnQ'].get('hidden')
    }
    bad = [k for k, v in checks.items() if not v]
    print('=== PV4 LAYOUT (844x390 landscape) ===')
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FALHA'} {k}")
    print(f"  minimap t={m['t'] if m else '?'} | hp l={hp['l'] if hp else '?'} r={hp['r'] if hp else '?'} | ck l={ck['l'] if ck else '?'} r={ck['r'] if ck else '?'}")
    if bad:
        raise AssertionError(f'PV4 layout falhou: {bad}')

    # ---- CD visivel: poe Q em cooldown e checa o espelho #cdt-q ----
    await ev(c, "(() => { const p = window.units.find(u => u.isPlayer); p.cds.q = 5.0; return 'ok'; })()")
    await asyncio.sleep(0.7)
    cd = await ev(c, "(() => { const d = document.getElementById('cdt-q'); const s = document.getElementById('cd-q'); return { tbtnDisplay: d ? getComputedStyle(d).display : 'MISSING', tbtnText: d ? d.textContent : '', slotDisplay: s ? getComputedStyle(s).display : 'MISSING', bg: d ? d.style.background.slice(0, 30) : '' }; })()")
    assert cd['tbtnDisplay'] == 'flex' and 's' in cd['tbtnText'] and 'conic' in cd['bg'], f'CD nao espelhado: {cd}'
    print(f"[OK] CD no botao touch: display={cd['tbtnDisplay']} texto='{cd['tbtnText']}' bg={cd['bg']}...")

    # screenshots
    for tag in ['hud', 'hud_cd']:
        shot = await c.send("Page.captureScreenshot", {"format": "png"})
        img = base64.b64decode(shot.get("data") or shot.get("result", {}).get("data"))
        out = os.environ.get("TEMP", "/tmp") + f"/nuba_pv4_{tag}.png"
        open(out, "wb").write(img)
        print(f'screenshot: {out} ({len(img)} bytes)')

    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    assert len(errs) == 0, f'console errors: {errs[:3]}'
    print('PV4 HUD PROBE PASS — layout touch validado')
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
