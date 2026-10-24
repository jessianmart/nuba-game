# -*- coding: utf-8 -*-
"""W-MENU T3/T4: draft completo — titulo -> home -> openDraft(3v3) -> preview -> auto-lock
por timer -> bots pensam -> reveal -> startMatch(draft) com composicao fiel."""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def wait_js(c, cond, timeout=25, poll=0.25):
    for _ in range(int(timeout / poll)):
        if await ev(c, cond) is True:
            return True
        await asyncio.sleep(poll)
    return False


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_draft_')
    proc = subprocess.Popen([
        find_edge_path(), '--headless=new', f'--remote-debugging-port={port}', '--disable-gpu',
        '--window-size=1280,720', '--inprivate', f'--user-data-dir={profile}',
        'http://localhost:8080/index.html'
    ])
    time.sleep(3)
    fails = []
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
        if not await wait_js(c, "window.__ajustesReady === true", timeout=60):
            fails.append('boot nao completou')

        # titulo -> home
        await ev(c, "window.dismissTitle(); return true;".replace('return true', '(() => { window.dismissTitle(); return true; })()'))
        await asyncio.sleep(0.5)

        # 1. abrir draft
        await ev(c, "(async () => { await window.openDraft('dm_3v3'); return 'ok'; })()", await_promise=True)
        r = await ev(c, """
        (() => ({
          draftActive: document.getElementById('draft-screen').classList.contains('active'),
          lobbyActive: document.getElementById('lobby-screen').classList.contains('active'),
          cards: document.querySelectorAll('#draft-board .draft-card').length,
          blueSlots: document.querySelectorAll('#draft-blue-slots .draft-slot').length,
          redSlots: document.querySelectorAll('#draft-red-slots .draft-slot').length,
          phase: window.DRAFT.phase, timer: document.getElementById('draft-timer').textContent,
          sel: window.DRAFT.sel, teamSize: window.DRAFT.teamSize
        }))()
        """)
        print('draft aberto:', r)
        if not r['draftActive']: fails.append('draft-screen NAO ativa')
        if r['lobbyActive']: fails.append('lobby deveria estar escondida')
        if r['cards'] != 12: fails.append(f"board deveria ter 12 cards: {r['cards']}")
        if r['blueSlots'] != 3 or r['redSlots'] != 3: fails.append(f"slots deveriam ser 3/3: {r['blueSlots']}/{r['redSlots']}")
        if r['phase'] != 'pick': fails.append(f"phase inicial deveria ser pick: {r['phase']}")
        import re as _re
        m = _re.match(r'00:(\d+)$', r['timer'] or '')
        if not m or not (14 <= int(m.group(1)) <= 20): fails.append(f"timer fora de 00:14-00:20: {r['timer']}")
        if r['teamSize'] != 3: fails.append('teamSize != 3')

        # screenshot do draft
        d = await c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(SHOTS, 'wmenu_draft_pick.png'), 'wb').write(base64.b64decode(d['data']))

        # 2. preview (pick) — Sakura
        await ev(c, "window.draftPick('1skr'); return true;".replace('return true', '(() => { window.draftPick(\'1skr\'); return true; })()'))
        await asyncio.sleep(0.3)
        r2 = await ev(c, """
        (() => ({
          sel: window.DRAFT.sel,
          name: document.getElementById('draft-hero-name').textContent,
          selCard: !!document.querySelector('#draft-board .draft-card.sel'),
          selectedHeroId: window.selectedHeroId
        }))()
        """)
        print('preview:', r2)
        if r2['sel'] != '1skr': fails.append(f"sel deveria ser 1skr: {r2['sel']}")
        if 'Sakura' not in r2['name']: fails.append(f"nome do hero errado: {r2['name']}")
        if not r2['selCard']: fails.append('card .sel nao aplicado')
        if r2['selectedHeroId'] != '1skr': fails.append('selectedHeroId nao atualizou (preview do pedestal)')

        # 3. timer curto -> auto-lock
        await ev(c, "window.DRAFT.remaining = 0.35; return true;".replace('return true', '(() => { window.DRAFT.remaining = 0.35; return true; })()'))
        ok = await wait_js(c, "window.DRAFT.phase !== 'pick'", timeout=10)
        r3 = await ev(c, """
        (() => ({
          phase: window.DRAFT.phase, blue0: window.DRAFT.blue[0],
          lockDisabled: document.getElementById('btn-draft-lock').disabled,
          phaseTxt: document.getElementById('draft-phase').textContent,
          blueFilled: document.querySelectorAll('#draft-blue-slots .draft-slot.filled').length
        }))()
        """)
        print('auto-lock:', ok, r3)
        if not ok: fails.append('timer nao disparou auto-lock')
        if r3['phase'] != 'lock': fails.append(f"phase apos lock: {r3['phase']}")
        if r3['blue0'] != '1skr': fails.append(f"blue[0] deveria ser a pick: {r3['blue0']}")
        if not r3['lockDisabled']: fails.append('botao SELAR deveria estar desabilitado')

        # 4. bots pensam -> todos prontos
        ok2 = await wait_js(c, "window.DRAFT.phase === 'reveal'", timeout=25)
        r4 = await ev(c, "(() => ({ blue: window.DRAFT.blue, red: window.DRAFT.red, ready: window.DRAFT.redReady }))()")
        print('bots prontos:', ok2, r4)
        if not ok2: fails.append('bots nao terminaram (phase != reveal)')
        blue_filled = [x for x in (r4['blue'] or []) if x]
        if len(blue_filled) != 3: fails.append(f"blue incompleto: {r4['blue']}")
        if not all(r4['ready'] or []): fails.append(f"redReady incompleto: {r4['ready']}")

        # 5. reveal -> partida
        ok3 = await wait_js(c, "window.DRAFT.phase === 'done' && window.matchActive === true", timeout=25)
        r5 = await ev(c, """
        (() => {
          const us = window.units || [];
          return {
            units: us.length,
            blue: us.filter(u => u.team === 'blue').map(u => u.heroId).sort(),
            red: us.filter(u => u.team === 'red').map(u => u.heroId).sort(),
            player: us.find(u => u.isPlayer) ? us.find(u => u.isPlayer).heroId : null,
            matchActive: window.matchActive
          };
        })()
        """)
        print('pos-reveal:', ok3, r5)
        if not ok3: fails.append('reveal nao chegou a partida')
        if r5['units'] != 6: fails.append(f"deveriam ter 6 units: {r5['units']}")
        if r5['player'] != '1skr': fails.append(f"player deveria ser 1skr: {r5['player']}")
        blueset = set(r5['blue'] or [])
        redset = set(r5['red'] or [])
        if len(blueset) != 3: fails.append(f"blue com repeticao: {r5['blue']}")
        if len(redset) != 3: fails.append(f"red com repeticao: {r5['red']}")
        if redset & blueset: fails.append(f"heroi repetido entre times: {sorted(redset & blueset)}")

        # partida roda 2s sem erro
        await asyncio.sleep(2.0)
        d2 = await c.send('Page.captureScreenshot', {'format': 'png' })
        open(os.path.join(SHOTS, 'wmenu_draft_postmatch.png'), 'wb').write(base64.b64decode(d2['data']))

        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        if errs: fails.append(f'{len(errs)} console errors')

        # 6. cancel do draft (fluxo separado)
        await ev(c, "(() => { window.returnToLobby(); return true; })()")
        await asyncio.sleep(0.4)
        await ev(c, "(async () => { await window.openDraft('br_vila'); return 'ok'; })()", await_promise=True)
        r6 = await ev(c, "(() => ({ matchActive: window.matchActive, draftActive: document.getElementById('draft-screen').classList.contains('active') }))()")
        print('br_vila (sem draft):', r6)
        if r6['draftActive']: fails.append('br_vila NAO deveria abrir draft')
        if not r6['matchActive']: fails.append('br_vila deveria iniciar partida direto')

        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    print('=' * 46)
    if fails:
        print('T3/T4 FAIL:'); [print('  -', f) for f in fails]
    else:
        print('T3/T4 PASS: draft completo — pick/auto-lock/bots/reveal/partida, composicao fiel')


if __name__ == '__main__':
    asyncio.run(main())
