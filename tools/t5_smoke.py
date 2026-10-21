# -*- coding: utf-8 -*-
"""Smoke T5 MATCH PACE: HP x1.5, dano x0.9, prorrogacao 1min, morte subita, vitoria por tempo."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

PROBE = """(async () => {
  let out = {};
  try {
    const S = window.__matchState;
    const p = window.units.find(u => u.isPlayer);
    out.diag = { units: window.units.length, matchActive: window.matchActive, teams: window.units.map(u => u.team) };
    // 1) HP escalado x1.5 em TODAS as units
    out.hpScale = window.units.every(u => u.maxHp === Math.round(window.HERO_STATS[u.heroId].hp * 1.5));
    // 2) dano global x0.9 (bot longe da base, sem shield)
    const bot = window.units.find(u => !u.isPlayer && u.team !== p.team);
    bot.spawnShield = 0; bot.x = 0; bot.z = 0; bot.hp = bot.maxHp;
    window.dealDamage(p, bot, 100, 'probe');
    out.dmgScale = (bot.maxHp - bot.hp) === Math.max(1, Math.round(100 * 0.9 * window.HERO_STATS[bot.heroId].dr));
    // 3) prorrogacao: tempo no fim + empate 0-0
    S.time = 0.3;
    await new Promise(r => setTimeout(r, 700));
    out.overtimeOn = S.overtime === true && !S.suddenDeath;
    out.overtimeTime = (S.time >= 59 && S.time <= 60);
    const mtEl = document.getElementById('match-timer');
    out.overtimeClass = mtEl && mtEl.classList.contains('overtime');
    // 4) prorrogacao empatada -> morte subita
    S.time = 0.3;
    await new Promise(r => setTimeout(r, 700));
    out.suddenOn = S.suddenDeath === true;
    out.suddenClass = mtEl && mtEl.classList.contains('sudden');
    out.matchStillLive = !window.__isMatchEnding();
    // 5) morte subita: proximo abate decide
    const bot2 = window.units.find(u => !u.isPlayer && u.team !== p.team && u.deadTimer <= 0);
    bot2.spawnShield = 0; bot2.x = 0; bot2.z = 0; bot2.hp = 1;
    window.dealDamage(p, bot2, 9999, 'probe');
    await new Promise(r => setTimeout(r, 300));
    out.sdEndedMatch = window.__isMatchEnding();
    out.blueLead = S.blue > S.red;
    // 6) vitoria por tempo sem empate: nova partida, 1 abate, fim de tempo
    await window.start5v5Match();
    await new Promise(r => setTimeout(r, 400));
    const S2 = window.__matchState;
    const p2 = window.units.find(u => u.isPlayer);
    const bot3 = window.units.find(u => !u.isPlayer && u.team !== p2.team);
    bot3.spawnShield = 0; bot3.x = 0; bot3.z = 0; bot3.hp = 1;
    window.dealDamage(p2, bot3, 9999, 'probe');
    await new Promise(r => setTimeout(r, 200));
    const blueScored = S2.blue > 0;
    S2.time = 0.3;
    await new Promise(r => setTimeout(r, 700));
    out.timeWin = { blueScored: blueScored, overtime: S2.overtime, ended: window.__isMatchEnding() };
    return out;
  } catch (e) { return { err: String(e && e.message ? e.message : e), out }; }
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
        await call("Page.navigate", {"url": BASE})
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("typeof window.start5v5Match === 'function'"): break
        start = await ev("(async () => { try { await window.start5v5Match(); return 'ok:' + window.units.length + ':' + window.matchActive; } catch (e) { return 'fail:' + (e && e.message ? e.message : e); } })()")
        print("start5v5Match:", start)
        if not (isinstance(start, str) and start.startswith('ok:10:')):
            print('SMOKE RESULT: FAIL (start5v5Match nao entregou 10 units)'); return 1
        v = await ev(PROBE)
        print(json.dumps(v, indent=1, ensure_ascii=False))
        tw = v.get('timeWin') or {}
        ok = (v and v.get('hpScale') and v.get('dmgScale') and v.get('overtimeOn')
              and v.get('overtimeTime') and v.get('overtimeClass') and v.get('suddenOn')
              and v.get('suddenClass') and v.get('matchStillLive') and v.get('sdEndedMatch')
              and v.get('blueLead') and tw.get('blueScored') and not tw.get('overtime')
              and tw.get('ended'))
        print('SMOKE RESULT:', 'PASS' if ok else 'FAIL')
        return 0 if ok else 1

def free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0)); return s.getsockname()[1]

port = free_port()
tmp = tempfile.mkdtemp()
proc = subprocess.Popen([EDGE, "--headless=new", f"--remote-debugging-port={port}", "--disable-gpu",
                         "--window-size=1280,720", "--inprivate", f"--user-data-dir={tmp}", "about:blank"])
time.sleep(3.0)
code = 1
try:
    code = asyncio.run(main(port))
finally:
    try: proc.kill(); proc.wait(timeout=3)
    except Exception: pass
    shutil.rmtree(tmp, ignore_errors=True)
sys.exit(code)
