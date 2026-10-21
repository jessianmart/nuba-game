# -*- coding: utf-8 -*-
"""Smoke W2 Integracao Serial: 12 herois no lobby + Tsunade (1tnd) e Orochimaru (1orc)
jogaveis end-to-end. Padrao §6.5: CDP, touch emulado 915x412 landscape (config provada
no PV1), 2 partidas sequenciais — valida roster, selecao, spawn do modelo, kit, cast Q."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

async def run_match(ws, mid, ev, call, hero_id, expect):
    """Seleciona heroi, inicia partida 3v3 e valida kit + cast Q."""
    # lobby: card existe?
    card = await ev(f"!!document.querySelector('.roster-card[data-id=\"{hero_id}\"], .hero-card[data-id=\"{hero_id}\"], .collection-card[data-id=\"{hero_id}\"]')")
    if not card:
        return {"card": False}
    await ev(f"document.querySelector('[data-id=\"{hero_id}\"]').click()")
    sel = await ev("window.selectedHeroId")
    if sel != hero_id:
        # fallback: selectLobbyHero pode requerer o card certo (algumas telas)
        await ev(f"document.querySelectorAll('[data-id]').forEach(e => e.dataset.id === '{hero_id}' && e.click())")
        sel = await ev("window.selectedHeroId")
    await ev("document.getElementById('btn-start-match').click()")
    # espera roster completo + player (licao de timing prod)
    for _ in range(40):
        await asyncio.sleep(1.5)
        if await ev("window.matchActive === true && window.units && window.units.length >= 6 && !!window.units.find(u => u.isPlayer)"):
            break
    info = await ev(f"""(() => {{
      const u = window.units.find(x => x.isPlayer);
      if (!u) return null;
      return {{
        heroId: u.heroId,
        kitQ: u.kit && u.kit.q ? u.kit.q.name : null,
        cd: u.kit && u.kit.q ? u.kit.q.cd : null,
        dmg: u.kit && u.kit.q ? u.kit.q.dmg : null,
        rigChildren: u.mesh ? u.mesh.children.length : -1,
        rigHero: u.mesh && u.mesh.userData ? u.mesh.userData.heroId : null,
        cds_q: u.cds ? u.cds.q : null,
        chakra: u.chakra,
        teamCount: window.units.length
      }};
    }})()""")
    if not info or info.get("heroId") != hero_id:
        return {"card": True, "selected": sel, "info": info}
    # cast Q via tap no botao touch (padrao PV1)
    coords = await ev("""(() => {
      const b = document.getElementById('tbtn-q').getBoundingClientRect();
      return {x: b.left + b.width/2, y: b.top + b.height/2};
    })()""")
    ck_before = info["chakra"]
    await call("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [{"x": coords["x"], "y": coords["y"], "id": 1}]})
    await call("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    await asyncio.sleep(0.6)
    after = await ev("(() => { const u = window.units.find(x => x.isPlayer); return {cds_q: u.cds.q, chakra: u.chakra}; })()")
    return {"card": True, "selected": sel, "info": info, "cast": after,
            "castOk": after["cds_q"] > 0 and (ck_before - after["chakra"]) > 0,
            "expect": expect}

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
        await call("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})
        await call("Emulation.setDeviceMetricsOverride", {"width": 915, "height": 412, "deviceScaleFactor": 2.0, "mobile": True})
        await call("Page.enable")
        out = {}
        # ---- Match A: Tsunade ----
        await call("Page.navigate", {"url": BASE})
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        out["roster"] = await ev("(() => { const ids = [...document.querySelectorAll('[data-id]')].map(e => e.dataset.id).filter(id => id.length === 4); return {n: new Set(ids).size, hasTnd: ids.includes('1tnd'), hasOrc: ids.includes('1orc')}; })()")
        out["tsunade"] = await run_match(ws, mid, ev, call, "1tnd", {"kitQ": "Rakanken (Punho Sismico)", "cd": 5.5, "dmg": 240})
        # ---- Match B: Orochimaru (reload limpo) ----
        await call("Page.navigate", {"url": BASE})
        for _ in range(40):
            await asyncio.sleep(2.0)
            if await ev("window.__ajustesReady === true"): break
        out["orochimaru"] = await run_match(ws, mid, ev, call, "1orc", {"kitQ": "Sen'nejashu (Cobras Ocultas)", "cd": 5.0, "dmg": 200})
        print(json.dumps(out, indent=1, ensure_ascii=False))
        r, t, o = out.get("roster") or {}, out.get("tsunade") or {}, out.get("orochimaru") or {}
        ti, oi = t.get("info") or {}, o.get("info") or {}
        ok = bool(r.get("n") == 12 and r.get("hasTnd") and r.get("hasOrc")
              and t.get("card") and t.get("selected") == "1tnd"
              and ti.get("heroId") == "1tnd" and ti.get("kitQ") == t.get("expect", {}).get("kitQ")
              and ti.get("cd") == 5.5 and ti.get("dmg") == 240
              and (ti.get("rigChildren") or -1) > 0 and ti.get("teamCount") == 6
              and t.get("castOk")
              and o.get("card") and o.get("selected") == "1orc"
              and oi.get("heroId") == "1orc" and oi.get("kitQ") == o.get("expect", {}).get("kitQ")
              and oi.get("cd") == 5.0 and oi.get("dmg") == 200
              and (oi.get("rigChildren") or -1) > 0 and oi.get("teamCount") == 6
              and o.get("castOk"))
        print("W2 SMOKE RESULT:", "PASS" if ok else "FAIL")
        return 0 if ok else 1

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=915,412", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
code = 1
try:
    code = asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(code)
