"""Verify that every hero's Ultimate (and directional secondaries) spawn in front of the
caster, along the caster's facing, and keep that facing while the VFX animates.
Captures top-down screenshots into the conversation scratch folder."""
import asyncio, json, urllib.request, websockets, subprocess, os, base64, sys

EDGE = next(p for p in [r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                        r'C:\Program Files\Microsoft\Edge\Application\msedge.exe'] if os.path.exists(p))
OUT = r'C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch'
PORT = 9311
HEROES = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']
# Neji's Kaiten and Gaara's shield are centred on the caster by design.
SELF_CENTRED = {'1nej'}

CAST_JS = r'''
(async ({heroId, angle, slot}) => {
  const U = window.units;
  let c = U.find(u => u.heroId === heroId);
  if (!c) {
    const foeCand = U.find(u => u.team === 'red');
    c = U.find(u => u !== foeCand && !u.isPlayer) || U[0];
    c.heroId = heroId;
    c.kit = (window.HERO_KITS || {})[heroId] || c.kit;
  }
  for (const u of U) { u.deadTimer = 0; u.hp = 99999; u.maxHp = 99999; u.animTimer = 0; }
  // park everyone far away, then put ONE enemy 7u along the requested direction
  U.forEach((u, i) => { u.x = -80 + i * 3; u.z = 80; if (u.mesh) u.mesh.position.set(u.x, 0, u.z); });
  const OX = -32, OZ = 22; c.x = OX; c.z = OZ; c.rotY = angle;
  const foe = U.find(u => u.team !== c.team && u !== c);
  foe.x = OX + Math.sin(angle) * 7; foe.z = OZ + Math.cos(angle) * 7;
  [c, foe].forEach(u => u.mesh && u.mesh.position.set(u.x, 0, u.z));
  const before = new Set(window.vfxList.map(v => v.mesh));
  const pBefore = new Set(window.projectiles.map(p => p.mesh));
  c.cds[slot] = 0; c.chakra = 100;
  window.executeSkill(c, slot);
  const fresh = window.vfxList.filter(v => !before.has(v.mesh));
  const freshP = window.projectiles.filter(p => !pBefore.has(p.mesh));
  await new Promise(r => setTimeout(r, 450));   // let the update loop animate it
  const dx = Math.sin(c.rotY), dz = Math.cos(c.rotY);
  const wrap = a => Math.atan2(Math.sin(a), Math.cos(a));
  const rep = fresh.filter(v => v.style === 'compound').map(v => {
    const p = v.mesh.position;
    return { dir: !!v.directional, fwd: +((p.x - c.x) * dx + (p.z - c.z) * dz).toFixed(2),
             side: +(-(p.x - c.x) * dz + (p.z - c.z) * dx).toFixed(2),
             yawErr: v.directional ? +Math.abs(wrap(v.mesh.rotation.y - c.rotY)).toFixed(3) : null };
  });
  const proj = freshP.map(p => ({ yawErr: +Math.abs(wrap(p.mesh.rotation.y - c.rotY)).toFixed(3),
    velAlign: +((p.vx * dx + p.vz * dz) / Math.hypot(p.vx, p.vz)).toFixed(3) }));
  window.cameraMode = 'cinematic';
  window.camera.position.set(OX - 4, 19, OZ + 15); window.camera.lookAt(OX + 3, 1, OZ);
  window.camera.updateMatrixWorld(true);
  return { rotY: +c.rotY.toFixed(3), vfx: rep, proj };
})
'''

async def main():
    proc = subprocess.Popen([EDGE, '--headless=new', f'--remote-debugging-port={PORT}',
        '--user-data-dir=C:/temp/edge_ultdir', '--no-first-run', '--no-default-browser-check',
        '--inprivate', '--window-size=1400,900', 'http://localhost:8080/index.html'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    fails = []
    try:
        await asyncio.sleep(2.5)
        tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{PORT}/json').read())
        ws = await websockets.connect([t['webSocketDebuggerUrl'] for t in tabs if 'localhost' in t['url']][0],
                                      max_size=50_000_000, compression=None)
        await ws.send(json.dumps({'id': 1, 'method': 'Network.enable'}))
        await ws.send(json.dumps({'id': 2, 'method': 'Network.setCacheDisabled', 'params': {'cacheDisabled': True}}))
        mid = [100]
        async def ev(expr):
            mid[0] += 1; i = mid[0]
            await ws.send(json.dumps({'id': i, 'method': 'Runtime.evaluate',
                'params': {'expression': expr, 'awaitPromise': True, 'returnByValue': True}}))
            while True:
                r = json.loads(await ws.recv())
                if r.get('id') == i:
                    res = r.get('result', {})
                    if 'exceptionDetails' in res: raise RuntimeError(json.dumps(res['exceptionDetails'])[:400])
                    return res.get('result', {}).get('value')
        async def snap(name):
            try:
                mid[0] += 1; i = mid[0]
                await ws.send(json.dumps({'id': i, 'method': 'Page.captureScreenshot', 'params': {'format': 'png'}}))
                while True:
                    r = json.loads(await ws.recv())
                    if r.get('id') == i:
                        if os.path.exists(OUT):
                            open(os.path.join(OUT, name), 'wb').write(base64.b64decode(r['result']['data']))
                        return
            except Exception as e:
                pass
        await ev('''(async()=>{for(let w=0;w<150;w++){if(window.applyArena&&window.arenasCatalog&&window.arenasCatalog.length)break;
            await new Promise(r=>setTimeout(r,200));}
            await window.applyArena('sd03b'); await window.start5v5Match();
            for(let w=0;w<150;w++){if(window.units&&window.units.length>=10)break;
            await new Promise(r=>setTimeout(r,100));}
            for(const id of ['center-banner','death-overlay']){const e=document.getElementById(id); if(e) e.style.display='none';}
            window.__origEnd = window.endMatch; })()''')
        await asyncio.sleep(0.5)
        cases = [(h, 'r') for h in HEROES] + [('1kks', 'w'), ('1jry', 'q'), ('1gar', 'q'), ('1nej', 'w'), ('1hnt', 'w')]
        for hero, slot in cases:
            for angle, tag in [(1.5708, 'E'), (-2.3562, 'SW')]:
                r = await ev(f'({CAST_JS})({json.dumps({"heroId": hero, "angle": angle, "slot": slot})})')
                ok = True
                for v in r['vfx']:
                    if v['dir'] and v['yawErr'] > 0.05: ok = False
                    if slot == 'r' and hero not in SELF_CENTRED and v['dir'] and v['fwd'] < 1.0: ok = False
                for p in r['proj']:
                    if p['velAlign'] < 0.99 or p['yawErr'] > 0.05: ok = False
                print(f"{'PASS' if ok else 'FAIL'} {hero} {slot} {tag}: {json.dumps(r)}")
                if not ok: fails.append((hero, slot, tag))
                if tag == 'E':
                    await asyncio.sleep(0.05); await snap(f'ultdir_{hero}_{slot}.png')
                await asyncio.sleep(1.2)
        await ws.close()
    finally:
        proc.kill()
    print('\nRESULT:', 'ALL PASS' if not fails else f'{len(fails)} FAIL -> {fails}')
    sys.exit(1 if fails else 0)

if __name__ == '__main__':
    asyncio.run(main())
