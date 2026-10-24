# -*- coding: utf-8 -*-
"""W-PROG probe: camada de progressao real (XP/nivel/RYO/missoes diarias).
Valida:
  1. perfil limpo -> 3 missoes diarias do pool W-PROG (deterministicas por data)
  2. partida real (dm_3v3, 2 abates) -> XP/RYO/counters/missoes persistem
  3. UI renderizada: profile-level, lobby-ryo, profile-ryo, painel de missoes
  4. virada de dia -> missoes regeneradas, contadores/progressos zerados
API real do jogo: window.units, window.dealDamage, window.startMatch, window.endMatch.
"""
import asyncio, base64, json, os, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')
FAILS = []


def ok(cond, label):
    print(('  OK   ' if cond else '  FAIL ') + label)
    if not cond:
        FAILS.append(label)


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
    profile = tempfile.mkdtemp(prefix='nuba_wprog_')
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
            if await ev(c, 'typeof window.progDailyRefresh') == 'function':
                break
            await asyncio.sleep(0.5)

        # 1. perfil limpo + missoes do dia
        await ev(c, """(() => { localStorage.setItem('nuba.profile.v1', JSON.stringify({
              matches: 0, wins: 0, losses: 0, kills: 0, deaths: 0, assists: 0, history: [], arenas: [],
              settings: { sound: true, music: true }, xp: 0, coins: 0, heroUse: {} })); return true; })()""")
        daily = await ev(c, """(() => { const d = window.progDailyRefresh();
              return { ids: d.daily.missions.map(m => m.id), date: d.daily.date,
                       n: d.daily.missions.length, zero: d.daily.counters.matches }; })()""")
        print('== missoes do dia ==', daily['date'], daily['ids'])
        ok(daily['n'] == 3, '3 missoes diarias geradas')
        ok(all(i in ('play3', 'win2', 'kill6', 'ult3', 'hero2') for i in daily['ids']), 'ids vem do pool W-PROG')
        ok(daily['zero'] == 0, 'contadores zerados no perfil novo')
        again = await ev(c, "(() => window.progDailyRefresh().daily.missions.map(m => m.id).join(','))()")
        ok(again == ','.join(daily['ids']), 'determinismo: mesmo dia gera as mesmas missoes')

        # 2. partida real (dm_3v3) com 2 abates
        await ev(c, "(async () => { await window.startMatch('dm_3v3'); })()", await_promise=True)
        for _ in range(60):
            if await ev(c, 'window.units ? window.units.length : -1') == 6:
                break
            await asyncio.sleep(0.5)
        await asyncio.sleep(1.5)
        res = await ev(c, """(() => {
              const p = window.units.find(u => u.isPlayer);
              const foes = window.units.filter(u => u.team === 'red' && u.deadTimer <= 0).slice(0, 2);
              for (const e of foes) { e.hp = 5; e.x = p.x + 2; e.z = p.z; window.dealDamage(p, e, 9999, 'Rasengan!'); }
              const kills = p.kills || 0;
              window.endMatch('FIM DE PARTida');
              return { kills, foes: foes.length };
            })()""")
        print('== abates creditados ==', res['kills'], 'de', res['foes'], 'inimigos')
        ok(res['kills'] == 2, '2 abates creditados ao player')
        await asyncio.sleep(2.5)
        prof = await ev(c, """(() => {
              const d = JSON.parse(localStorage.getItem('nuba.profile.v1'));
              return { matches: d.matches, wins: d.wins, xp: d.xp, coins: d.coins,
                       kills: d.daily.counters.kills, ults: d.daily.counters.ults,
                       done: d.daily.missions.filter(m => m.done).length,
                       prog: d.daily.missions.filter(m => m.progress > 0).length,
                       level: document.getElementById('profile-level').textContent,
                       ryoHdr: document.getElementById('lobby-ryo').textContent,
                       ryoProf: document.getElementById('profile-ryo').textContent,
                       missionHtml: document.getElementById('profile-missions').children.length };
            })()""")
        print('== apos partida ==', {k: prof[k] for k in ('matches', 'wins', 'xp', 'coins', 'kills', 'ults', 'level', 'ryoHdr', 'ryoProf')})
        ok(prof['matches'] == 1 and prof['wins'] == 1, 'partida e vitoria contabilizadas no perfil')
        ok(prof['kills'] == 2, 'abates contabilizados no counter da missao (2)')
        ok(prof['ults'] == 0, 'ougi zerado sem cast de R neste probe')
        ok(prof['xp'] == 190, f"XP = 100 base + 60 vitoria + 30 abates = 190 (nenhuma missao fecha na 1a partida) -> {prof['xp']}")
        ok(prof['coins'] == 39, f"RYO = 25 base + 10 vitoria + 4 abates = 39 -> {prof['coins']}")
        ok(prof['done'] == 0, 'nenhuma missao concluida na 1a partida (goals 2-3)')
        ok(prof['prog'] >= 1, 'pelo menos 1 missao progrediu')
        ok(prof['level'] == '1', f"nivel 1 com 190 XP (precisa de 800) -> {prof['level']}")
        ok(prof['ryoHdr'] == '39', 'header do lobby mostra a carteira')
        ok(prof['ryoProf'] == '39', 'painel do perfil mostra a carteira')
        ok(prof['missionHtml'] == 3, 'painel de missoes renderiza 3 itens')

        # 3. screenshot do painel (reload limpo, perfil preservado)
        await ev(c, "location.href = 'http://localhost:8080/index.html'")
        await asyncio.sleep(4)
        for _ in range(40):
            if await ev(c, 'typeof window.progDailyRefresh') == 'function':
                break
            await asyncio.sleep(0.5)
        await ev(c, """(() => { const el = document.querySelector('[data-page="perfil"], [data-nav="perfil"]'); if (el) el.click();
              return !!el; })()""")
        await asyncio.sleep(1.0)
        data = await c.send('Page.captureScreenshot', {'format': 'png'})
        fn = os.path.join(SHOTS, 'wprog_painel.png')
        open(fn, 'wb').write(base64.b64decode(data['data']))
        print(f'shot={fn}')

        # 4. virada de dia
        dd = await ev(c, """(() => {
              const d = window.progDailyRefresh();
              d.daily.date = '2000-01-01';
              localStorage.setItem('nuba.profile.v1', JSON.stringify(d)); // persiste a virada simulada
              const after = window.progDailyRefresh();
              const again = window.progDailyRefresh();
              return { date: after.daily.date,
                       zero: after.daily.counters.matches === 0 && after.daily.counters.kills === 0,
                       progZero: after.daily.missions.every(m => m.progress === 0),
                       stable: again.daily.missions.map(m => m.id).join(',') === after.daily.missions.map(m => m.id).join(',') };
            })()""")
        ok(dd['date'] != '2000-01-01', 'data voltou para hoje apos refresh com dia velho')
        ok(dd['zero'] and dd['progZero'], 'contadores e progressos zerados no novo dia')
        ok(dd['stable'], 'refresh idempotente dentro do mesmo dia')
    finally:
        proc.kill()

    print('')
    if FAILS:
        print(f'WPROG PROBE FALHOU: {len(FAILS)} problema(s)')
        for f in FAILS:
            print('  -', f)
        return 1
    print('WPROG PROBE PASSOU — XP/nivel/RYO/missoes diarias OK')
    return 0


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
