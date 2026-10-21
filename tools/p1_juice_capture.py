# -*- coding: utf-8 -*-
"""P1 Juice capture — photographic proof of hitstop/slow-mo/KO VFX in NUBA.

Boots headless Edge, starts a 5v5 match, forces a player kill (full juice
drama: hitstop + slow-mo + shake + FOV punch + flash) and an ultimate cast,
capturing PNG frames at the money moments. Also dumps window.JUICE state as
hard evidence the feel system is live.
"""
import asyncio, base64, json, os, socket, subprocess, sys, tempfile, time, urllib.request
import websockets

sys.stdout.reconfigure(encoding='utf-8')

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if not os.path.exists(EDGE_PATH):
    EDGE_PATH = r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"

SCRATCH = r"C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\p1_juice"
os.makedirs(SCRATCH, exist_ok=True)

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        return s.getsockname()[1]

async def call_cdp(ws, method, params=None, _id=[0]):
    _id[0] += 1
    mid = _id[0]
    await ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
    while True:
        raw = await asyncio.wait_for(ws.recv(), timeout=60.0)
        msg = json.loads(raw)
        if msg.get("id") == mid:
            if "error" in msg:
                raise RuntimeError(f"CDP error {method}: {msg['error']}")
            return msg.get("result", {})

async def evaluate(ws, expression):
    res = await call_cdp(ws, "Runtime.evaluate", {
        "expression": expression, "returnByValue": True
    })
    return res.get("result", {}).get("value")

async def save_shot(ws, name):
    shot = await call_cdp(ws, "Page.captureScreenshot", {"format": "png"})
    path = os.path.join(SCRATCH, name)
    with open(path, "wb") as f:
        f.write(base64.b64decode(shot["data"]))
    print(f"  [SHOT] {path}")
    return path

async def main(port):
    tabs = json.loads(urllib.request.urlopen(
        f"http://127.0.0.1:{port}/json", timeout=10).read())
    tab = next(t for t in tabs if "localhost:8080" in t.get("url", ""))
    ws = await websockets.connect(tab["webSocketDebuggerUrl"], max_size=256 * 1024 * 1024)
    print("Connected to page:", tab["url"])

    # Wait for lobby assets (roster meta ready)
    print("Waiting for lobby assets...")
    for _ in range(180):
        if await evaluate(ws, "Boolean(window.rosterMeta && window.rosterMeta.length && window.lobbyHeroMesh)"):
            break
        await asyncio.sleep(1.0)
    print("Lobby ready.")

    # Start the 5v5 match
    print("Starting 5v5 match...")
    await evaluate(ws, "window.start5v5Match()")
    for _ in range(120):
        if await evaluate(ws, "Boolean(window.matchActive && window.units && window.units.length === 10)"):
            break
        await asyncio.sleep(0.25)
    await asyncio.sleep(1.5)
    print("Match live: 10 units on arena.")

    # ---- MOMENT 1: forced player kill -> full juice drama ----
    print("\n[M1] Forcing player kill (hitstop + slow-mo + shake + flash)...")
    m1 = await evaluate(ws, """(() => {
      const p = window.units.find(u => u.isPlayer);
      const e = window.units.find(u => u.team !== p.team);
      window.dealDamage(p, e, 99999, 'P1 Juice KO Demo');
      return JSON.stringify({
        killed: e.deadTimer > 0,
        state: e.state,
        juice: window.JUICE
      });
    })()""")
    print("  Kill state:", m1)
    # capture inside the drama window (hitstop first, then slow-mo)
    await save_shot(ws, "p1_juice_ko_impact.png")
    await asyncio.sleep(0.35)
    m1b = await evaluate(ws, "JSON.stringify(window.JUICE)")
    print("  JUICE mid-slow-mo:", m1b)
    await save_shot(ws, "p1_juice_ko_slowmo.png")

    # ---- MOMENT 2: ultimate cast -> wind-up freeze + ougi banner + fov punch ----
    print("\n[M2] Firing ultimate (wind-up freeze + ougi banner + zoom punch)...")
    m2 = await evaluate(ws, """(() => {
      const p = window.units.find(u => u.isPlayer);
      p.chakra = 100;
      p.cds.r = 0;
      window.executeSkill(p, 'r');
      return JSON.stringify({ cast: true, juice: window.JUICE });
    })()""")
    print("  Ult cast:", m2)
    await asyncio.sleep(0.18)
    await save_shot(ws, "p1_juice_ult_cast.png")
    m2b = await evaluate(ws, "JSON.stringify(window.JUICE)")
    print("  JUICE post-ult:", m2b)

    await ws.close()
    print("\nALL P1 JUICE CAPTURES DONE ->", SCRATCH)

def run():
    port = get_free_port()
    tmp_profile = tempfile.mkdtemp()
    print(f"Headless Edge on debug port {port}...")
    proc = subprocess.Popen([
        EDGE_PATH, "--headless=new",
        f"--remote-debugging-port={port}",
        "--disable-gpu", "--window-size=1280,720", "--inprivate",
        f"--user-data-dir={tmp_profile}",
        "http://localhost:8080/index.html"
    ])
    time.sleep(3.0)
    try:
        asyncio.run(main(port))
    finally:
        proc.kill()
        try:
            proc.wait(timeout=3)
        except Exception:
            pass
        import shutil
        shutil.rmtree(tmp_profile, ignore_errors=True)

if __name__ == "__main__":
    run()
