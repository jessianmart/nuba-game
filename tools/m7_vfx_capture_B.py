# -*- coding: utf-8 -*-
"""M7 B: valida e captura VFX de skill (q/w/e/r) de 1roc, 1itc e 1gar — 12 casts.

Nao edita nenhum arquivo do repo; apenas le o jogo via CDP em Edge headless.
Resultados em stdout (RESULTS_JSON) — entrega via m7_results_B.json (write_file).
"""
import asyncio, base64, json, os, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
SHOTS_DIR = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

# esperado pelo brief (verificado tb em runtime via window.SKILL_VFX_MAP)
HEROES = [
    ("1roc", {"q": "whirlwind", "w": "air_tornado", "e": "leaf_flurry", "r": "air_tornado"}),
    ("1itc", {"q": "amaterasu_flame", "w": "crow_smoke", "e": "crow_smoke", "r": "amaterasu_flame"}),
    ("1gar", {"q": "1gareff1_bd_snd02", "w": "1gareff1_hnd01_body", "e": "sand_dust", "r": "1gareff1_snd15"}),
]
SLOTS = ["q", "w", "e", "r"]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def js_silence():
    # IA so chama executeSkill apos pre-checar cds<=0 e chakra>=cost (updateAIBotUnit);
    # bloquear cds (nao sao resetados no respawn) impede QUALQUER cast concorrente,
    # que senao sobrescreveria a global activeSkillVfxModel (setada no topo de executeSkill).
    return ("(function(){"
            " for (const u of window.units) { u.chakra = 0;"
            "   for (const k of ['q','w','e','r','atk']) u.cds[k] = 9999; }"
            " return window.units.length; })()")


def js_cast(hero, slot):
    # atomico (JS single-thread): setup + cast em uma expressao — nenhum tick da IA
    # roda entre o reset de cds e o cast, nem entre o cast e o re-bloqueio.
    return ("(function(){"
            " const H = window.units.find(u => u.heroId === '" + hero + "');"
            " if (!H) return { error: 'hero not found' };"
            " const E = window.units.find(u => u.team !== H.team && !(u.deadTimer > 0))"
            "         || window.units.find(u => u.team !== H.team);"
            " if (E) { E.x = H.x + 4; E.z = H.z; }"
            " if (H.deadTimer > 0) H.deadTimer = 0;"
            " H.chakra = 100;"
            " for (const k of ['q','w','e','r']) H.cds[k] = 0;"
            " for (const u of window.units) if (u !== H) { u.chakra = 0;"
            "   for (const k of ['q','w','e','r','atk']) u.cds[k] = 9999; }"
            " const before = window.vfxList.filter(v => v.style === 'extracted').length;"
            " window.executeSkill(H, '" + slot + "');"
            " for (const k of ['q','w','e','r','atk']) if (k !== '" + slot + "') H.cds[k] = 9999;"
            " return { before: before };"
            "})()")


