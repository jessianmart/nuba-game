# -*- coding: utf-8 -*-
"""P2 captura B — valida stats + kits de 1roc, 1itc, 1gar no NUBA (:8080).

Determinístico, via CDP em Edge headless. NÃO edita nada do repo.
Artefatos: p2_<hero>.png em nuba_sketches/shots + p2_results_B.json no workspace.
No finally mata SOMENTE a própria árvore Edge e remove o TEMP próprio.
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

import websockets

WORKSPACE = r'C:\Users\jessi\Documents\antigravity\fearless-davinci'
SHOTS_DIR = os.path.join(WORKSPACE, 'nuba_sketches', 'shots')
OUT_JSON = os.path.join(WORKSPACE, 'p2_results_B.json')
EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
GAME_URL = 'http://localhost:8080/index.html'

ORDER = ['1roc', '1itc', '1gar']

# Esperados do patch P2 (bot: speed = 19.5*spd; DR probe 100 => perda round(100*dr))
# kit[slot] = (cd, cost, dmg)
EXPECTED = {
    '1roc': dict(hp=900, spd=1.18, dr=1.10, reg=1.00, speed=19.5 * 1.18, drLoss=110,
                 kit={'q': (3.8, 20, 135), 'w': (5.5, 20, 180),
                      'e': (7.5, 15, 0), 'r': (20.0, 50, 470)}),
    '1itc': dict(hp=850, spd=1.02, dr=1.18, reg=0.95, speed=19.5 * 1.02, drLoss=118,
                 kit={'q': (7.0, 30, 300), 'w': (8.0, 25, 170),
                      'e': (9.0, 15, 60), 'r': (24.0, 50, 500)}),
    '1gar': dict(hp=1250, spd=0.90, dr=0.82, reg=1.00, speed=19.5 * 0.90, drLoss=82,
                 kit={'q': (7.0, 25, 190), 'w': (10.0, 25, 80),
                      'e': (9.0, 15, 0), 'r': (24.0, 50, 430)}),
}

ATTEMPTS = 3
START_TIMEOUT_S = 150


def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    port = s.getsockname()[1]
    s.close()
    return port


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self._id = 0

    async def call(self, method, **params):
        self._id += 1
        mid = self._id
        await self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params}))
        while True:
            msg = json.loads(await self.ws.recv())
            if msg.get('id') == mid:
                if 'error' in msg:
                    raise RuntimeError(f'{method}: {msg["error"]}')
                return msg.get('result', {})

    async def ev(self, expression, await_promise=False):
        res = await self.call('Runtime.evaluate', expression=expression,
                              returnByValue=True, awaitPromise=await_promise)
        if res.get('exceptionDetails'):
            raise RuntimeError('JS error: ' + json.dumps(res['exceptionDetails'])[:400])
        return res.get('result', {}).get('value')


def gather_expr(hero):
    # NUMA ÚNICA EXPRESSÃO: maxHp, speed, reg (HERO_STATS) e kit q/w/e/r {dmg, cd, cost}
    return f"""
(() => {{
  const u = window.units.find(x => x.heroId === '{hero}');
  if (!u) return null;
  const hs = window.HERO_STATS['{hero}'];
  const pick = s => {{ const k = u.kit[s]; return {{dmg: k.dmg, cd: k.cd, cost: k.cost}}; }};
  return {{
    maxHp: u.maxHp,
    speed: u.speed,
    reg: hs.reg,
    isPlayer: !!u.isPlayer,
    deadTimer: u.deadTimer,
    nUnits: window.units.length,
    kit: {{q: pick('q'), w: pick('w'), e: pick('e'), r: pick('r')}}
  }};
}})()
""".strip()


def probe_expr(hero):
    # DR probe: u.hp=u.maxHp; dealDamage(player, u, 100, 'probe'); loss = maxHp - hp
    return f"""
(() => {{
  const u = window.units.find(x => x.heroId === '{hero}');
  if (!u || u.deadTimer > 0) return null;
  u.hp = u.maxHp;
  window.dealDamage(window.units.find(x => x.isPlayer), u, 100, 'probe');
  return u.maxHp - u.hp;
}})()
""".strip()


def match_state_expr(hero):
    return f"""
