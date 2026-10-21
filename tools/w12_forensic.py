# -*- coding: utf-8 -*-
"""Probe forense: o que a pagina prod (via proxy) realmente executou no boot."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

PROBE = """(async () => {
  let out = {};
  try {
    out.ready = { ajustesReady: window.__ajustesReady === true, authSfx: typeof window.AUTH_SFX, start: typeof window.start5v5Match, renderer: typeof window.__renderer };
    out.dom = { ajSound: !!document.getElementById('aj-sound'), navTabs: document.querySelectorAll('.lobby-nav .nav-tab').length, pageAjustes: !!document.getElementById('page-ajustes') };
    // listeners presentes? clona e testa setLobbyPage direto
    const sec = document.getElementById('page-ajustes');
    out.direct = { fn: typeof window.setLobbyPage };
    // o game.js carregado: versao pela performance API
    const gjs = performance.getEntriesByType('resource').filter(r => r.name.includes('game.js')).map(r => r.name.split('/').pop() + ' status:' + (r.responseStatus || '?'));
    out.gameJs = gjs;
    out.errors = (window.__probeErrors || []).slice(-8);
    // testa click depois de esperar MAIS
    await new Promise(r => setTimeout(r, 8000));
    const tab = document.querySelector('.nav-tab[data-page="ajustes"]');
    tab.click();
    await new Promise(r => setTimeout(r, 400));
    out.lateClick = { active: sec.classList.contains('active'), ready: window.__ajustesReady === true };
    return out;
  } catch (e) { return { err: String(e && e.message ? e.message : e), out }; }
})()"""

CONSOLE_HOOK = """window.__probeErrors = [];
window.addEventListener('error', (e) => { window.__probeErrors.push('ERROR: ' + e.message + ' @ ' + (e.filename||'') + ':' + e.lineno); });
const _ce = console.error.bind(console);
console.error = function (...a) { window.__probeErrors.push('CONSOLE.ERROR: ' + a.join(' ').slice(0, 200)); _ce(...a); };"""

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
                return {"err": r["exceptionDetails"].get("text", "")}
            return r.get("result", {}).get("value")
        await call("Page.enable")
        await call("Runtime.enable")
        await call("Page.addScriptToEvaluateOnNewDocument", {"source": CONSOLE_HOOK})
        await call("Page.navigate", {"url": BASE})
        # espera longa: boot completo sob proxy
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true || typeof window.start5v5Match === 'function'"): break
        await asyncio.sleep(3.0)
        v = await ev(PROBE)
        print(json.dumps(v, indent=1, ensure_ascii=False))
        return 0

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=1280,720", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
try:
    asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
