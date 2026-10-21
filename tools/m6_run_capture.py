# -*- coding: utf-8 -*-
"""M6.1: captura das unidades CORRENDO (clip run autentico do APK) em plena batalha."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys, base64, os
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
OUT = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

CHECK = """(() => {
  const states = {};
  for (const u of window.units || []) states[u.id] = u.state;
  const running = Object.values(states).filter(s => s === 'run').length;
  const idle = Object.values(states).filter(s => s === 'idle').length;
  return { total: (window.units || []).length, running, idle, states };
})()"""

async def run(ws_url):
    mid = 0
    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            req = {"id": mid, "method": method}
            if params: req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=60))
                if data.get("id") == mid:
                    if "error" in data: raise RuntimeError(f"{method}: {data['error']}")
                    return data.get("result", {})
        async def ev(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return r.get("result", {}).get("value")
        async def shot(name):
            s = await call("Page.captureScreenshot", {"format": "png"})
            p = os.path.join(OUT, name)
            with open(p, "wb") as f: f.write(base64.b64decode(s["data"]))
            print("shot:", p)

        await call("Page.enable")
        await call("Emulation.setDeviceMetricsOverride",
                   {"width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
        await call("Page.navigate", {"url": BASE})
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("typeof window.start5v5Match === 'function'"): break
        await ev("window.start5v5Match()")
        for _ in range(60):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true"): break
        # deixa os bots correrem pro meio do mapa (~12s de batalha)
        peak = 0
        for i in range(8):
            await asyncio.sleep(1.5)
            v = await ev(CHECK)
            if v: peak = max(peak, v["running"])
            if i == 6:
                await shot("m6_10_units_running.png")
        v = await ev(CHECK)
        print("STATES FINAIS:", json.dumps(v, ensure_ascii=False))
        print("PEAK RUNNING:", peak, "/ 10")
        ok = v and v["total"] == 10 and peak >= 3
        print("M6.1 VALIDATION:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

def main():
    os.makedirs(OUT, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]
    tmp = tempfile.mkdtemp()
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}",
                             "--disable-gpu", "--window-size=1280,720", "--inprivate",
                             f"--user-data-dir={tmp}", BASE])
    time.sleep(3.0)
    code = 1
    try:
        info = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
        page = next(t for t in info if t.get("type") == "page")
        code = asyncio.run(run(page["webSocketDebuggerUrl"]))
    finally:
        try: proc.kill(); proc.wait(timeout=3)
        except Exception: pass
        shutil.rmtree(tmp, ignore_errors=True)
    return code

if __name__ == "__main__":
    sys.exit(main())