(() => {{
  const u = window.units.find(x => x.heroId === '{hero}');
  return {{active: window.matchActive === true, n: window.units ? window.units.length : 0,
           present: !!u, alive: !!u && u.deadTimer === 0}};
}})()
""".strip()


async def wait_ready(cdp, timeout_s=60):
    deadline = time.time() + timeout_s
    last = None
    while time.time() < deadline:
        try:
            if await cdp.ev("typeof window.start5v5Match === 'function'"):
                return
            last = 'hook ausente'
        except Exception as e:
            last = str(e)
        await asyncio.sleep(0.5)
    raise RuntimeError(f'readiness timeout: {last}')


async def start_match(cdp, hero):
    async def _once():
        await cdp.ev('window.start5v5Match()', await_promise=True)
        deadline = time.time() + 120
        while time.time() < deadline:
            st = await cdp.ev(match_state_expr(hero))
            if st and st['active'] and st['n'] == 10 and st['present'] and st['alive']:
                return st
            await asyncio.sleep(0.4)
        raise RuntimeError(f'partida nunca ficou pronta com {hero} vivo: {st}')
    return await asyncio.wait_for(_once(), START_TIMEOUT_S)


async def check_hero(cdp, hero):
    exp = EXPECTED[hero]
    last_err = None
    for attempt in range(1, ATTEMPTS + 1):
        try:
            await start_match(cdp, hero)
            g = await cdp.ev(gather_expr(hero))
            if not g:
                raise RuntimeError('unidade não encontrada')
            loss = await cdp.ev(probe_expr(hero))
            if loss is None:
                raise RuntimeError('unidade morta no momento do probe')

            shot_path = os.path.join(SHOTS_DIR, f'p2_{hero}.png')
            res = await cdp.call('Page.captureScreenshot', format='png')
            with open(shot_path, 'wb') as f:
                f.write(base64.b64decode(res['data']))

            checks = {
                'maxHp': g['maxHp'] == exp['hp'],
                'speed(|got-exp|<0.02)': abs(g['speed'] - exp['speed']) < 0.02,
                'drLoss': loss == exp['drLoss'],
                'reg': abs(g['reg'] - exp['reg']) < 1e-9,
                'bot(nao-player)': g['isPlayer'] is False,
                '10-units': g['nUnits'] == 10,
            }
            for slot in ('q', 'w', 'e', 'r'):
                cd_e, cost_e, dmg_e = exp['kit'][slot]
                k = g['kit'][slot]
                checks[f'{slot}.dmg'] = k['dmg'] == dmg_e
                checks[f'{slot}.cd(|<=0.001|)'] = abs(k['cd'] - cd_e) <= 0.001
                checks[f'{slot}.cost'] = k['cost'] == cost_e

            record = {
                'hero': hero,
                'maxHp': g['maxHp'],
                'speed': g['speed'],
                'speedExpected': round(exp['speed'], 2),
                'drLoss': loss,
                'drLossExpected': exp['drLoss'],
                'reg': g['reg'],
                'kitQ': g['kit']['q'],
                'kitW': g['kit']['w'],
                'kitE': g['kit']['e'],
                'kitR': g['kit']['r'],
                'ok': all(checks.values()),
                'shot': shot_path,
            }
            return record, checks
        except Exception as e:
            last_err = e
            print(f'[{hero}] tentativa {attempt}/{ATTEMPTS} falhou: {e}', flush=True)
            await asyncio.sleep(1.5)
    return {'hero': hero, 'ok': False, 'error': str(last_err),
            'shot': os.path.join(SHOTS_DIR, f'p2_{hero}.png')}, {}


async def run():
    os.makedirs(SHOTS_DIR, exist_ok=True)
    port = free_port()
    temp_dir = tempfile.mkdtemp(prefix='p2_cap_B_',
                                dir=os.environ.get('TMPDIR') or None)
    args = [EDGE, '--headless=new', f'--remote-debugging-port={port}',
            '--disable-gpu', '--window-size=1280,720', '--inprivate',
            f'--user-data-dir={temp_dir}', 'about:blank']
    proc = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        time.sleep(3)
        ws_url = None
        for host in ('127.0.0.1', 'localhost'):
            try:
                with urllib.request.urlopen(f'http://{host}:{port}/json', timeout=5) as r:
                    targets = json.load(r)
                page = next((t for t in targets if t.get('type') == 'page'), None)
                if page:
                    ws_url = page['webSocketDebuggerUrl']
                    break
            except Exception as e:
                print(f'/json via {host}: {e}', flush=True)
        if not ws_url:
            raise RuntimeError('nenhum alvo page no DevTools')

        async with websockets.connect(ws_url, max_size=20_000_000) as ws:
            cdp = CDP(ws)
            await cdp.call('Page.enable')
            await cdp.call('Page.navigate', url=GAME_URL)
            await wait_ready(cdp)
            print('PAGINA PRONTA (start5v5Match exposto)', flush=True)

            results = []
            for hero in ORDER:
                record, checks = await check_hero(cdp, hero)
                results.append(record)
                print(json.dumps(record, ensure_ascii=False), flush=True)
                if checks:
                    failed = [k for k, v in checks.items() if not v]
                    print(f'[{hero}] checks: ' + ('ALL PASS' if not failed else 'FAIL -> ' + ', '.join(failed)), flush=True)

            with open(OUT_JSON, 'w', encoding='utf-8') as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            print('WROTE ' + OUT_JSON, flush=True)
            return results
    finally:
        try:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           capture_output=True)
        except Exception as e:
            print('taskkill falhou:', e, flush=True)
        try:
            proc.kill()
        except Exception:
            pass
        shutil.rmtree(temp_dir, ignore_errors=True)
        print('MEU Edge finalizado; TEMP removido', flush=True)


if __name__ == '__main__':
    res = asyncio.run(run())
    all_ok = len(res) == 3 and all(r.get('ok') for r in res)
    print('ALL_OK' if all_ok else 'HAS_FAILURE', flush=True)
    sys.exit(0 if all_ok else 1)
