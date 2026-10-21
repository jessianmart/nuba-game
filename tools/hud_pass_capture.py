# -*- coding: utf-8 -*-
"""M4.2 HUD PASS - captura de prova: lobby, HUD, kill-feed kanji, scoreboard, death overlay."""
import asyncio, json, socket, subprocess, tempfile, time, base64, os, sys, shutil
import urllib.request
import websockets

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
OUT = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

async def run(ws_url):
    msg_id = 0
    shots = {}
    async with websockets.connect(ws_url, max_size=20_000_000) as ws:
        async def call_cdp(method, params=None):
            nonlocal msg_id
            msg_id += 1
            cid = msg_id
            req = {"id": cid, "method": method}
            if params: req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=60.0))
                if data.get("id") == cid:
                    if "error" in data: raise RuntimeError(f"{method}: {data['error']}")
                    return data.get("result", {})
        async def ev(expr):
            r = await call_cdp("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
            return r.get("result", {}).get("value")
        async def shot(name):
            s = await call_cdp("Page.captureScreenshot", {"format": "png"})
            p = os.path.join(OUT, f"hudpass_{name}.png")
            with open(p, "wb") as f: f.write(base64.b64decode(s["data"]))
            shots[name] = p
            print("shot:", p)

        await call_cdp("Page.enable")
        await call_cdp("Emulation.setDeviceMetricsOverride",
                       {"width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
        await call_cdp("Page.navigate", {"url": BASE})
        # espera o lobby carregar (assets pesados)
        for _ in range(90):
            await asyncio.sleep(2.0)
            if await ev("!!window.HERO_KITS") : break
        await asyncio.sleep(2.0)
        await shot("01_lobby")

        # inicia partida
        await ev("window.start5v5Match()")
        for _ in range(60):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true"): break
        await asyncio.sleep(3.5)
        await shot("02_hud_clean")

        # kill-feed com kanji
        await ev("""(() => {
            const p = window.units.find(u => u.isPlayer);
            const e = window.units.find(u => !u.isPlayer && u.team === 'red');
            e.hp = 5; e.x = p.x + 2; e.z = p.z;
            window.dealDamage(p, e, 9999, 'Rasengan!');
            return true;
        })()""")
        await asyncio.sleep(1.2)
        await shot("03_killfeed_kanji")

        # awakening chip + ougi banner
        await ev("window.units.find(u => u.isPlayer).awakenedTimer = 5")
        await asyncio.sleep(0.4)
        await shot("04_awake_chip")

        # scoreboard tab
        await ev("window.toggleScoreboard(true)")
        await asyncio.sleep(1.0)
        await shot("05_scoreboard")
        await ev("window.toggleScoreboard(false)")

        # death overlay
        await ev("""(() => {
            const p = window.units.find(u => u.isPlayer);
            const e = window.units.find(u => !u.isPlayer && u.team === 'red');
            window.dealDamage(e, p, 99999, 'Chidori (Mil Pássaros)');
            return true;
        })()""")
        await asyncio.sleep(1.2)
        await shot("06_death_overlay")
    return shots

def get_ws_url(port):
    data = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
    page = next(t for t in data if t.get("type") == "page")
    return page["webSocketDebuggerUrl"]

def main():
    os.makedirs(OUT, exist_ok=True)
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); free_port = s.getsockname()[1]
    tmp_profile = tempfile.mkdtemp()
    proc = subprocess.Popen([
        EDGE_PATH, "--headless=new", f"--remote-debugging-port={free_port}",
        "--disable-gpu", "--window-size=1280,720", "--inprivate",
        f"--user-data-dir={tmp_profile}", BASE])
    time.sleep(3.0)
    try:
        asyncio.run(run(get_ws_url(free_port)))
    finally:
        try: proc.kill(); proc.wait(timeout=3)
        except Exception: pass
        shutil.rmtree(tmp_profile, ignore_errors=True)
    print("CAPTURE DONE")

if __name__ == "__main__":
    sys.exit(main())
