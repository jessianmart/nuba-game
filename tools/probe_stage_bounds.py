"""Mede o bounding box REAL do cenario em unidades de jogo (pos-load, pos-scale)
para sd00a e sa00z — resolve a questao da escala efetiva pro layout do BR.
Run: python tools/probe_stage_bounds.py   (cwd = repo root)
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
PROFILE = tempfile.mkdtemp(prefix='nuba_bnd_')
proc = subprocess.Popen([
    find_edge_path(), '--headless=new', f'--remote-debugging-port={PORT}', '--disable-gpu',
    '--window-size=1280,720', '--inprivate', f'--user-data-dir={PROFILE}',
    'http://localhost:8080/index.html'
])
time.sleep(3)

MEASURE = """(() => {
  const u0 = window.units && window.units[0];
  if (!u0 || !u0.mesh) return { err: 'sem units' };
  let node = u0.mesh;
  while (node.parent) node = node.parent;          // raiz = scene
  let stage = null;
  node.traverse(o => {
    if (stage || !o.children) return;
    if (o.children.some(ch => ch.userData && ch.userData.texture)) stage = o;
  });
  if (!stage) return { err: 'sem stage group' };
  const box = new THREE.Box3().setFromObject(stage);
  const sz = box.getSize(new THREE.Vector3());
  const ct = box.getCenter(new THREE.Vector3());
  return {
    scale: +stage.scale.x.toFixed(4),
    meshes: stage.children.length,
    size: { x: +sz.x.toFixed(2), y: +sz.y.toFixed(2), z: +sz.z.toFixed(2) },
    center: { x: +ct.x.toFixed(2), y: +ct.y.toFixed(2), z: +ct.z.toFixed(2) },
    arenaRadius: (typeof ARENA !== 'undefined' && ARENA.radius) || null,
    playerPos: { x: +u0.x.toFixed(2), z: +u0.z.toFixed(2) }
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

    for arena_id in ['sd00a', 'sa00z']:
        await ev(c, "(async () => { window.setLobbyPage('arenas'); const card = document.querySelector(`.arena-card[data-arena=\"" + arena_id + "\"]`); card.click(); await new Promise(r => setTimeout(r, 2500)); return 'ok'; })()", await_promise=True)
        await ev(c, "(async () => { try { await window.start5v5Match(); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        n = -1
        for _ in range(60):
            n = await ev(c, 'window.units ? window.units.length : -1')
            if n == 10:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.5)
        m = await ev(c, MEASURE)
        print(f'[{arena_id}] ' + json.dumps(m))
        await ev(c, "(async () => { if (typeof endMatch === 'function') { endMatch(); } return 'ok'; })()")
        await asyncio.sleep(0.8)
    print('BOUNDS PROBE DONE')
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
