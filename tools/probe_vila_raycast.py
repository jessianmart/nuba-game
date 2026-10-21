"""Raycast vertical na vila: onde ha chao/estrutura no clamp de jogo (±140)?
Amostra grade + posicoes do player — evidencia numerica pro layout do BR.
Run: python tools/probe_vila_raycast.py   (cwd = repo root)
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
PROFILE = tempfile.mkdtemp(prefix='nuba_rc_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

RAY = """(() => {
  const u0 = window.units.find(u => u.isPlayer) || window.units[0];
  let node = u0.mesh;
  while (node.parent) node = node.parent;
  let stage = null;
  node.traverse(o => {
    if (stage || !o.children) return;
    if (o.children.some(ch => ch.userData && ch.userData.texture)) stage = o;
  });
  if (!stage) return { err: 'sem stage' };
  const rc = new THREE.Raycaster();
  const hitAt = (x, z) => {
    rc.set(new THREE.Vector3(x, 400, z), new THREE.Vector3(0, -1, 0));
    rc.far = 800;
    const hits = rc.intersectObject(stage, true);
    if (!hits.length) return null;
    const h = hits[0];
    return { d: +h.distance.toFixed(1), y: +h.point.y.toFixed(2), mesh: (h.object.userData && h.object.userData.name) || h.object.type };
  };
  const pts = {};
  const grid = [-130, -95, -60, -30, 0, 30, 60, 95, 130];
  for (const x of grid) for (const z of grid) {
    const h = hitAt(x, z);
    if (h) pts[`${x},${z}`] = h;
  }
  return {
    player: { x: +u0.x.toFixed(1), z: +u0.z.toFixed(1), under: hitAt(+u0.x.toFixed(1), +u0.z.toFixed(1)) },
    center: hitAt(0, 0),
    hits: pts,
    hitCount: Object.keys(pts).length,
    gridN: grid.length * grid.length
  };
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

    r = await ev(c, RAY)
    print('[raycast vila] ' + json.dumps(r, ensure_ascii=False))
    print('RAYCAST DONE')
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
