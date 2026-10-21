# -*- coding: utf-8 -*-
"""P2 captacao A: valida stats + kits dos herois 1nrt/1ssk/1skr/1kks no NUBA.

Por heroi: start5v5Match -> acha unit -> le maxHp/speed/reg/kit -> DR probe
(dealDamage 100) -> screenshot 1280x720. Grava p2_results_A.json.
NAO edita nada do repo do jogo; roda o proprio Edge headless e mata so ele.
"""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys, os
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
OUT_DIR = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"
RESULTS = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\p2_results_A.json"

# esperados: hp, spd, speed (base*mult), dr, loss=round(100*dr), reg, kit q/w/e/r
HEROES = {
    "1nrt": dict(hp=1050, spd=1.06, speed=21.5 * 1.06, dr=1.00, reg=1.15,
                 kit=dict(q=dict(dmg=250, cd=6.0, cost=25),
                          w=dict(dmg=160, cd=8.0, cost=20),
                          e=dict(dmg=0, cd=10.0, cost=15),
                          r=dict(dmg=480, cd=22.0, cost=50))),
    "1ssk": dict(hp=920, spd=1.10, speed=19.5 * 1.10, dr=1.05, reg=1.00,
                 kit=dict(q=dict(dmg=235, cd=4.8, cost=25),
                          w=dict(dmg=220, cd=6.5, cost=20),
                          e=dict(dmg=70, cd=8.5, cost=15),
                          r=dict(dmg=470, cd=20.0, cost=50))),
    "1skr": dict(hp=1000, spd=1.00, speed=19.5 * 1.00, dr=0.95, reg=1.30,
                 kit=dict(q=dict(dmg=205, cd=6.5, cost=25),
                          w=dict(dmg=300, cd=11.0, cost=30),
                          e=dict(dmg=0, cd=8.5, cost=15),
                          r=dict(dmg=400, cd=22.0, cost=50))),
    "1kks": dict(hp=950, spd=1.08, speed=19.5 * 1.08, dr=1.05, reg=1.00,
                 kit=dict(q=dict(dmg=265, cd=6.0, cost=25),
                          w=dict(dmg=200, cd=7.0, cost=20),
                          e=dict(dmg=90, cd=9.0, cost=15),
                          r=dict(dmg=460, cd=22.0, cost=50))),
}

PROBE = """(hero) => {
  const u = window.units.find(x => x.heroId === hero);
  if (!u) return { error: 'unit-not-found' };
  const p = window.units.find(x => x.isPlayer);
  const out = {
    maxHp: u.maxHp, speed: u.speed, isPlayer: !!u.isPlayer,
    reg: window.HERO_STATS[hero].reg,
    kit: {
      q: { dmg: u.kit.q.dmg, cd: u.kit.q.cd, cost: u.kit.q.cost },
      w: { dmg: u.kit.w.dmg, cd: u.kit.w.cd, cost: u.kit.w.cost },
      e: { dmg: u.kit.e.dmg, cd: u.kit.e.cd, cost: u.kit.e.cost },
      r: { dmg: u.kit.r.dmg, cd: u.kit.r.cd, cost: u.kit.r.cost },
    },
    playerHero: p ? p.heroId : null,
    playerAwakened: p ? (p.awakenedTimer || 0) : null,
    playerLevel: p ? p.level : null,
  };
  // DR probe em run unica: alvo cheio, dano bruto 100 pelo player
  u.hp = u.maxHp;
  window.dealDamage(p, u, 100, 'probe');
  out.drLoss = u.maxHp - u.hp;
  return out;
}"""


