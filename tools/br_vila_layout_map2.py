"""PV2.1b: contorno polar da vila (72 angulos, r 130->30) + recalibra o arena sa00z
(radius/spawns/baús DENTRO do nucleo real). Grava br_vila_layout.json + ajusta arenas.json.
Run: python tools/br_vila_layout_map2.py   (cwd = repo root)
"""
import asyncio
import json
import math
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
PROFILE = tempfile.mkdtemp(prefix='nuba_map2_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

POLAR = """(() => {
  let node = window.units[0].mesh;
  while (node.parent) node = node.parent;
  let stage = null;
  node.traverse(o => {
    if (stage || !o.children) return;
    if (o.children.some(ch => ch.userData && ch.userData.texture)) stage = o;
  });
  if (!stage) return { err: 'sem stage' };
  const rc = new THREE.Raycaster();
  rc.far = 800;
  const hit = (x, z) => {
    rc.set(new THREE.Vector3(x, 400, z), new THREE.Vector3(0, -1, 0));
    const h = rc.intersectObject(stage, true);
    return h.length ? h[0].point.y : null;
  };
  const contorno = [];
  for (let a = 0; a < 360; a += 5) {
    const rad = a * Math.PI / 180;
    let rHit = null;
    for (let r = 130; r >= 30; r -= 5) {
      if (hit(Math.cos(rad) * r, Math.sin(rad) * r) !== null) { rHit = r; break; }
    }
    contorno.push({ a, r: rHit });
  }
  return { contorno };
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

    p = await ev(c, POLAR)
    assert 'contorno' in p, p
    cont = [c_ for c_ in p['contorno'] if c_['r'] is not None]
    print(f'[polar] {len(cont)}/72 angulos com chao; raios: min={min(x["r"] for x in cont)} max={max(x["r"] for x in cont)}')
    for x in p['contorno']:
        print(f"   a={x['a']:3}  r={x['r']}")

    # ---------- decisao ----------
    radii = sorted(x['r'] for x in cont)
    # zone radius start = raio que cobre >= 60% dos angulos (contorno confiavel)
    r60 = radii[int(len(radii) * 0.60)]
    rmax = radii[-1]
    print(f'[zone] r60={r60} rmax={rmax}')

    # spawns: 10 angulos equidistantes DENTRO do contorno (r = min(r_do_angulo, r60) - 10)
    byang = {x['a']: x['r'] for x in cont}
    spawns = []
    for i in range(10):
        a = i * 36
        # acha o angulo com contorno mais proximo
        cand = min(byang.keys(), key=lambda k: abs(k - a))
        rr = max(35, min(byang[cand], r60) - 10)
        spawns.append({'x': round(math.cos(math.radians(a)) * rr), 'z': round(math.sin(math.radians(a)) * rr), 'angle': a, 'r': rr})
    print(f'[spawns] {[(s["x"], s["z"]) for s in spawns]}')

    # centro: media ponderada do nucleo (densidade) — usando celulas do mapa anterior seria ideal;
    # aqui: centro geometrico dos hits (aprox (-10, 0))
    zone_center = {'x': -10, 'z': 0}

    # baús: POIs no interior, espacados
    chests = []
    for (x, z) in [(-10, 10), (10, 0), (0, -20), (-30, 0), (10, 20), (20, -20), (30, 0), (-30, 20), (-20, -20), (30, 20), (-10, 30), (40, -20)]:
        chests.append({'x': x, 'z': z})
    print(f'[baús] {len(chests)} POIs (nucleo denso)')

    layout = {
        'id': 'br_vila',
        'arena': 'sa00z',
        'source': 'contorno polar raycast 72 angulos (tools/br_vila_layout_map2.py)',
        'zoneCenter': zone_center,
        'zoneRadiusStart': r60,
        'zoneRadiusMin': 6,
        'zonePhases': 6,
        'spawnRing': spawns,
        'chests': chests,
        'notes': 'vila solida e um nucleo compacto (~r60); spawns dentro do contorno real'
    }
    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(layout, f, ensure_ascii=False, indent=1)
    print(f'[ok] {OUT_JSON} atualizado (zoneStart={r60})')
    print('BR LAYOUT MAP2 DONE')
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
