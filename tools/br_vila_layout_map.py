"""PV2.1: mapeia a malha real da vila (grade 10m, raycast) e GERA br_vila_layout.json
com: 10 spawns (anel com chao), centro de zona (maior clareira), 12 baús (POIs com hit).
Run: python tools/br_vila_layout_map.py   (cwd = repo root)
"""
import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

sys.path.insert(0, os.getcwd())
from tools.test_e2e_suite import CDPClient, find_edge_path  # noqa: E402

OUT_JSON = 'public/assets/data/br_vila_layout.json'


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


def http_json(port, path):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}{path}', timeout=5) as r:
        return json.load(r)


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


PORT = free_port()
PROFILE = tempfile.mkdtemp(prefix='nuba_map_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

GRID = """(() => {
  let stage = null;
  window.units[0].mesh.parent.traverse(o => {});
  let node = window.units[0].mesh;
  while (node.parent) node = node.parent;
  node.traverse(o => {
    if (stage || !o.children) return;
    if (o.children.some(ch => ch.userData && ch.userData.texture)) stage = o;
  });
  if (!stage) return { err: 'sem stage' };
  const rc = new THREE.Raycaster();
  rc.far = 800;
  const cells = [];
  for (let x = -140; x <= 140; x += 10) {
    for (let z = -140; z <= 140; z += 10) {
      rc.set(new THREE.Vector3(x, 400, z), new THREE.Vector3(0, -1, 0));
      const hits = rc.intersectObject(stage, true);
      if (hits.length) {
        const h = hits[0];
        cells.push({ x, z, d: +h.distance.toFixed(1), y: +h.point.y.toFixed(2), m: (h.object.userData && h.object.userData.name) || '?' });
      }
    }
  }
  return { n: cells.length, cells };
})()"""


async def main():
    tabs = None
    for _ in range(20):
        try:
            tabs = http_json(PORT, '/json')
            break
        except Exception:
            time.sleep(0.5)
    ws_url = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
    c = CDPClient(ws_url)
    await c.connect()

    await ev(c, "(async () => { window.setLobbyPage('arenas'); const card = document.querySelector('.arena-card[data-arena=\"sa00z\"]'); card.click(); await new Promise(r => setTimeout(r, 2500)); return 'ok'; })()", await_promise=True)
    await ev(c, "(async () => { try { await window.start5v5Match(); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
    n = -1
    for _ in range(60):
        n = await ev(c, 'window.units ? window.units.length : -1')
        if n == 10:
            break
        await asyncio.sleep(0.5)
    await asyncio.sleep(2)

    g = await ev(c, GRID)
    assert 'cells' in g, g
    cells = g['cells']
    print(f'[grade] {g["n"]}/841 celulas com geometria')

    # ---------- decisao do layout (python) ----------
    import math
    solid = {(c['x'], c['z']): c for c in cells}

    def ok(x, z):
        return (round(x / 10) * 10, round(z / 10) * 10) in solid

    # anel de spawn: r entre 85 e 125, 36 angulos — escolhe 10 equidistantes com chao
    ring = []
    for ang in range(0, 360, 10):
        a = math.radians(ang)
        for r in (110, 100, 90, 125, 80):
            x, z = round(math.cos(a) * r), round(math.sin(a) * r)
            if ok(x, z):
                ring.append((ang, x, z, r))
                break
    spawns = []
    if len(ring) >= 10:
        # escolhe 10 espacados
        chosen = []
        step = len(ring) / 10
        for i in range(10):
            chosen.append(ring[int(i * step) % len(ring)])
        # elimina duplicados
        seen = set()
        for ang, x, z, r in chosen:
            if (x, z) not in seen:
                seen.add((x, z))
                spawns.append({'x': x, 'z': z, 'angle': ang})
    print(f'[spawns] {len(spawns)} pontos com chao no anel: {[(s["x"], s["z"]) for s in spawns]}')

    # centro de zona: celula com mais vizinhos solidos num raio de 30 (maior clareira central)
    def density(x, z):
        d = 0
        for dx in range(-30, 40, 10):
            for dz in range(-30, 40, 10):
                if ok(x + dx, z + dz):
                    d += 1
        return d
    best = max(solid, key=lambda p: density(*p))
    zone_center = {'x': best[0], 'z': best[1]}
    print(f'[zona] centro: {zone_center} (densidade {density(*best)}/49)')

    # baús: 12 POIs espalhados com chao, longe dos spawns (>25u) e entre si (>18u)
    chests = []
    cand = sorted(solid.keys(), key=lambda p: -density(*p))
    for (x, z) in cand:
        if len(chests) >= 12:
            break
        if abs(x) > 130 or abs(z) > 130:
            continue
        if any((x - s['x']) ** 2 + (z - s['z']) ** 2 < 25 ** 2 for s in spawns):
            continue
        if any((x - cc['x']) ** 2 + (z - cc['z']) ** 2 < 18 ** 2 for cc in chests):
            continue
        if (x, z) == tuple(zone_center.values()):
            continue
        chests.append({'x': x, 'z': z})
    print(f'[baús] {len(chests)} POIs: {[(c["x"], c["z"]) for c in chests]}')

    layout = {
        'id': 'br_vila',
        'arena': 'sa00z',
        'source': 'raycast mesh grid 10m (probe tools/br_vila_layout_map.py)',
        'zoneCenter': zone_center,
        'zoneRadiusStart': 132,
        'zoneRadiusMin': 8,
        'zonePhases': 6,
        'spawnRing': spawns,
        'chests': chests,
        'notes': 'spawns/baús apenas em celulas com geometria real acima (raycast)'
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    print(f'[ok] layout gravado: {OUT_JSON} ({len(json.dumps(layout))} bytes)')
    print('BR LAYOUT MAP DONE')
    c.running = False


try:
    asyncio.run(main())
finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    shutil.rmtree(PROFILE, ignore_errors=True)
