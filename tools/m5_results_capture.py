# -*- coding: utf-8 -*-
"""M5 MATCH RESULTS - captura + validacao: win/lose/tie + revanche."""
import asyncio, json, socket, subprocess, tempfile, time, base64, os, sys, shutil
import urllib.request
import websockets

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
OUT = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

VALIDATE = """(() => {
  const ov = document.getElementById('match-results-overlay');
  if (!ov) return { error: 'sem overlay' };
  const q = id => document.getElementById(id);
  const tb = q('mr-tbody-blue'), tr = q('mr-tbody-red');
  return {
    shown: ov.classList.contains('show'),
    state: ov.className.replace('match-results-overlay', '').trim(),
    banner: (q('mr-banner-img') || {}).src || '',
    kanji: (q('mr-banner-kanji') || {}).textContent || '',
    text: (q('mr-banner-text') || {}).textContent || '',
    mvpName: (q('mr-mvp-name') || {}).textContent || '',
    mvpKda: (q('mr-mvp-kda') || {}).textContent || '',
    rowsBlue: tb ? tb.children.length : -1,
    rowsRed: tr ? tr.children.length : -1,
    subBlue: (q('mr-sub-blue') || {}).textContent || '',
    digitsBlue: ov.querySelectorAll('#mr-score-blue .skin-digit').length
  };
})()"""

async def run(ws_url):
    msg_id = 0
    results = {}
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
            p = os.path.join(OUT, f"m5_{name}.png")
            with open(p, "wb") as f: f.write(base64.b64decode(s["data"]))
            print("shot:", p)

        await call_cdp("Page.enable")
        await call_cdp("Emulation.setDeviceMetricsOverride",
                       {"width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
        await call_cdp("Page.navigate", {"url": BASE})
        for _ in range(90):
            await asyncio.sleep(2.0)
            if await ev("!!window.HERO_KITS"): break
        await ev("window.start5v5Match()")
        for _ in range(60):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true"): break
        await asyncio.sleep(4.0)

        # popula stats reais: player mata 2, um rival mata o player 1x
        await ev("""(() => {
            const p = window.units.find(u => u.isPlayer);
            for (const e of window.units.filter(u => u.team === 'red').slice(0, 2)) {
              e.hp = 5; e.x = p.x + 2; e.z = p.z;
              window.dealDamage(p, e, 9999, 'Rasengan!');
            }
            const r = window.units.find(u => u.team === 'red' && u.deadTimer <= 0);
            if (r) { window.dealDamage(r, window.units.find(u => u.isPlayer), 99999, 'Chidori (Mil Pássaros)'); }
            return true;
        })()""")
        await asyncio.sleep(2.5)

        # dispara o fim de partida REAL (guard + delay + show chain)
        await ev("window.endMatch('VITÓRIA DO TIME KONOHA AZUL!')")
        await asyncio.sleep(4.0)  # 1.5s de drama do abate + ~2.5s de animacoes
        v = await ev(VALIDATE)
        results['win'] = v
        print("WIN validate:", json.dumps(v, ensure_ascii=False))
        await shot("07_results_win")

        # derrota
        await ev("window.hideMatchResults()")
        await ev("window.showMatchResults('red')")
        await asyncio.sleep(3.0)
        v = await ev(VALIDATE); results['lose'] = v
        print("LOSE validate:", json.dumps(v, ensure_ascii=False))
        await shot("08_results_lose")

        # empate
        await ev("window.hideMatchResults()")
        await ev("window.showMatchResults('tie')")
        await asyncio.sleep(3.0)
        v = await ev(VALIDATE); results['tie'] = v
        print("TIE validate:", json.dumps(v, ensure_ascii=False))
        await shot("09_results_tie")

        # revanche funciona?
        await ev("window.hideMatchResults()")
        await ev("window.start5v5Match()")
        ok_rematch = False
        for _ in range(40):
            await asyncio.sleep(1.5)
            if await ev("window.matchActive === true && document.getElementById('match-results-overlay').classList.contains('hidden')"):
                ok_rematch = True; break
        results['rematch'] = {"matchActiveAgain": ok_rematch}
        print("REMATCH:", ok_rematch)

    ok = (results['win'].get('shown') and results['win'].get('rowsBlue') == 5
          and '勝利' in results['win'].get('kanji', '')
          and results['lose'].get('shown') and '敗北' in results['lose'].get('kanji', '')
          and results['tie'].get('shown') and '引' in results['tie'].get('kanji', '')
          and results['rematch']['matchActiveAgain'])
    print("M5 VALIDATION:", "PASS" if ok else "FAIL")
    return 0 if ok else 1

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
        code = asyncio.run(run(get_ws_url(free_port)))
    finally:
        try: proc.kill(); proc.wait(timeout=3)
        except Exception: pass
        shutil.rmtree(tmp_profile, ignore_errors=True)
    print("CAPTURE DONE")
    return code

if __name__ == "__main__":
    sys.exit(main())
