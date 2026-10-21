"""measure_perf.py — régua de performance do NUBA (PV-A de docs/PIVOT_MOBILE.md).

Mede, em Edge headless via CDP:
  * FPS (avg/min/p5/max) durante uma partida real
  * draw calls / triângulos / geometrias / texturas / programs
  * payload de rede (Resource Timing API) em MB
  * pixel ratio, viewport, draw buffer, unidades/VFX/projéteis ativos
  * console errors durante a janela

Uso:
  python tools\measure_perf.py                 # lobby + partida 3v3, 45s de amostra
  python tools\measure_perf.py --mode dm_3v3   # força o modo
  python tools\measure_perf.py --mode dm_legacy_5v5
  python tools\measure_perf.py --seconds 90 --out perf_3v3.json
  python tools\measure_perf.py --no-match      # só lobby

Saída: JSON em stdout + arquivo (--out) + captura de screenshot.
"""

import argparse
import asyncio
import base64
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR = os.path.join(ROOT, 'perf_reports')


async def _run(port, args):
    tabs = None
    for _ in range(24):
        try:
            tabs = json.loads(urllib.request.urlopen(f'http://127.0.0.1:{port}/json', timeout=5).read())
            if tabs:
                break
        except Exception:
            await asyncio.sleep(0.5)
    if not tabs:
        raise RuntimeError('Edge CDP nao respondeu /json')
    tab = next((t for t in tabs if 'localhost:' in t.get('url', '')), None)
    if not tab:
        raise RuntimeError(f'aba do jogo nao encontrada: {[t.get("url") for t in tabs]}')

    mid = 0
    async with websockets.connect(tab['webSocketDebuggerUrl'], max_size=40_000_000) as ws:
        async def call(method, params=None):
            nonlocal mid
            mid += 1
            await ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
            while True:
                d = json.loads(await asyncio.wait_for(ws.recv(), timeout=90))
                if d.get('id') == mid:
                    return d.get('result', {})

        async def js(expr, await_promise=False):
            r = await call('Runtime.evaluate', {
                'expression': expr, 'returnByValue': True, 'awaitPromise': await_promise})
            if 'exceptionDetails' in r:
                return {'__error__': r['exceptionDetails'].get('text')}
            return r.get('result', {}).get('value')

        await call('Runtime.enable')
        await call('Page.enable')
        await call('Log.enable')

        console_errors = []
        while True:
            try:
                d = json.loads(await asyncio.wait_for(ws.recv(), timeout=1.0))
            except asyncio.TimeoutError:
                break
            if d.get('method') == 'Runtime.consoleAPICalled' and d['params'].get('type') == 'error':
                console_errors.append(d['params'].get('args', [{}])[0].get('value', 'console.error'))

        # espera o boot
        for _ in range(80):
            if await js('Boolean(window.__PERF && window.rosterMeta && window.lobbyHeroMesh)'):
                break
            await asyncio.sleep(0.5)

        report = {'mode': args.mode, 'window': [args.width, args.height], 'startedAt': time.time()}

        # ---- payload de rede (boot) ----
        report['boot'] = await js("""(() => {
          const res = performance.getEntriesByType('resource');
          const byType = {};
          for (const r of res) {
            const t = r.transferSize || r.encodedBodySize || 0;
            const key = (r.name.split('/assets/')[1] || r.name).split('?')[0].split('/').slice(0, 2).join('/');
            byType[key] = (byType[key] || 0) + t;
          }
          const top = Object.entries(byType).sort((a, b) => b[1] - a[1]).slice(0, 12)
            .map(([k, v]) => ({ path: k, mb: +(v / 1048576).toFixed(3) }));
          const total = res.reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0);
          return { totalMb: +(total / 1048576).toFixed(2), entries: res.length, top };
        })()""")

        # ---- lobby ----
        report['lobby'] = await js('window.__PERF.snapshot()')

        # ---- partida ----
        if not args.no_match:
            await js("window.__PERF.reset()")
            start = await js("""(async () => {
              if (window.MATCH_CONFIGS && window.startMatch) {
                await window.startMatch('%s');
              } else {
                await window.start5v5Match();
              }
              for (let i = 0; i < 100; i++) {
                if (window.units && window.units.length) return { units: window.units.length, cfg: (window.activeMatchCfg || {}).label || null };
                await new Promise(r => setTimeout(r, 100));
              }
              return { units: (window.units || []).length, cfg: null };
            })()""" % (args.mode or 'dm_3v3'), True)

            # aquece (compila shaders, popula caches) antes de medir
            await asyncio.sleep(args.warmup)
            await js('window.__PERF.reset()')
            samples = []
            deadline = time.time() + args.seconds
            while time.time() < deadline:
                s = await js('window.__PERF.snapshot()')
                if s:
                    samples.append(s)
                await asyncio.sleep(args.interval)
            report['match'] = {
                'start': start,
                'samples': len(samples),
                'drawCalls': _agg(samples, 'drawCalls'),
                'triangles': _agg(samples, 'triangles'),
                'textures': _agg(samples, 'textures'),
                'geometries': _agg(samples, 'geometries'),
                'programs': _agg(samples, 'programs'),
                'fps': _agg(samples, 'fps'),
                'cpuFrameMs': _agg_nested(samples, 'frameMs', 'last'),
                'worstFrameMs': _agg_nested(samples, 'frameMs', 'worst'),
                'vfxMax': max([s.get('vfx', 0) for s in samples] or [0]),
                'projectilesMax': max([s.get('projectiles', 0) for s in samples] or [0]),
                'units': max([s.get('units', 0) for s in samples] or [0]),
                'pixelRatio': samples[-1].get('pixelRatio') if samples else None,
                'drawBuffer': samples[-1].get('drawBuffer') if samples else None,
                'viewport': samples[-1].get('viewport') if samples else None,
            }
            shot = await call('Page.captureScreenshot', {'format': 'png'})
            os.makedirs(OUT_DIR, exist_ok=True)
            shot_path = os.path.join(OUT_DIR, f'perf_{args.mode or "match"}.png')
            with open(shot_path, 'wb') as f:
                f.write(base64.b64decode(shot['data']))
            report['screenshot'] = shot_path

            # payload acumulado ate aqui (boot + partida) — o numero real do mobile
            report['payloadAfterMatch'] = await js("""(() => {
              const res = performance.getEntriesByType('resource');
              const by = {};
              for (const r of res) {
                const name = r.name.split('/').pop().split('?')[0];
                const ext = (name.split('.').pop() || '?').toLowerCase();
                by[ext] = (by[ext] || 0) + (r.transferSize || r.encodedBodySize || 0);
              }
              const total = res.reduce((s, r) => s + (r.transferSize || r.encodedBodySize || 0), 0);
              const out = { totalMb: +(total / 1048576).toFixed(2), requests: res.length, byExt: {} };
              for (const k of Object.keys(by).sort((a,b)=>by[b]-by[a])) out.byExt[k] = +(by[k] / 1048576).toFixed(2);
              return out;
            })()""")

        report['consoleErrors'] = console_errors
        report['endedAt'] = time.time()
        return report


