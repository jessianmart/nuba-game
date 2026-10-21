# -*- coding: utf-8 -*-
"""M7 A: valida e captura VFX de skill (q/w/e/r) de 1nrt, 1ssk, 1skr, 1kks — 16 casts.

Nao edita nenhum arquivo do repo; apenas le o jogo via CDP em Edge headless.
Resultados em stdout (RESULTS_JSON) — entrega via m7_results_A.json (write_file).
"""
import asyncio, base64, json, os, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"
SHOTS_DIR = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots"

# esperado pelo brief (verificado tb em runtime via window.SKILL_VFX_MAP)
HEROES = [
    ("1nrt", {"q": "rasengan", "w": "smoke", "e": "1efc_log01", "r": "giant_rasengan"}),
    ("1ssk", {"q": "chidori_spark", "w": "fireball", "e": "1sskeff1_sharin01", "r": "1sskeff1_aura01"}),
    ("1skr", {"q": "shatter", "w": "heal_chakra", "e": "1efc_log01", "r": "shatter"}),
    ("1kks", {"q": "raikiri_spark", "w": "water_dragon", "e": "raikiri_spark", "r": "1kkseff1_sharin01"}),
]
SLOTS = ["q", "w", "e", "r"]


def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def js_setup_and_cast(hero, slot):
    # passos (2)-(6): acha heroi, teleporta inimigo perto, reseta chakra/cds,
    # registra vfxBefore/extractedBefore e faz o cast — numa unica expressao.
    return ("(function(){"
            " const H = window.units.find(u => u.heroId === '" + hero + "');"
            " if (!H) return { heroFound: false };"
            " const E = window.units.find(u => u.team !== H.team && !(u.deadTimer > 0))"
            "         || window.units.find(u => u.team !== H.team);"
            " if (E) { E.x = H.x + 4; E.z = H.z; }"
            " const heroWasDead = H.deadTimer > 0;"
            " if (heroWasDead) H.deadTimer = 0;"
            " H.chakra = 100;"
            " for (const k of ['q','w','e','r']) H.cds[k] = 0;"
            " const vfxBefore = window.vfxList.length;"
            " const extractedBefore = window.vfxList.filter(v => v.style === 'extracted').length;"
            " window.executeSkill(H, '" + slot + "');"
            " const activeNow = window.__activeVfxModel();"  # mesmo tick do cast: imune a casts de bot
            " return { heroFound: true, heroWasDead: heroWasDead, enemyMoved: !!E,"
            "          vfxBefore: vfxBefore, extractedBefore: extractedBefore, activeNow: activeNow };"
            "})()")


def js_state(hero, slot):
    # leitura tardia (+350ms): activeLate e so diagnostico de race (bots castam na janela)
    return ("(function(){"
            " return { activeLate: window.__activeVfxModel(),"
            "          expected: window.SKILL_VFX_MAP['" + hero + "']['" + slot + "'],"
            "          vfxNow: window.vfxList.length,"
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
        for _ in range(20):
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
            await cdp.ev("window.start5v5Match()")  # nova partida por heroi (awaitPromise espera o reset)
            mactive = False
            for _ in range(30):
                if await cdp.ev("window.matchActive === true"):
                    mactive = True
                    break
                await asyncio.sleep(1.5)
            if not mactive:
                raise RuntimeError(f"matchActive timeout para {hero}")
            for _ in range(10):
                if await cdp.ev("!!window.units.find(u => u.heroId === '" + hero + "')"):
                    break
                await asyncio.sleep(1)
            print(f"[MATCH] {hero} ativo", flush=True)

            for slot in SLOTS:
                try:
                    pre = await cdp.ev(js_setup_and_cast(hero, slot))
                    if not pre or not pre.get("heroFound"):
                        raise RuntimeError(f"unidade {hero} nao encontrada antes de {slot}")
                    await asyncio.sleep(0.35)
                    st = await cdp.ev(js_state(hero, slot))
                    shot_path = os.path.join(SHOTS_DIR, f"m7_{hero}_{slot}.png")
                    shot = await cdp.call("Page.captureScreenshot", {"format": "png"})
                    with open(shot_path, "wb") as f:
                        f.write(base64.b64decode(shot["data"]))
                    rec = {
                        "hero": hero, "slot": slot,
                        "active": pre.get("activeNow"), "expected": st.get("expected"),
                        "ok": pre.get("activeNow") == st.get("expected"),
                        "extractedDelta": (st.get("extracted") or 0) - (pre.get("extractedBefore") or 0),
                        "shot": shot_path,
                    }
                    results.append(rec)
                    print(f"[{hero}:{slot}] active={rec['active']} expected={rec['expected']} "
                          f"ok={rec['ok']} extractedDelta={rec['extractedDelta']} "
                          f"vfxBefore={pre.get('vfxBefore')} vfxNow={st.get('vfxNow')} "
                          f"activeLate={st.get('activeLate')} "
                          f"heroWasDead={pre.get('heroWasDead')} -> {shot_path}", flush=True)
                    if rec["expected"] != exp_map[slot]:
                        print(f"[WARN] runtime expected {rec['expected']} != brief {exp_map[slot]}", flush=True)
                except Exception as e:
                    rec = {"hero": hero, "slot": slot, "active": None,
                           "expected": exp_map[slot], "ok": False, "extractedDelta": None,
                           "shot": os.path.join(SHOTS_DIR, f"m7_{hero}_{slot}.png"),
                           "error": str(e)}
                    results.append(rec)
                    print(f"[{hero}:{slot}] ERRO: {e}", flush=True)

        print("RESULTS_JSON=" + json.dumps(results, ensure_ascii=False), flush=True)
        print("EXCEPTIONS=" + json.dumps(cdp.exceptions, ensure_ascii=False), flush=True)
        return results, list(cdp.exceptions)


if __name__ == "__main__":
    port = free_port()
    tmp = tempfile.mkdtemp(prefix="m7capA_")
    proc = subprocess.Popen([EDGE, "--headless=new",
                             f"--remote-debugging-port={port}", "--disable-gpu",
                             "--window-size=1280,720", "--inprivate",
                             f"--user-data-dir={tmp}", "about:blank"])
    time.sleep(3)
    exit_code = 1
    try:
        results, exceptions = asyncio.run(main(port))
        exit_code = 0 if (len(results) == 16 and all(r["ok"] for r in results) and not exceptions) else 1
    finally:
        try:
            proc.kill()
            proc.wait(timeout=3)
        except Exception:
            pass
        shutil.rmtree(tmp, ignore_errors=True)  # so o MEU TEMP/Edge
    sys.exit(exit_code)
