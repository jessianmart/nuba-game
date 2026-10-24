# -*- coding: utf-8 -*-
"""W-MENU T2c: layout DOM do draft (3 colunas, board, lock button, sem vazamento)."""
import asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def ev(c, expr, await_promise=False):
    v = await c.eval_js(expr, await_promise)
    if isinstance(v, dict) and 'value' in v:
        v = v['value']
    return v


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_draftlay_')
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
        for _ in range(60):
            if await c.eval_js('window.__ajustesReady === true'):
                break
            await asyncio.sleep(0.5)
        await ev(c, "(() => { window.dismissTitle(); window.__TITLE_DISMISSED = 1; return true; })()")
        await ev(c, "(async () => { await window.openDraft('dm_3v3'); return 'ok'; })()", await_promise=True)
        await asyncio.sleep(0.8)
        r = await ev(c, """
        (() => {
          const q = (s) => document.querySelector(s);
          const rect = (el) => { if (!el) return null; const b = el.getBoundingClientRect();
            return { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height),
                     font: Math.round(parseFloat(getComputedStyle(el).fontSize)) }; };
          const els = {
            blue: rect(q('#draft-blue-slots')), center: rect(q('.draft-center')), red: rect(q('#draft-red-slots')),
            board: rect(q('#draft-board')), timer: rect(q('#draft-timer')), lock: rect(q('#btn-draft-lock')),
            heroInfo: rect(q('#draft-hero-info')), footer: rect(q('.draft-footer')), card0: rect(q('#draft-board .draft-card'))
          };
          const vp = { w: innerWidth, h: innerHeight };
          const cards = document.querySelectorAll('#draft-board .draft-card').length;
          const chips = document.querySelectorAll('.draft-chip').length;
          const boardBottom = els.board ? els.board.y + els.board.h : -1;
          const lockTop = els.lock ? els.lock.y : -1;
          return { vp, els, cards, chips, boardAboveLock: lockTop >= boardBottom,
                   inView: !!els.board && els.board.y >= 0 && boardBottom <= vp.h && !!els.lock && els.lock.y + els.lock.h <= vp.h };
        })()
        """)
        print('viewport:', r['vp'], '| cards:', r['cards'], '| chips:', r['chips'])
        for k, v in r['els'].items():
            if v: print(f"  {k:10} x={v['x']:4} y={v['y']:4} {v['w']:4}x{v['h']:3}")
        fails = []
        if r['cards'] != 12: fails.append(f"cards={r['cards']}")
        if not r['boardAboveLock']: fails.append('board e lock sobrepostos')
        if not r['inView']: fails.append('elementos vazando do viewport')
        if r['els']['lock'] and r['els']['lock']['h'] < 44: fails.append(f"botao lock pequeno: {r['els']['lock']['h']}")
        if r['els']['timer'] and r['els']['timer']['font'] < 24: fails.append('timer pequeno')
        lb, lc, lr = r['els']['blue'], r['els']['center'], r['els']['red']
        if lb and lc and not (lb['x'] + lb['w'] <= lc['x'] + 4): fails.append('blue invade o centro')
        if lr and lc and not (lc['x'] + lc['w'] <= lr['x'] + 4): fails.append('centro invade red')
        print('layout fails:', fails if fails else 'NENHUM')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
