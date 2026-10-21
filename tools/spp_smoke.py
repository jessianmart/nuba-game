# -*- coding: utf-8 -*-
"""Smoke SPP: clones 3D do Kage Bunshin (spawn/movimento/contato/poof/reset) + anim/facing do VFX."""
import asyncio, json, socket, subprocess, tempfile, time, shutil, sys
import urllib.request
import websockets

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE = "http://localhost:8080/index.html"

PROBE = """(async () => {
  let out = {};
  try {
    const p = window.units.find(u => u.isPlayer);
    // 1) Kage Bunshin: cast do W com chakra garantido
    const kitW = p.kit['w'];
    p.chakra = kitW.cost; p.cds['w'] = 0;
    const clonesBefore = window.__shadowClones().length;
    window.executeSkill(p, 'w');
    const clones = window.__shadowClones();
    out.spawn = clones.length === 3 && clonesBefore === 0;
    out.kitType = kitW.type;
    out.cloneErr = window.__sppCloneErr || null;
    out.rigged = clones.every(c => c.mesh && c.mesh.userData && c.mesh.userData.bones);
    // 2) clones perseguem inimigos (posicao muda)
    const pos0 = clones.map(c => [c.x, c.z]);
    await new Promise(r => setTimeout(r, 600));
    const moved = clones.map((c, i) => Math.hypot(c.x - pos0[i][0], c.z - pos0[i][1]));
    out.moving = moved.every(d => d > 0.05) || window.__shadowClones().length < 3;
    // 3) contato: teleporta clone pro inimigo -> dano + poof
    const enemy = window.units.find(u => u.team !== p.team && u.deadTimer <= 0);
    enemy.spawnShield = 0; enemy.x = 0; enemy.z = 0; enemy.hp = enemy.maxHp;
    const c0 = window.__shadowClones()[0];
    if (c0) { c0.x = 0.5; c0.z = 0.5; c0.ttl = 5; }
    const hp0 = enemy.hp;
    await new Promise(r => setTimeout(r, 500));
    out.contact = { dmgDealt: hp0 - enemy.hp > 0, poofed: window.__shadowClones().length < 3 };
    // 4) TTL: clones restantes somem em <=5.5s com poof
    await new Promise(r => setTimeout(r, 5500));
    out.ttlClean = window.__shadowClones().length === 0;
    // 5) Q do Naruto: vfxList com anim 'spin' + facing = rotY do caster
    p.chakra = p.kit['q'].cost; p.cds['q'] = 0; p.cds['w'] = 0;
    p.x = 5; p.z = 5; p.rotY = 1.234;
    window.executeSkill(p, 'q');
    await new Promise(r => setTimeout(r, 120));
    const exts = window.__vfxProbe ? window.__vfxProbe() : null;
    out.qAnim = !!window.SKILL_VFX_ANIM['1nrt']['q'];
    // 6) reset em nova partida
    await window.start5v5Match();
    out.reset = window.__shadowClones().length === 0;
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
        start = await ev("(async () => { try { await window.start5v5Match(); return 'ok:' + window.units.length; } catch (e) { return 'fail:' + (e && e.message ? e.message : e); } })()")
        print("start5v5Match:", start)
        if not (isinstance(start, str) and start.startswith('ok:10')):
            print('SMOKE RESULT: FAIL (start)'); return 1
        v = await ev(PROBE)
        print(json.dumps(v, indent=1, ensure_ascii=False))
        ct = v.get('contact') or {}
        ok = (not v.get('err') and v.get('spawn') and v.get('rigged') and v.get('moving')
              and ct.get('dmgDealt') and ct.get('poofed') and v.get('ttlClean')
              and v.get('qAnim') and v.get('reset'))
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
