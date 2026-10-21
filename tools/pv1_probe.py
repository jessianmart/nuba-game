# -*- coding: utf-8 -*-
"""Probe forense PV1: quais eventos chegam ao #touch-joystick com CDP dispatchTouchEvent?"""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

HOOK = """window.__evlog = [];
['touchstart','touchmove','touchend','pointerdown','pointermove','pointerup','mousedown','mouseup','click'].forEach(t => {
  document.addEventListener(t, (e) => {
    window.__evlog.push(t + '|tgt=' + (e.target && e.target.id ? e.target.id : (e.target && e.target.className || '').toString().slice(0,30)) + '|type=' + (e.pointerType || '-'));
  }, { passive: false, capture: true });
});"""

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
            return r.get("result", {}).get("value")
        await call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        await call("Emulation.setDeviceMetricsOverride", {"width": 412, "height": 915, "deviceScaleFactor": 2.0, "mobile": True})
        await call("Page.enable")
        await call("Page.addScriptToEvaluateOnNewDocument", {"source": HOOK})
        await call("Page.navigate", {"url": BASE})
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        await ev("document.getElementById('btn-start-match').click()")
        for _ in range(30):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true"): break
        # dispara 1 touch no joystick
        await call("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": 91, "y": 677, "id": 1}]})
        await call("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [{"x": 91, "y": 637, "id": 1}]})
        await asyncio.sleep(0.5)
        await call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
        await asyncio.sleep(0.5)
        log = await ev("window.__evlog")
        print("EVENT LOG:", json.dumps(log, indent=1))
        # segunda tentativa: mouse event no mesmo ponto (comparativo)
        await ev("window.__evlog = []")
        await call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 91, "y": 677, "button": "left", "clickCount": 1})
        await call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": 91, "y": 677, "button": "left", "clickCount": 1})
        await asyncio.sleep(0.5)
        log2 = await ev("window.__evlog")
        print("MOUSE LOG:", json.dumps(log2, indent=1))
        joy = await ev("({moveX: window.INPUT.moveX, moveZ: window.INPUT.moveZ, active: document.getElementById('touch-joystick').classList.contains('active')})")
        print("STATE:", json.dumps(joy))
        return 0

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=412,915", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
try:
    asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
