# -*- coding: utf-8 -*-
"""W-REAL: debug do rasengan novo — bbox do grupo, posicao vs mao, textura viva."""
import asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_rasdbg_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(3)
    try:
        tabs = None
        for _ in range(20):
            try:
                with urllib.request.urlopen(f'http://127.0.0.1:{port}/json') as r:
                    tabs = json.load(r)
                break
            except Exception:
                time.sleep(0.5)
        ws = next(t['webSocketDebuggerUrl'] for t in tabs if t['type'] == 'page')
        c = CDPClient(ws)
        await c.connect()
        for _ in range(40):
            if await ev(c, 'typeof window.startMatch') == 'function':
                break
            await asyncio.sleep(0.5)
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        await asyncio.sleep(5)
        r = await ev(c, """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          window.units.forEach(u => { if (!u.isPlayer) { u.cds = { atk: 9999, q: 9999, w: 9999, e: 9999, r: 9999 }; u.chakra = 0; } });
          p.hitstun = 0; p.animTimer = 0; p.state = 'idle'; p.chakra = 100;
          p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };
          const kb = p.mesh.parent.children.length;
          window.executeSkill(p, 'q');
          return kb;
        })()
        """)
        await asyncio.sleep(0.35)
        info = await ev(c, """
        (() => {
          const p = window.units.find(u => u.isPlayer);
          const out = { groups: [] };
          p.mesh.parent.children.forEach(g => {
            if (!g.isGroup || !g.children.length) return;
            const box = new THREE.Box3().setFromObject(g);
            const size = new THREE.Vector3();
            box.getSize(size);
            if (size.x > 2.2 && size.x < 12) {
              const mesh = g.children[0];
              out.groups.push({
                size: [size.x, size.y, size.z].map(v => +v.toFixed(2)),
                pos: [g.position.x, g.position.y, g.position.z].map(v => +v.toFixed(2)),
                meshes: g.children.length,
                matColor: mesh && mesh.material ? '#' + mesh.material.color.getHexString() : '?',
                matOpacity: mesh && mesh.material ? mesh.material.opacity : '?',
                tex: mesh && mesh.material && mesh.material.map ? (mesh.material.map.image ? (mesh.material.map.image.width + 'x' + mesh.material.map.image.height) : 'NO-IMG') : 'no-map'
              });
            }
          });
          const hand = p.mesh.userData.bones['13'];
          const hw = new THREE.Vector3(); hand.getWorldPosition(hw);
          out.hand = [hw.x, hw.y, hw.z].map(v => +v.toFixed(2));
          return out;
        })()
        """)
        for g in info.get('groups', []):
            print(f"grupo: size={g['size']} pos={g['pos']} meshes={g['meshes']} cor={g['matColor']} opacity={g['matOpacity']} tex={g['tex']}")
        print("mao (bone13 world):", info.get('hand'))
        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print('console errors:', len(errs))
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