def js_state(hero, slot):
    return ("(function(){"
            " return { active: window.__activeVfxModel(),"
            "          expected: window.SKILL_VFX_MAP['" + hero + "']['" + slot + "'],"
            "          extracted: window.vfxList.filter(v => v.style === 'extracted').length };"
            "})()")


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self.mid = 0
        self.exceptions = []

    async def call(self, method, params=None):
        self.mid += 1
        req = {"id": self.mid, "method": method}
        if params:
            req["params"] = params
        await self.ws.send(json.dumps(req))
        while True:
            data = json.loads(await asyncio.wait_for(self.ws.recv(), timeout=120))
            if "id" in data:
                if data["id"] == self.mid:
                    if "error" in data:
                        raise RuntimeError(f"{method}: {data['error']}")
                    return data.get("result", {})
            elif data.get("method") == "Runtime.exceptionThrown":
                d = data.get("params", {}).get("exceptionDetails", {})
                exc = (d.get("exception") or {}).get("description") or d.get("text", "")
                self.exceptions.append(f"{method}| {exc}".strip())
                print(f"[JS-EXCEPTION] {exc}", flush=True)

    async def ev(self, expr):
        r = await self.call("Runtime.evaluate",
                            {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in r:
            d = r["exceptionDetails"]
            raise RuntimeError(f"JS error: {d.get('text')} {(d.get('exception') or {}).get('description', '')}")
        return r.get("result", {}).get("value")


async def main(port):
    # /json do DevTools (com retry — Edge pode levar alguns segundos)
    info = None
    for _ in range(10):
        try:
            info = json.load(urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=5))
            break
        except Exception:
            time.sleep(1.0)
    if not info:
        raise RuntimeError("DevTools /json inacessivel")
    page = next(t for t in info if t.get("type") == "page")
    async with websockets.connect(page["webSocketDebuggerUrl"], max_size=20_000_000) as ws:
        cdp = CDP(ws)
        await cdp.call("Page.enable")
        await cdp.call("Runtime.enable")  # necessario p/ receber Runtime.exceptionThrown
        await cdp.call("Emulation.setDeviceMetricsOverride",
                       {"width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
        await cdp.call("Page.navigate", {"url": BASE})
        ready = False
        for _ in range(30):
            if await cdp.ev("typeof window.start5v5Match === 'function'"):
                ready = True
                break
            await asyncio.sleep(2)
        if not ready:
            raise RuntimeError("readiness timeout: start5v5Match nao apareceu")
        print("[READY] start5v5Match exposta", flush=True)

        os.makedirs(SHOTS_DIR, exist_ok=True)
        results = []
        for hero, exp_map in HEROES:
            await cdp.ev("window.start5v5Match()")  # nova partida por heroi
            mactive = False
            for _ in range(30):
                if await cdp.ev("window.matchActive === true"):
                    mactive = True
                    break
                await asyncio.sleep(2)
            if not mactive:
                raise RuntimeError(f"matchActive timeout para {hero}")
            for _ in range(10):
                if await cdp.ev("!!window.units.find(u => u.heroId === '" + hero + "')"):
                    break
                await asyncio.sleep(1)
            n_units = await cdp.ev(js_silence()) or 0
            print(f"[{hero}] partida ativa, {n_units} unidades silenciadas (IA sem cast)", flush=True)

            for slot in SLOTS:
                cast = await cdp.ev(js_cast(hero, slot))  # setup+cast atomicos
                if not cast or cast.get("error"):
                    raise RuntimeError(f"cast {hero}:{slot} falhou no setup: {cast}")
                before = cast.get("before") or 0
                await asyncio.sleep(0.35)
                st = await cdp.ev(js_state(hero, slot))
                shot_path = os.path.join(SHOTS_DIR, f"m7_{hero}_{slot}.png")
                shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
                with open(shot_path, "wb") as f:
                    f.write(base64.b64decode(shot["data"]))
                rec = {
                    "hero": hero, "slot": slot,
                    "active": st.get("active"), "expected": st.get("expected"),
                    "ok": st.get("active") == st.get("expected"),
                    "extractedDelta": (st.get("extracted") or 0) - before,
                    "shot": shot_path,
                }
                results.append(rec)
                print(f"[{hero}:{slot}] active={rec['active']} expected={rec['expected']} "
                      f"ok={rec['ok']} extractedDelta={rec['extractedDelta']} -> {shot_path}",
                      flush=True)
                if rec["expected"] != exp_map[slot]:
                    print(f"[WARN] runtime expected {rec['expected']} != brief {exp_map[slot]}", flush=True)

        print("RESULTS_JSON=" + json.dumps(results, ensure_ascii=False), flush=True)
        print("EXCEPTIONS=" + json.dumps(cdp.exceptions, ensure_ascii=False), flush=True)
        return results, list(cdp.exceptions)


if __name__ == "__main__":
    port = free_port()
    tmp = tempfile.mkdtemp(prefix="m7capB_")
    proc = subprocess.Popen([EDGE, "--headless=new",
                             f"--remote-debugging-port={port}", "--disable-gpu",
                             "--window-size=1280,720", "--inprivate",
                             f"--user-data-dir={tmp}", "about:blank"])
    time.sleep(3)
    exit_code = 1
    try:
        results, exceptions = asyncio.run(main(port))
        exit_code = 0 if (len(results) == 12 and all(r["ok"] for r in results)) else 1
    finally:
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)  # so o MEU TEMP/Edge
    sys.exit(exit_code)
