# -*- coding: utf-8 -*-
"""
p2_cap_C.py - Validacao do patch P2 (kits unicos) dos herois 1hnt / 1nej / 1jry no NUBA.

NAO edita nenhum arquivo do repo. Sobe UM Edge headless proprio (porta livre,
profile temp), conecta via CDP (Runtime.evaluate + Page.captureScreenshot) e,
para cada heroi: start5v5Match -> poll matchActive/units -> probe atomico em
expressao UNICA (stats + kit q/w/e/r + DR probe com dealDamage 100) ->
screenshot. No finally mata APENAS o proprio Edge (taskkill /PID /T) e apaga
o profile temp.

Entregas:
  - C:\\Users\\jessi\\Documents\\antigravity\\fearless-davinci\\p2_results_C.json
  - C:\\Users\\jessi\\Documents\\antigravity\\fearless-davinci\\nuba_sketches\\shots\\p2_<hero>.png (x3)

Tolerancias: speed abs < 0.02; dmg/cost exatos; cd abs < 0.001; drLoss/reg/maxHp exatos.
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
import traceback
import urllib.request

import websockets

EDGE = r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
PAGE_URL = 'http://localhost:8080/index.html'
SHOTS_DIR = r'C:\Users\jessi\Documents\antigravity\fearless-davinci\nuba_sketches\shots'
OUT_JSON = r'C:\Users\jessi\Documents\antigravity\fearless-davinci\p2_results_C.json'

HEROES = ['1hnt', '1nej', '1jry']
BOT_BASE = 19.5  # bots: 19.5 * spd (player e sempre 1nrt -> 21.5 * spd)

# Esperados (fonte: contexto do patch P2 + conferidos no codigo public/game.js)
EXP = {
    '1hnt': dict(maxHp=920, spd=1.06, dr=1.05, reg=1.05,
                 q=dict(cd=5.0, cost=25, dmg=140),
                 w=dict(cd=8.0, cost=20, dmg=165),
                 e=dict(cd=8.0, cost=15, dmg=0),
                 r=dict(cd=22.0, cost=50, dmg=440)),
    '1nej': dict(maxHp=940, spd=1.05, dr=1.02, reg=1.05,
                 q=dict(cd=5.2, cost=25, dmg=135),
                 w=dict(cd=6.0, cost=20, dmg=150),
                 e=dict(cd=8.0, cost=15, dmg=0),
                 r=dict(cd=22.0, cost=50, dmg=450)),
    '1jry': dict(maxHp=1150, spd=0.94, dr=0.90, reg=1.10,
                 q=dict(cd=6.5, cost=25, dmg=210),
                 w=dict(cd=9.0, cost=25, dmg=150),
                 e=dict(cd=9.0, cost=15, dmg=0),
                 r=dict(cd=23.0, cost=50, dmg=490)),
}

# ---------------------------------------------------------------------------
# CDP minimo
# ---------------------------------------------------------------------------
def free_port():
    s = socket.socket()
    s.bind(('127.0.0.1', 0))
    p = s.getsockname()[1]
    s.close()
    return p


class CDP:
    def __init__(self, ws):
        self.ws = ws
        self._id = 0

    async def call(self, method, params=None, timeout=120):
        self._id += 1
        mid = self._id
        await self.ws.send(json.dumps({'id': mid, 'method': method, 'params': params or {}}))
        loop = asyncio.get_event_loop()
        deadline = loop.time() + timeout
        while True:
            remaining = deadline - loop.time()
            if remaining <= 0:
                raise TimeoutError('CDP %s: timeout %ss' % (method, timeout))
            raw = await asyncio.wait_for(self.ws.recv(), timeout=remaining)
            msg = json.loads(raw)
            if msg.get('id') == mid:
                if 'error' in msg:
                    raise RuntimeError('CDP %s: %s' % (method, msg['error']))
                return msg.get('result', {})
            # eventos (Page.*, Runtime.*, etc.) sao ignorados

    async def ev(self, expression, await_promise=False, timeout=180):
        r = await self.call('Runtime.evaluate',
                            {'expression': expression,
                             'returnByValue': True,
                             'awaitPromise': await_promise},
                            timeout=timeout)
        if 'exceptionDetails' in r:
            raise RuntimeError('JS error: %s' % json.dumps(r['exceptionDetails'])[:800])
        return r.get('result', {}).get('value')


async def wait_ready(cdp, total=120):
    t0 = time.time()
    while time.time() - t0 < total:
        v = await cdp.ev("typeof window.start5v5Match === 'function'", timeout=30)
        if v is True:
            return
        await asyncio.sleep(1.0)
    raise RuntimeError('readiness timeout: start5v5Match nunca virou function')


async def wait_match(cdp, total=90):
    t0 = time.time()
    while time.time() - t0 < total:
        v = await cdp.ev(
            "(window.matchActive === true && window.units && window.units.length >= 10)",
            timeout=30)
        if v is True:
            return
        await asyncio.sleep(0.5)
    raise RuntimeError('timeout: matchActive/units (>=10) nunca prontos')


def probe_js(hero):
    # Expressao UNICA, sincrona -> atomica (nenhum tick de rAF entre leituras)
    return f"""(() => {{
  const u = window.units.find(x => x.heroId === '{hero}');
  if (!u) return {{ error: 'unit-not-found', have: window.units.map(x => x.heroId) }};
  const pl = window.units.find(x => x.isPlayer);
  const st = window.HERO_STATS['{hero}'];
  const out = {{
    hero: '{hero}',
    maxHp: u.maxHp,
    speed: u.speed,
    reg: st.reg,
    kitQ: {{ dmg: u.kit.q.dmg, cd: u.kit.q.cd, cost: u.kit.q.cost }},
    kitW: {{ dmg: u.kit.w.dmg, cd: u.kit.w.cd, cost: u.kit.w.cost }},
    kitE: {{ dmg: u.kit.e.dmg, cd: u.kit.e.cd, cost: u.kit.e.cost }},
    kitR: {{ dmg: u.kit.r.dmg, cd: u.kit.r.cd, cost: u.kit.r.cost }},
    playerLevel: pl ? pl.level : null,
    playerAwakened: pl ? (pl.awakenedTimer > 0) : null,
    targetWasDead: u.deadTimer > 0
  }};
  u.hp = u.maxHp;
  window.dealDamage(pl, u, 100, 'probe');
  out.drLoss = u.maxHp - u.hp;
  return out;
}})()"""


def check(hero, got):
    """Retorna lista de falhas (vazia = ok)."""
    e = EXP[hero]
    fails = []
    if got.get('maxHp') != e['maxHp']:
        fails.append('maxHp %r != %r' % (got.get('maxHp'), e['maxHp']))
    exp_speed = BOT_BASE * e['spd']
    if got.get('speed') is None or abs(got['speed'] - exp_speed) >= 0.02:
        fails.append('speed %r != %r' % (got.get('speed'), exp_speed))
    exp_drloss = round(100 * e['dr'])
    if got.get('drLoss') != exp_drloss:
        fails.append('drLoss %r != %r' % (got.get('drLoss'), exp_drloss))
    if got.get('reg') is None or abs(got['reg'] - e['reg']) > 1e-9:
        fails.append('reg %r != %r' % (got.get('reg'), e['reg']))
    for slot in ('q', 'w', 'e', 'r'):
        k = (got.get('kit' + slot.upper()) or {})
        ke = e[slot]
        if k.get('dmg') != ke['dmg']:
            fails.append('kit.%s.dmg %r != %r' % (slot, k.get('dmg'), ke['dmg']))
        if k.get('cost') != ke['cost']:
            fails.append('kit.%s.cost %r != %r' % (slot, k.get('cost'), ke['cost']))
        if k.get('cd') is None or abs(k['cd'] - ke['cd']) > 0.001:
            fails.append('kit.%s.cd %r != %r' % (slot, k.get('cd'), ke['cd']))
    # validade do probe de DR
    if got.get('playerLevel') != 1:
        fails.append('playerLevel %r != 1 (probe de DR invalido)' % got.get('playerLevel'))
    if got.get('playerAwakened'):
        fails.append('player awakened no probe (dmgRaw seria *1.35)')
    if got.get('targetWasDead'):
        fails.append('alvo estava morto (dealDamage retorna cedo)')
    return fails


def png_stats(path):
    """(w, h, cores_unicas_em_downsample, bytes) - frame real ~1400-2100 cores; preto ~1."""
    size = os.path.getsize(path)
    try:
        from PIL import Image
        im = Image.open(path).convert('RGB')
        w, h = im.size
        px = im.load()
        colors = set()
        step = 8
        for y in range(0, h, step):
            for x in range(0, w, step):
                colors.add(px[x, y])
        return w, h, len(colors), size
    except Exception as ex:
        return None, None, -1, size


def kill_my_edge(proc):
    """Mata SOMENTE a arvore do processo Edge que EU subi."""
    try:
        subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                       capture_output=True, timeout=15)
    except Exception:
        try:
            proc.terminate()
        except Exception:
            pass
    try:
        proc.wait(timeout=10)
    except Exception:
        pass


def main():
    if not os.path.exists(EDGE):
        print('FATAL: Edge nao encontrado em %s' % EDGE)
        sys.exit(2)
    port = free_port()
    temp = tempfile.mkdtemp(prefix='p2capC_edge_')
    print('CDP port=%d temp=%s' % (port, temp), flush=True)
    proc = subprocess.Popen(
        [EDGE, '--headless=new', '--remote-debugging-port=%d' % port,
         '--disable-gpu', '--window-size=1280,720', '--inprivate',
         '--user-data-dir=%s' % temp, 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    results = []
    try:
        # /json -> webSocketDebuggerUrl
        ws_url = None
        for _ in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:%d/json' % port, timeout=5) as r:
                    targets = json.load(r)
                page = next((t for t in targets if t.get('type') == 'page'), None)
                if page and page.get('webSocketDebuggerUrl'):
                    ws_url = page['webSocketDebuggerUrl']
                    break
            except Exception:
                pass
            time.sleep(1.0)
        if not ws_url:
            raise RuntimeError('nao achei target page no /json do Edge')
        print('WS: %s' % ws_url, flush=True)

        async def session():
            async with websockets.connect(ws_url, max_size=20_000_000) as w:
                cdp = CDP(w)
                await cdp.call('Page.enable')
                await cdp.call('Page.navigate', {'url': PAGE_URL})
                await wait_ready(cdp)
                print('READY: start5v5Match exposto', flush=True)

                for hero in HEROES:
                    try:
                        await cdp.ev('window.start5v5Match()', await_promise=True, timeout=300)
                        await wait_match(cdp)
                        got = await cdp.ev(probe_js(hero), timeout=60)
                        if not got or got.get('error'):
                            raise RuntimeError('probe falhou: %s' % json.dumps(got)[:300])
                        await asyncio.sleep(1.5)  # deixa renderizar alguns frames
                        shot_data = await cdp.call('Page.captureScreenshot',
                                                   {'format': 'png'}, timeout=60)
                        shot = os.path.join(SHOTS_DIR, 'p2_%s.png' % hero)
                        with open(shot, 'wb') as f:
                            f.write(base64.b64decode(shot_data['data']))
                        fails = check(hero, got)
                        w_, h_, colors, nbytes = png_stats(shot)
                        shot_ok = bool(w_) and colors >= 300 and nbytes > 20000
                        if not shot_ok:
                            fails.append('shot invalido (%sx%s, %d cores, %d bytes)'
                                         % (w_, h_, colors, nbytes))
                        rec = {
                            'hero': hero,
                            'maxHp': got['maxHp'],
                            'speed': got['speed'],
                            'speedExpected': round(BOT_BASE * EXP[hero]['spd'], 4),
                            'drLoss': got['drLoss'],
                            'drLossExpected': round(100 * EXP[hero]['dr']),
                            'reg': got['reg'],
                            'kitQ': got['kitQ'], 'kitW': got['kitW'],
                            'kitE': got['kitE'], 'kitR': got['kitR'],
                            'ok': (not fails),
                            'shot': shot,
                        }
                        if fails:
                            rec['fails'] = fails
                        results.append(rec)
                        with open(OUT_JSON, 'w', encoding='utf-8') as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
                        status = 'OK' if not fails else 'FAIL -> ' + '; '.join(fails)
                        print('%s: %s | shot %sx%s %d cores %d bytes'
                              % (hero, status, w_, h_, colors, nbytes), flush=True)
                        if fails:
                            flag[0] = False
                    except Exception as ex:
                        flag[0] = False
                        results.append({'hero': hero, 'ok': False,
                                        'error': '%s: %s' % (type(ex).__name__, ex)})
                        with open(OUT_JSON, 'w', encoding='utf-8') as f:
                            json.dump(results, f, ensure_ascii=False, indent=2)
                        print('%s: EXC %s' % (hero, ex), flush=True)
                        traceback.print_exc()

        flag = [True]
        asyncio.run(session())
        ok_all = flag[0]
    finally:
        kill_my_edge(proc)
        for _ in range(5):
            shutil.rmtree(temp, ignore_errors=True)
            if not os.path.exists(temp):
                break
            time.sleep(1.0)
        print('Edge morto (pid %s) + temp limpo' % proc.pid, flush=True)

    with open(OUT_JSON, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    all_ok = len(results) == len(HEROES) and all(r.get('ok') for r in results)
    print('RESULT: %s (%d/%d ok)' % ('PASS' if all_ok else 'FAIL',
                                     sum(1 for r in results if r.get('ok')), len(HEROES)),
          flush=True)
    print('ALL DONE' if all_ok else 'CAP FAILED', flush=True)
    sys.exit(0 if all_ok else 1)


if __name__ == '__main__':
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        print('CAP FAILED', flush=True)
        sys.exit(1)
