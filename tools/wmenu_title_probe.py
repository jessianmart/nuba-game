# -*- coding: utf-8 -*-
"""W-MENU T1: tela-titulo ativa no boot -> clique/Enter vai pra Home; startMatch
direto (E2E) remove o titulo (nao vaza pro HUD); 0 console errors."""
import asyncio, base64, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')


def free_port():
    st = socket.socket(); st.bind(('127.0.0.1', 0)); p = st.getsockname()[1]; st.close(); return p


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_title_')
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

        # esperar boot completo
        for _ in range(60):
            if await ev(c, 'typeof window.startMatch') == 'function' and await ev(c, 'window.__ajustesReady === true'):
                break
            await asyncio.sleep(0.5)

        r = await ev(c, """
        (() => ({
          titleActive: document.getElementById('title-screen').classList.contains('active'),
          lobbyActive: document.getElementById('lobby-screen').classList.contains('active')
        }))()
        """)
        print('boot:', r)
        if not r['titleActive']: fails.append('titulo NAO esta ativo no boot')
        if r['lobbyActive']: fails.append('lobby NAO deveria estar ativo no boot')

        # clique no botao TOCAR PARA INICIAR
        await ev(c, "(() => { document.getElementById('btn-title-play').click(); return true; })()")
        await asyncio.sleep(0.6)
        r2 = await ev(c, """
        (() => ({
          titleActive: document.getElementById('title-screen').classList.contains('active'),
          lobbyActive: document.getElementById('lobby-screen').classList.contains('active'),
          playPageActive: document.getElementById('page-play').classList.contains('active'),
          dismissed: typeof window.__TITLE_DISMISSED
        }))()
        """)
        print('apos clique:', r2)
        if r2['titleActive']: fails.append('titulo NAO saiu no clique')
        if not r2['lobbyActive']: fails.append('lobby NAO entrou no clique')
        if not r2['playPageActive']: fails.append('page-play NAO ficou ativa')
        if r2['dismissed'] != 'number': fails.append('__TITLE_DISMISSED nao setado')

        # screenshot do titulo em NOVA aba (estado boot) pra revisao estetica
        d = await c.send('Page.captureScreenshot', {'format': 'png'})
        open(os.path.join(SHOTS, 'wmenu_title_after.png'), 'wb').write(base64.b64decode(d['data']))

        # startMatch direto (padrao E2E) — titulo nao deve vazar pro HUD
        ok = await ev(c, "(async () => { try { await window.startMatch('dm_3v3'); return 'ok'; } catch (e) { return 'ERR:' + e.message; } })()", await_promise=True)
        print('startMatch direto:', ok)
        if ok != 'ok': fails.append(f'startMatch falhou: {ok}')
        r3 = await ev(c, """
        (() => ({
          titleActive: document.getElementById('title-screen').classList.contains('active'),
          hudActive: document.getElementById('hud-screen').classList.contains('active'),
          units: window.units ? window.units.length : -1
        }))()
        """)
        print('partida:', r3)
        if r3['titleActive']: fails.append('titulo vazou sobre o HUD')
        if not r3['hudActive']: fails.append('HUD NAO ativo')
        if r3['units'] != 6: fails.append(f"units esperado 6, veio {r3['units']}")

        # voltar ao lobby NAO deve reabrir o titulo
        await ev(c, "(() => { window.returnToLobby(); return true; })()")
        await asyncio.sleep(0.4)
        r4 = await ev(c, """
        (() => ({
          titleActive: document.getElementById('title-screen').classList.contains('active'),
          lobbyActive: document.getElementById('lobby-screen').classList.contains('active')
        }))()
        """)
        print('retorno ao lobby:', r4)
        if r4['titleActive']: fails.append('titulo reapareceu ao voltar do lobby')
        if not r4['lobbyActive']: fails.append('lobby NAO voltou')

        errs = [e for e in getattr(c, 'console_errors', []) if 'net::ERR' not in str(e)]
        print(f'console errors: {len(errs)}')
        if errs: fails.append(f'{len(errs)} console errors')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    print('=' * 46)
    if fails:
        print('T1 FAIL:'); [print('  -', f) for f in fails]
    else:
        print('T1 PASS: titulo -> home -> partida -> retorno, 0 errors')


if __name__ == '__main__':
    asyncio.run(main())
