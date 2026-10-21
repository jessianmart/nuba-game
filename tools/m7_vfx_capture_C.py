# -*- coding: utf-8 -*-
"""M7 C: valida e captura VFX de skill (q/w/e/r) de 1hnt, 1nej e 1jry — 12 casts.

Nao edita nenhum arquivo do repo; apenas le o jogo via CDP em Edge headless.
Resultados em stdout (RESULTS_JSON) — entrega via m7_results_C.json (write_file).
"""
import asyncio, base64, json, os, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
SHOTS_DIR = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

# esperado pelo brief (verificado tb em runtime via window.SKILL_VFX_MAP)
HEROES = [
    ("1hnt", {"q": "palms_rotation", "w": "lion_chakra", "e": "palms_rotation", "r": "lion_chakra"}),
    ("1nej", {"q": "kaiten_dome", "w": "air_palm", "e": "kaiten_dome", "r": "kaiten_dome"}),
    ("1jry", {"q": "toad_fire", "w": "1jryeff01", "e": "1efc_log01", "r": "chou_rasengan"}),
]
SLOTS = ["q", "w", "e", "r"]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def js_setup(hero):
    return ("(function(){"
            " const H = window.units.find(u => u.heroId === '" + hero + "');"
            " if (!H) return null;"
            " const E = window.units.find(u => u.team !== H.team && !(u.deadTimer > 0))"
            "         || window.units.find(u => u.team !== H.team);"
            " if (E) { E.x = H.x + 4; E.z = H.z; }"
            " if (H.deadTimer > 0) H.deadTimer = 0;"
            " H.chakra = 100;"
            " for (const k of ['q','w','e','r']) H.cds[k] = 0;"
            " return { heroFound: true, x: H.x, z: H.z, chakra: H.chakra };"
            "})()")


def js_cast(hero, slot):
    # Cast + leitura ATOMICOS: activeSkillVfxModel e um global cujo unico escritor e
    # executeSkill (game.js:2788), chamado tambem pela IA (q/w/e/r/atk) a todo momento;
    # ler em expressao separada apos 350ms seria corrida com casts de IA.
    return ("(function(){"
            " const H = window.units.find(u => u.heroId === '" + hero + "');"
            " if (!H) return null;"
            " window.executeSkill(H, '" + slot + "');"
            " return { active: window.__activeVfxModel(),"
            "          dead: H.deadTimer, chakra: H.chakra,"
            "          cdAfter: H.cds['" + slot + "'], hasKit: !!H.kit['" + slot + "'] };"
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

            for slot in SLOTS:
                setup = await cdp.ev(js_setup(hero))   # teleporte inimigo + chakra/cds por cast
                if not setup or not setup.get("heroFound"):
                    raise RuntimeError(f"unidade {hero} nao encontrada antes de {slot}")
                before = await cdp.ev(
                    "window.vfxList.filter(v => v.style === 'extracted').length") or 0
                cast = await cdp.ev(js_cast(hero, slot))  # cast + leitura atomicos
                active = (cast or {}).get("active")
                if active != exp_map[slot]:
                    print(f"[DIAG {hero}:{slot}] {json.dumps(cast)}", flush=True)
                await asyncio.sleep(0.35)  # janela p/ VFX spawn/render + screenshot
                st = await cdp.ev(js_state(hero, slot))
                if st.get("active") != active:
                    print(f"[INFO {hero}:{slot}] activeLate={st.get('active')} "
                          f"(cast de IA sobrescreveu o global apos 350ms; esperado em "
                          f"partida viva, o global e 'modelo do ultimo cast' do jogo)",
                          flush=True)
                shot_path = os.path.join(SHOTS_DIR, f"m7_{hero}_{slot}.png")
                shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
                with open(shot_path, "wb") as f:
                    f.write(base64.b64decode(shot["data"]))
                rec = {
                    "hero": hero, "slot": slot,
                    "active": active, "expected": st.get("expected"),
                    "ok": active == st.get("expected"),
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
    tmp = tempfile.mkdtemp(prefix="m7capC_")
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
