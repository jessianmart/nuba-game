# -*- coding: utf-8 -*-
"""Smoke BOOT-GUARD: cold-start ×3 — start5v5Match chamado no primeiro tick de readiness
(antes do fetch do roster completar) deve esperar e devolver 10 units, zero excecao."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

RACE = """(async () => {
  try {
    await window.start5v5Match(); // chamado O MAIS CEDO possivel — e o ponto da race
    const n = window.units.length;
    const shields = window.units.every(u => u.spawnShield > 0);
    return { units: n, shieldsOn: shields, matchActive: window.matchActive };
  } catch (e) { return { err: String(e && e.message ? e.message : e) }; }
})()"""

async def run_once():
    port = free_port()
    tmp = tempfile.mkdtemp()
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                             "--window-size=1280,720", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
    time.sleep(2.5)
    try:
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
                    data = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                    if data.get("id") == mid:
                        if "error" in data: raise RuntimeError(str(data["error"]))
                        return data.get("result", {})
            async def ev(expr, await_promise=True):
                r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": await_promise})
                if r.get("exceptionDetails"):
                    return {"err": r["exceptionDetails"].get("text", "")}
                return r.get("result", {}).get("value")
            await call("Page.enable")
            await call("Page.navigate", {"url": BASE})
            # readiness APERTADO: checa a cada 50ms e dispara na PRIMEIRA presenca da funcao
            for _ in range(600):
                v = await ev("typeof window.start5v5Match === 'function'", await_promise=False)
                if v: break
                await asyncio.sleep(0.05)
            v = await ev(RACE)
            return v
    finally:
        try: proc.kill(); proc.wait(timeout=3)
        except Exception: pass
        shutil.rmtree(tmp, ignore_errors=True)

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

results = []
for i in range(3):
    r = asyncio.run(run_once())
    results.append(r)
    print(f"cold-start {i+1}: {json.dumps(r, ensure_ascii=False)}")
ok = all(r and r.get('units') == 10 and r.get('shieldsOn') and not r.get('err') for r in results)
print('SMOKE RESULT:', 'PASS' if ok else 'FAIL')
sys.exit(0 if ok else 1)
