# -*- coding: utf-8 -*-
"""W-MENU T1c: mede os rects DOM da tela-titulo e checa sobreposicao/constraste."""
import asyncio, json, os, shutil, socket, subprocess, sys, tempfile, time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.test_e2e_suite import CDPClient, find_edge_path


def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); p = s.getsockname()[1]; s.close(); return p


async def main():
    port = free_port()
    profile = tempfile.mkdtemp(prefix='nuba_titlelay_')
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
        r = await c.eval_js("""
        (() => {
          const sel = ['.title-kanji-top', '.title-logo-jp', '.title-logo-sub', '.title-tagline',
                       '#btn-title-play', '.title-play-text strong', '.title-play-kanji', '.title-footer'];
          const out = {};
          for (const s of sel) {
            const el = document.querySelector(s);
            if (!el) { out[s] = null; continue; }
            const b = el.getBoundingClientRect();
            const cs = getComputedStyle(el);
            out[s] = { x: Math.round(b.x), y: Math.round(b.y), w: Math.round(b.width), h: Math.round(b.height),
                       font: Math.round(parseFloat(cs.fontSize)), color: cs.color, visible: cs.display !== 'none' };
          }
          const vp = { w: innerWidth, h: innerHeight };
          const btn = out['#btn-title-play'], logo = out['.title-logo-jp'];
          const overlap = !!(btn && logo) && btn.y < logo.y + logo.h && logo.y < btn.y + btn.h;
          return { vp, els: out, overlapLogoBtn: overlap,
                   inViewport: !!(btn && btn.y >= 0 && btn.y + btn.h <= innerHeight) };
        })()
        """)
        print('viewport:', r['vp'])
        for k, v in r['els'].items():
            if v: print(f"  {k:26} x={v['x']:4} y={v['y']:4} {v['w']:4}x{v['h']:3} font={v['font']:3}px color={v['color']}")
            else: print(f"  {k:26} AUSENTE")
        fails = []
        if r['overlapLogoBtn']: fails.append('logo e botao SOBREPOSTOS')
        if not r['inViewport']: fails.append('botao FORA do viewport')
        for k, v in r['els'].items():
            if v is None: fails.append(f'{k} ausente')
        lo = r['els']['.title-logo-jp']
        if lo and lo['font'] < 40: fails.append(f"logo pequeno ({lo['font']}px)")
        bt = r['els']['#btn-title-play']
        if bt and bt['h'] < 40: fails.append(f"botao pequeno ({bt['h']}px)")
        ft = r['els']['.title-footer']
        if ft and ft['y'] + ft['h'] > r['vp']['h']: fails.append('footer vazando do viewport')
        print('layout fails:', fails if fails else 'NENHUM')
        c.running = False
    finally:
        proc.terminate()
        shutil.rmtree(profile, ignore_errors=True)


if __name__ == '__main__':
    asyncio.run(main())
