# -*- coding: utf-8 -*-
"""Auditoria do lobby na viewport do usuario (1883x851): heroi 3D + fontes de scroll."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys, base64
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
W, H = 1883, 851

AUDIT = """(() => {
  const out = { viewport: [window.innerWidth, window.innerHeight] };
  out.doc = { sh: document.documentElement.scrollHeight, ch: document.documentElement.clientHeight,
              sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth };
  // hero 3D
  const m = window.lobbyHeroMesh;
  out.hero = m ? { visible: m.visible, bones: m.userData.bones ? m.userData.bones.length : 0,
                   pos: m.position ? [m.position.x, m.position.y, m.position.z] : null,
                   scale: m.scale ? m.scale.x : null,
                   worldPos: (() => { const v = new THREE.Vector3(); m.getWorldPosition(v); return [v.x, v.y, v.z]; })() }
               : null;
  out.stageMeshes = window.stage3DData && window.stage3DData.meshes ? window.stage3DData.meshes.length : 0;
  const cv = document.querySelector('canvas');
  out.canvas = cv ? { w: cv.width, h: cv.height, styleW: cv.style.width, styleH: cv.style.height } : null;
  out.camera = window.camera ? { pos: [window.camera.position.x, window.camera.position.y, window.camera.position.z],
                                  fov: window.camera.fov, aspect: window.camera.aspect } : null;
  const stg = document.querySelector('.hero-stage-center');
  if (stg) { const r = stg.getBoundingClientRect(); out.stageRect = [r.x, r.y, r.width, r.height]; }
  // scrollbars: todo elemento com overflow vertical real
  out.scrollEls = [...document.querySelectorAll('*')].filter(e => {
    if (e.clientHeight < 40 || e.scrollHeight <= e.clientHeight + 2) return false;
    const st = getComputedStyle(e);
    return st.overflowY === 'auto' || st.overflowY === 'scroll' || st.overflowY === 'visible';
  }).map(e => ({ tag: e.tagName, cls: (e.className.toString() || '').slice(0, 50), id: e.id,
                 sh: e.scrollHeight, ch: e.clientHeight })).slice(0, 20);
  out.lobbyScreen = (() => { const s = document.getElementById('lobby-screen');
    return s ? { active: s.classList.contains('active'), sh: s.scrollHeight, ch: s.clientHeight } : null; })();
  return out;
})()"""

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
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                if data.get("id") == mid:
                    if "error" in data: raise RuntimeError(f"{method}: {data['error']}")
                    return data.get("result", {})
        async def ev(expr):
            r = await call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return r.get("result", {}).get("value")
        await call("Page.enable")
        await call("Emulation.setDeviceMetricsOverride", {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
        await call("Page.navigate", {"url": BASE})
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("Boolean(window.rosterMeta && window.animationsData && window.lobbyHeroMesh)"): break
        await asyncio.sleep(2.0)
        v = await ev(AUDIT)
        print(json.dumps(v, indent=1))
        shot = await call("Page.captureScreenshot", {"format": "png"})
        io_ = open(r"C:/Users/jessi/Documents/antigravity/fearless-davinci/nuba_sketches/shots/lobby_audit_1883.png", "wb")
        io_.write(base64.b64decode(shot["data"])); io_.close()
        print("SHOT SALVO")

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=1920,1080", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
try:
    asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