def _agg(samples, key):
    vals = []
    for s in samples:
        v = s.get(key)
        if isinstance(v, dict):
            for vv in v.values():
                if isinstance(vv, (int, float)):
                    vals.append(vv)
        elif isinstance(v, (int, float)):
            vals.append(v)
    if not vals:
        return None
    vals_sorted = sorted(vals)
    return {
        'avg': round(sum(vals) / len(vals), 2),
        'min': vals_sorted[0],
        'max': vals_sorted[-1],
        'p5': vals_sorted[max(0, int(len(vals_sorted) * 0.05))],
        'n': len(vals),
    }


def _agg_nested(samples, key, sub):
    vals = []
    for s in samples:
        v = s.get(key)
        if isinstance(v, dict) and isinstance(v.get(sub), (int, float)):
            vals.append(v[sub])
    if not vals:
        return None
    vals_sorted = sorted(vals)
    return {
        'avg': round(sum(vals) / len(vals), 2),
        'min': vals_sorted[0],
        'max': vals_sorted[-1],
        'p95': vals_sorted[min(len(vals_sorted) - 1, int(len(vals_sorted) * 0.95))],
        'n': len(vals),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mode', default='dm_3v3', help='MATCH_CONFIGS id (dm_3v3 | dm_legacy_5v5 | br_vila)')
    ap.add_argument('--seconds', type=int, default=45, help='janela de amostragem da partida')
    ap.add_argument('--interval', type=float, default=1.0, help='intervalo entre amostras')
    ap.add_argument('--warmup', type=float, default=6.0, help='aquecimento antes de medir')
    ap.add_argument('--width', type=int, default=1280)
    ap.add_argument('--height', type=int, default=720)
    ap.add_argument('--out', default=None, help='caminho do JSON de saida')
    ap.add_argument('--no-match', action='store_true', help='mede so o lobby')
    ap.add_argument('--url', default='http://localhost:8080', help='origem do jogo (ex.: :8090 para o server com gzip)')
    args = ap.parse_args()

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]
    prof = tempfile.mkdtemp()
    proc = subprocess.Popen([
        EDGE_PATH, '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        f'--window-size={args.width},{args.height}', '--inprivate', f'--user-data-dir={prof}',
        args.url + '/index.html'])
    time.sleep(3)
    try:
        report = asyncio.run(_run(port, args))
    finally:
        proc.kill()
        import shutil
        shutil.rmtree(prof, ignore_errors=True)

    print(json.dumps(report, indent=2, ensure_ascii=False))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print('JSON salvo em', args.out, file=sys.stderr)


if __name__ == '__main__':
    main()
