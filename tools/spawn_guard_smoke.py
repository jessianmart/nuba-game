# -*- coding: utf-8 -*-
"""Smoke SPAWN GUARD: bloqueio na base, libera longe, quebra ao atacar, respawna com shield."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

PROBE = """(async () => {
  try {
  await window.start5v5Match();
  await new Promise(r => setTimeout(r, 400));
  const unitsAfter = window.units.length;
  const p = window.units.find(u => u.isPlayer);
  const bot = window.units.find(u => !u.isPlayer && u.team !== p.team);
  const out = {};
  // 1) bot no spawn: shield ativo perto da base -> dano bloqueado
  out.spawnShield0 = bot.spawnShield;
  bot.hp = bot.maxHp;
  window.dealDamage(p, bot, 200, 'probe');
  out.blockedAtBase = bot.hp === bot.maxHp;
  // 2) longe da base -> dano passa
  bot.x = 0; bot.z = 0;
  window.dealDamage(p, bot, 200, 'probe');
  out.damageAway = bot.hp < bot.maxHp - 100;
  // 3) atacar quebra a propria protecao
  const bot2 = window.units.find(u => !u.isPlayer && u.team !== p.team && u.spawnShield > 0);
  const victim = window.units.find(u => !u.isPlayer && u.team === p.team);
  victim.spawnShield = 0; victim.x = bot2.x + 2; victim.z = bot2.z;
  window.dealDamage(bot2, victim, 50, 'probe');
  out.attackerShieldBroken = bot2.spawnShield === 0;
  // 4) respawn restaura shield
  const bot3 = window.units.find(u => !u.isPlayer && u.team !== p.team);
  bot3.deadTimer = 0.05; bot3.hp = 0;
  await new Promise(r => setTimeout(r, 600));
  out.respawnShield = bot3.deadTimer <= 0 ? bot3.spawnShield : -1;
  out.respawned = bot3.deadTimer <= 0 && bot3.hp === bot3.maxHp;
  // 5) label com classe shielded
  const anyShielded = window.units.some(u => u.spawnShield > 0 && u.labelEl && u.labelEl.classList.contains('shielded'));
  out.labelGlow = anyShielded;
  return { unitsAfter: window.units.length, out };
  } catch (e) { return { err: String(e && e.message ? e.message : e), unitsAfter: typeof window.units !== 'undefined' ? window.units.length : -1 }; }
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
        await call("Page.navigate", {"url": BASE})
        for _ in range(30):
            await asyncio.sleep(2.0)
            if await ev("typeof window.start5v5Match === 'function'"): break
        raw = await call("Runtime.evaluate", {"expression": PROBE, "returnByValue": True, "awaitPromise": True})
        print("RAW CDP:", json.dumps(raw, indent=1)[:2000])
        v = raw.get("result", {}).get("value")
        print(json.dumps(v, indent=1))
        o = (v or {}).get('out') or {}
        ok = (not (v or {}).get('err') and o.get('blockedAtBase') and o.get('damageAway')
              and o.get('attackerShieldBroken') and o.get('respawned')
              and o.get('respawnShield', 0) > 0 and o.get('labelGlow'))
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
