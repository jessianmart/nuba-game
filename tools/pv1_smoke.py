# -*- coding: utf-8 -*-
"""Smoke PV1 Tier 5 (docs/PIVOT_MOBILE.md PV1.6): emulacao touch CDP 412x915.
Valida a IIFE touch dos agentes: joystick (.active, INPUT.moveX/Z, dead-zone),
cluster .tbtn (atk hold->INPUT.fire, q tap->executeSkill c/ auto-aim, chakra hold),
camera thirdperson auto (PV1.5a), gate de atk fantasma (PV1.4c)."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

async def main(port):
    info = json.load(urllib.request.urlopen(f'http://127.0.0.1:{port}/json'))
    page = next(t for t in info if t.get('type') == 'page')
    async with websockets.connect(page['webSocketDebuggerUrl'], max_size=20_000_000) as ws:
        mid = 0
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            req = {"id": mid, "method": method}
            if params: req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
                if data.get("id") == mid:
                    if "error" in data: raise RuntimeError(str(data["error"]))
                    return data.get("result", {})
        async def ev(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            if r.get("exceptionDetails"):
                return {"__err": r["exceptionDetails"].get("text", "")}
            return r.get("result", {}).get("value")
        # emulacao mobile: touch + viewport 412x915 (Tier 5)
        await call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        await call("Emulation.setDeviceMetricsOverride", {"width": 915, "height": 412, "deviceScaleFactor": 2.0, "mobile": True})
        await call("Page.enable")
        await call("Page.navigate", {"url": BASE})
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        out = {}
        # (1) device detection (controles ficam visiveis so apos a partida)
        out['device'] = await ev("""(() => ({
          isTouch: window.__DEVICE.isTouch,
          bodyTouch: document.body.classList.contains('touch'),
          keyBadgeHidden: getComputedStyle(document.querySelector('.ability-key')).display === 'none'
        }))()""")
        # (2) partida 3v3 pelo botao JOGAR (default dm_3v3)
        await ev("document.getElementById('btn-start-match').click()")
        # robustez de timing prod (proxy): esperar roster COMPLETO + player spawnado
        for _ in range(40):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true && window.units && window.units.length >= 6 && !!window.units.find(u => u.isPlayer)"): break
        out['match'] = await ev("""(() => ({
          active: window.matchActive === true,
          teamCount: window.units ? window.units.length : -1,
          camMode: window.__cameraMode ? window.__cameraMode() : 'n/a',
          controlsVisible: document.getElementById('touch-controls').getClientRects().length > 0,
          aimFn: typeof window.findAimTarget
        }))()""")
        # coords dos alvos (viewport 412x915; joystick deles = 44vw x 52vh bottom-left)
        coords = await ev("""(() => {
          const r = (id) => { const b = document.getElementById(id).getBoundingClientRect(); return {x: b.left + b.width/2, y: b.top + b.height/2}; };
          return { q: r('tbtn-q'), atk: r('tbtn-atk'), c: r('tbtn-c'), joy: {x: 201, y: 305} };
        })()""")
        async def touch(kind, x, y):
            pts = [{"x": x, "y": y, "id": 1}] if kind != "touchEnd" else []
            await call("Input.dispatchTouchEvent", {"type": kind, "touchPoints": pts})
        # (3) joystick: drag 40px p/ cima -> INPUT.moveZ>0 e player anda
        out['posBefore'] = await ev("(() => { const p = window.units.find(u => u.isPlayer); return {x: p.x, z: p.z}; })()")
        await touch("touchStart", coords['joy']['x'], coords['joy']['y'])
        await touch("touchMove", coords['joy']['x'], coords['joy']['y'] - 40)
        await asyncio.sleep(0.3)
        out['joyDrag'] = await ev("({moveZ: +window.INPUT.moveZ.toFixed(2), moveX: +window.INPUT.moveX.toFixed(2), active: document.getElementById('touch-joystick').classList.contains('active')})")
        await asyncio.sleep(1.2)
        out['posAfter'] = await ev("(() => { const p = window.units.find(u => u.isPlayer); return {x: p.x, z: p.z}; })()")
        await touch("touchEnd", 0, 0)
        await asyncio.sleep(0.3)
        out['joyRelease'] = await ev("({moveZ: window.INPUT.moveZ, moveX: window.INPUT.moveX, active: document.getElementById('touch-joystick').classList.contains('active')})")
        # (4) tap Q -> auto-aim + executeSkill (cds.q>0 ou chakra gasto)
        await ev("window.__ckBefore = window.units.find(u => u.isPlayer).chakra;")
        await touch("touchStart", coords['q']['x'], coords['q']['y'])
        await touch("touchEnd", 0, 0)
        await asyncio.sleep(0.5)
        out['qTap'] = await ev("(() => { const p = window.units.find(u => u.isPlayer); return {cdsq: p.cds.q, ckDelta: window.__ckBefore - p.chakra}; })()")
        # (5) hold ATK -> INPUT.fire / release -> false
        await touch("touchStart", coords['atk']['x'], coords['atk']['y'])
        await asyncio.sleep(0.3)
        out['atkHold'] = await ev("window.INPUT.fire === true")
        await touch("touchEnd", 0, 0)
        await asyncio.sleep(0.2)
        out['atkRelease'] = await ev("window.INPUT.fire === false")
        # (6) chakra hold -> INPUT.chakra
        await touch("touchStart", coords['c']['x'], coords['c']['y'])
        await asyncio.sleep(0.2)
        out['chakraHold'] = await ev("window.INPUT.chakra === true")
        await touch("touchEnd", 0, 0)
        # (7) tap no canvas (fora de joystick/cluster) nao gera atk fantasma
        await touch("touchStart", 457, 150)
        await asyncio.sleep(0.2)
        out['noGhost'] = await ev("window.INPUT.fire === false")
        await touch("touchEnd", 0, 0)
        print(json.dumps(out, indent=1, ensure_ascii=False))
        d, m, jd, jr = out.get('device') or {}, out.get('match') or {}, out.get('joyDrag') or {}, out.get('joyRelease') or {}
        qt, ah, ar, ch, ng = out.get('qTap') or {}, out.get('atkHold'), out.get('atkRelease'), out.get('chakraHold'), out.get('noGhost')
        pb, pa = out.get('posBefore') or {}, out.get('posAfter') or {}
        moved = abs(pa.get('x', 0) - pb.get('x', 0)) + abs(pa.get('z', 0) - pb.get('z', 0)) > 0.5
        ok = bool(d.get('isTouch') and d.get('bodyTouch') and d.get('keyBadgeHidden')
              and m.get('active') and m.get('teamCount') == 6 and m.get('camMode') == 'thirdperson'
              and m.get('controlsVisible') and m.get('aimFn') == 'function'
              and moved
              and jd.get('moveZ', 0) > 0.4 and jd.get('active')
              and jr.get('moveZ') == 0 and not jr.get('active')
              and (qt.get('cdsq', 0) > 0 or qt.get('ckDelta', 0) > 0)
              and ah is True and ar is True and ch is True and ng is True)
        print('moved:', moved, '| SMOKE RESULT:', 'PASS' if ok else 'FAIL')
        return 0 if ok else 1

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=412,915", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
code = 1
try:
    code = asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(code)
