"""World positions REAIS (getWorldPosition) dos marcos da vila vs player —
resolve a escala efetiva e entrega a base numerica do layout BR.
Run: python tools/probe_vila_worldpos.py   (cwd = repo root)
"""
import asyncio
import base64
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

OUT = os.path.join(os.environ.get('TMPDIR', tempfile.gettempdir()), 'nuba_vila_worldpos.png')


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
PROFILE = tempfile.mkdtemp(prefix='nuba_wp_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1600,900', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

MEASURE = """(() => {
  const u0 = window.units.find(u => u.isPlayer) || window.units[0];
  let node = u0.mesh;
  while (node.parent) node = node.parent;
  let stage = null;
  node.traverse(o => {
    if (stage || !o.children) return;
    if (o.children.some(ch => ch.userData && ch.userData.texture)) stage = o;
  });
  if (!stage) return { err: 'sem stage' };
  // escala EFETIVA da cadeia inteira (pai pode reescalar)
  const ws = stage.getWorldScale(new THREE.Vector3());
  // vertice REAL de um mesh (posicoes sao baked) -> localToWorld
  const probe = (namePart) => {
    let mesh = null;
    stage.traverse(o => { if (!mesh && ((o.userData && o.userData.name) || '').includes(namePart)) mesh = o; });
    if (!mesh) return null;
    const p = mesh.geometry.attributes.position;
    const v = new THREE.Vector3(p.array[0], p.array[1], p.array[2]);
    mesh.localToWorld(v);
    return { name: mesh.userData.name, world: { x: +v.x.toFixed(2), y: +v.y.toFixed(2), z: +v.z.toFixed(2) }, raw: { x: +p.array[0].toFixed(1), y: +p.array[1].toFixed(1), z: +p.array[2].toFixed(1) } };
  };
  return {
    stageLocalScale: +stage.scale.x.toFixed(4),
    worldScale: { x: +ws.x.toFixed(4), y: +ws.y.toFixed(4), z: +ws.z.toFixed(4) },
    hkgVertex: probe('hkg'),
    riverVertex: probe('river'),
    kiVertex: probe('ki'),
    rockVertex: probe('rock'),
    player: { x: +u0.x.toFixed(1), z: +u0.z.toFixed(1) },
    arenaRadius: (typeof ARENA !== 'undefined' && ARENA.radius) || null
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
    await asyncio.sleep(3)

    m = await ev(c, MEASURE)
    print('[vila worldpos] ' + json.dumps(m, ensure_ascii=False))

    shot = await c.send('Page.captureScreenshot', {'format': 'png'})
    with open(OUT, 'wb') as f:
        f.write(base64.b64decode(shot['data']))
    print(f'[shot] {OUT} ({os.path.getsize(OUT)//1024} KB) — errors: {len(list(c.console_errors))}')
    print('WORLDPOS DONE')
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
