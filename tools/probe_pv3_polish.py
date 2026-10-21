"""Probe PV3 — governor mobile, VFX cap, haptics e PWA.
Usa Emulation.setUserAgentOverride (iPhone) para que __DEVICE.isMobile seja
true no BOOT — o governor e lido no load, nao da pra so add('touch').
Run: python tools/probe_pv3_polish.py   (cwd = repo root)
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
PROFILE = tempfile.mkdtemp(prefix='nuba_pv3_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=844,390', '--inprivate', f'--user-data-dir={PROFILE}', 'about:blank'
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

    # UA mobile ANTES do load (governor roda no boot)
    await c.send("Emulation.setUserAgentOverride", {"userAgent": IPHONE_UA, "platform": "iPhone"})
    await c.send("Emulation.setDeviceMetricsOverride",
                 {"width": 844, "height": 390, "deviceScaleFactor": 2, "mobile": True})
    await c.send("Page.navigate", {"url": "http://localhost:8080/index.html"})
    for _ in range(40):
        if await ev(c, 'typeof window.startMatch') == 'function':
            break
        await asyncio.sleep(0.5)

    # ---------- governor ----------
    gov = await ev(c, """(() => {
      const g = window.__GOV || null;
      return g ? { mobile: g.mobile, pref: g.pref, dprCap: g.dprCap, vfxCap: g.vfxCap,
        isMobileDevice: !!(window.__DEVICE && window.__DEVICE.isMobile),
        uaMobile: /iPhone/.test(navigator.userAgent),
        pixelRatio: window.__renderer ? window.__renderer.getPixelRatio() : null } : null;
    })()""")
    assert gov, 'window.__GOV ausente'
    checks = {
        'gov-mobile-detectado': gov['mobile'] and gov['isMobileDevice'] and gov['uaMobile'],
        'gov-dpr-cap-1.25': gov['dprCap'] == 1.25,
        'gov-pixel-ratio-aplicado': gov['pixelRatio'] is not None and gov['pixelRatio'] <= 1.25,
        'gov-vfx-cap-24': gov['vfxCap'] == 24,
    }
    print('=== PV3.1 GOVERNO MOBILE ===')
    for k, v in checks.items():
        print(f"  {'OK ' if v else 'FALHA'} {k}")
    print(f"  gov={gov}")
    bad = [k for k, v in checks.items() if not v]
    assert not bad, f'governor: {bad}'

    # ---------- partida + VFX cap ----------
    await ev(c, "document.body.classList.add('touch')")
    ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    assert ok == 'ok', f'startMatch: {ok}'
    for _ in range(30):
        if await ev(c, 'window.units ? window.units.length : -1') == 6:
            break
        await asyncio.sleep(0.3)
    await asyncio.sleep(0.6)

    # Pico NATURAL (cap desligado) para provar que o caminho foi exercitado; o
    # SPAWN GUARD da base bloqueia hits perto dela -> zera o shield de cada alvo.
    # Atacante bot (longe do player) evita hitstop acumulado no meio da injecao.
    inj = await ev(c, """(() => {
      const us = window.units.filter(u => !u.isPlayer);
      const a = us[0];
      const others = us.filter(u => u !== a);
      if (!a || !others.length) return 'sem units';
      window.__GOV.vfxCap = 999; // mede o pico natural
      for (let i = 0; i < 40; i++) {
        const t = others[i % others.length];
        t.spawnShield = 0;              // SPAWN GUARD: imortal perto da base
        window.dealDamage(a, t, 1, 'probe');
      }
      return 'ok';
    })()""")
    assert inj == 'ok', f'injecao VFX: {inj}'
    await asyncio.sleep(0.3)
    peak = await ev(c, "window.__PERF.snapshot().vfx")
    print('=== PV3.1 VFX CAP ===')
    print(f"  pico natural (cap off)={peak}")
    assert peak > 24, f'pico {peak} nao excedeu 24 — injecao nao exercitou o caminho'

    await ev(c, "window.__GOV.vfxCap = 24")   # cap real mobile
    await asyncio.sleep(2.0)                   # cap remove ~1/frame — converge em <1s
    settled = await ev(c, "window.__PERF.snapshot().vfx")
    print(f"  apos cap 24 (2s)={settled}")
    assert settled <= 24, f'VFX cap falhou: {settled} > 24'

    # ---------- haptics ----------
    hb = await ev(c, """(() => {
      window.__vb = [];
      try { Object.defineProperty(navigator, 'vibrate', { value: (p) => { window.__vb.push(p); return true; }, configurable: true, writable: true }); }
      catch (e) { navigator.vibrate = (p) => { window.__vb.push(p); return true; }; }
      const p = window.units.find(u => u.isPlayer);
      const b = window.units.find(u => !u.isPlayer);
      if (!p || !b) return { err: 'sem units' };
      p.spawnShield = 0; b.spawnShield = 0;
      window.dealDamage(b, p, 30, 'probe-dano-recebido');   // levou dano -> 18
      return { after: window.__vb.slice() };
    })()""")
    assert hb.get('after') == [18], f'haptic de dano recebido: {hb}'
    # throttle de 60ms: espera e testa o "acertou" (12)
    await asyncio.sleep(0.12)
    hb2 = await ev(c, """(() => {
      window.__vb = [];
      const p = window.units.find(u => u.isPlayer);
      const b = window.units.filter(u => !u.isPlayer && u.deadTimer <= 0)[0];
      p.spawnShield = 0; if (b) b.spawnShield = 0;
      window.dealDamage(p, b, 30, 'probe-acertou');
      return { after: window.__vb.slice() };
    })()""")
    assert hb2.get('after') == [12], f'haptic de acerto: {hb2}'
    print('=== PV3.3 HAPTICS ===')
    print(f"  dano recebido -> {hb['after']} | acertou -> {hb2['after']}")

    # ---------- PWA ----------
    mf = await c.send("Page.getAppManifest", {})
    data = mf.get('result', mf) or {}
    errors = data.get('errors') or []
    raw = data.get('data') or ''
    parsed = json.loads(raw) if raw else {}
    head = await ev(c, """(() => ({
      link: !!document.querySelector('link[rel="manifest"]'),
      theme: (document.querySelector('meta[name="theme-color"]') || {}).content || null,
      apple: !!document.querySelector('meta[name="apple-mobile-web-app-capable"]')
    }))()""")
    ico = await ev(c, """(async () => {
      const out = {};
      for (const p of ['assets/logo/icon-192.png', 'assets/logo/icon-512.png', 'manifest.webmanifest']) {
        try { const r = await fetch(p, { cache: 'no-store' }); out[p] = r.status; } catch (e) { out[p] = 'ERR'; }
      }
      return out;
    })()""", await_promise=True)
    pchecks = {
        'manifest-parseado-sem-erros': bool(parsed) and not errors,
        'manifest-orientation-landscape': parsed.get('orientation') == 'landscape',
        'manifest-theme-laranja': parsed.get('theme_color') == '#f97316',
        'manifest-display-fullscreen': parsed.get('display') == 'fullscreen',
        'manifest-icones-192-512': sorted((i.get('sizes') for i in parsed.get('icons', []))) == ['192x192', '512x512'],
        'head-link-manifest': head['link'],
        'head-theme-color': head['theme'] == '#f97316',
        'head-apple-capable': head['apple'],
        'icones-e-manifest-200': ico.get('assets/logo/icon-192.png') == 200 and ico.get('assets/logo/icon-512.png') == 200 and ico.get('manifest.webmanifest') == 200,
    }
    print('=== PV3.3 PWA ===')
    for k, v in pchecks.items():
        print(f"  {'OK ' if v else 'FALHA'} {k}")
    print(f"  fetch={ico} erros_manifest={errors}")
    pbad = [k for k, v in pchecks.items() if not v]
    assert not pbad, f'PWA: {pbad}'

    errs = [e for e in c.console_errors if '.webp' not in str(e) and 'THREE.WebGLState' not in str(e)]
    assert len(errs) == 0, f'console errors: {errs[:3]}'
    print(f'console errors (filtrado): 0')
    print('PV3 POLISH PROBE PASS')
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