async def main(port):
    info = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json"))
    page = next(t for t in info if t.get("type") == "page")
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
        mid = 0

        async def call(method, params=None):
            nonlocal mid
            mid += 1
            req = {"id": mid, "method": method}
            if params:
                req["params"] = params
            await ws.send(json.dumps(req))
            while True:
                data = json.loads(await asyncio.wait_for(ws.recv(), timeout=120))
                if data.get("id") == mid:
                    if "error" in data:
                        raise RuntimeError(f"{method}: {data['error']}")
                    return data.get("result", {})

        async def ev(expr):
            r = await call("Runtime.evaluate",
                           {"expression": expr, "returnByValue": True, "awaitPromise": True})
            res = r.get("result", {})
            if res.get("type") == "object" and "value" not in res and res.get("subtype") == "error":
                raise RuntimeError(f"JS error: {r}")
            return res.get("value")

        await call("Page.enable")
        await call("Page.navigate", {"url": BASE})
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("typeof window.start5v5Match === 'function'"):
                break
        else:
            raise RuntimeError("pagina nao carregou (start5v5Match indisponivel)")

        results = []
        for hero, exp in HEROES.items():
            # partida fresca por heroi (start5v5Match reconstroi units);
            # retry se a primeira chamada (warm-up de modelos) nao spawnar a tempo
            probe = None
            for attempt in range(3):
                await ev("window.start5v5Match()")
                active = None
                for _ in range(20):
                    await asyncio.sleep(1.5)
                    active = await ev("window.matchActive")
                    if active:
                        break
                if not active:
                    break
                # espera a unidade do heroi existir em window.units
                for _ in range(20):
                    await asyncio.sleep(1.0)
                    probe = await ev(f"({PROBE})({json.dumps(hero)})")
                    if probe and "error" not in probe:
                        break
                if probe and "error" not in probe:
                    break
            if not probe or "error" in probe:
                results.append({"hero": hero, "ok": False, "error": probe or "match-nao-ativou"})
                continue

            exp_speed = exp["speed"]
            exp_loss = round(100 * exp["dr"])
            checks = {
                "maxHp": probe["maxHp"] == exp["hp"],
                "speed": abs(probe["speed"] - exp_speed) < 0.02,
                "reg": probe["reg"] == exp["reg"],
                "drLoss": probe["drLoss"] == exp_loss,
                "playerIs1nrt": probe["playerHero"] == "1nrt",
            }
            for slot in ("q", "w", "e", "r"):
                k = exp["kit"][slot]
                checks[f"kit{slot}"] = (
                    probe["kit"][slot]["dmg"] == k["dmg"]
                    and abs(probe["kit"][slot]["cd"] - k["cd"]) < 0.001
                    and probe["kit"][slot]["cost"] == k["cost"]
                )
            ok = all(checks.values())

            shot = os.path.join(OUT_DIR, f"p2_{hero}.png")
            res = await call("Page.captureScreenshot",
                             {"format": "png", "captureBeyondViewport": False})
            data = res.get("data", "")
            with open(shot, "wb") as f:
                f.write(__import__("base64").b64decode(data))

            row = {
                "hero": hero,
                "maxHp": probe["maxHp"], "maxHpExpected": exp["hp"],
                "speed": probe["speed"], "speedExpected": round(exp_speed, 4),
                "drLoss": probe["drLoss"], "drLossExpected": exp_loss,
                "reg": probe["reg"],
                "isPlayer": probe["isPlayer"],
                "kitQ": probe["kit"]["q"], "kitW": probe["kit"]["w"],
                "kitE": probe["kit"]["e"], "kitR": probe["kit"]["r"],
                "ok": ok, "checks": checks, "shot": shot,
            }
            if probe.get("playerAwakened") is not None and probe["playerAwakened"] > 0:
                row["warnPlayerAwakened"] = probe["playerAwakened"]
            results.append(row)
            print(f"[{hero}] ok={ok} " + json.dumps({k: v for k, v in row.items() if k not in ('checks',)}))

        with open(RESULTS, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        allok = all(r.get("ok") for r in results)
        print("RESULTADO FINAL:", "PASS" if allok else "FAIL")
        return 0 if allok else 1


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


if __name__ == "__main__":
    port = free_port()
    tmp = tempfile.mkdtemp()
    proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}",
                             "--disable-gpu", "--window-size=1280,720", "--inprivate",
                             f"--user-data-dir={tmp}", "about:blank"])
    time.sleep(3.0)
    code = 1
    try:
        code = asyncio.run(main(port))
    finally:
        try:
            proc.kill()
            proc.wait(timeout=5)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)
    sys.exit(code)
