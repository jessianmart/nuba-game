"""PV4 — TOUCH HUD V2 (docs/PIVOT_MOBILE.md §PV4).
Pedido do usuario: mapa no topo; HP e chakra cada um de um lado; base APENAS
joystick (esq) + skills (dir) COM tempo de CD; banners de streak/oulti discretos
no padrao do APK; menos poluicao visual.

Estrategia: ZERO componente novo no DOM — reaproveita os existentes via gates
body.touch (esconde o que nao faz sentido no touch, reposiciona o resto) e
espelha o CD dos slots desktop (#cd-*) nos botoes touch (#cdt-*).

Edits:
  E1 game.js — espelho de CD nos tbtns (5 linhas, no updater existente)
  E2 index.html — div .tbtn-cd dentro dos 5 tbtns (c = chakra hold, nao tem CD)
  E3 styles.css — bloco PV4 (gates body.touch, ~45 linhas)
Run: python tools/pv4_touch_hud_patch.py   (cwd = repo root)
"""
import shutil
import subprocess

GJ = 'public/game.js'
HTML = 'public/index.html'
CSS = 'public/styles.css'
shutil.copy2(GJ, GJ + '.bak_pv4')
shutil.copy2(HTML, HTML + '.bak_pv4')
shutil.copy2(CSS, CSS + '.bak_pv4')

g = open(GJ, 'r', encoding='utf-8', newline='').read()   # LF
h = open(HTML, 'r', encoding='utf-8', newline='').read()  # CRLF
c = open(CSS, 'r', encoding='utf-8', newline='').read()   # CRLF


def rep(text, old, new, what, n=1):
    k = text.count(old)
    assert k == n, f'{what}: esperava {n}, achei {k}'
    return text.replace(old, new, 1 if n == 1 else None)


# E1 — espelho de CD nos botoes touch (fonte unica: #cd-* dos slots)
g = rep(g,
        """    } else {
      cdEl.style.display = 'none';
      cdEl.style.background = 'none';
      cdEl.textContent = '';
    }
  }
""",
        """    } else {
      cdEl.style.display = 'none';
      cdEl.style.background = 'none';
      cdEl.textContent = '';
    }
  }

  // PV4: espelha o CD dos slots nos botoes touch (mesma fonte de verdade #cd-*)
  for (const _s of ['atk', 'q', 'w', 'e', 'r']) {
    const _src = document.getElementById(`cd-${_s}`);
    const _dst = document.getElementById(`cdt-${_s}`);
    if (_src && _dst) {
      _dst.style.display = _src.style.display;
      _dst.style.background = _src.style.background;
      _dst.textContent = _src.textContent;
    }
  }
""",
        'E1 espelho CD touch')

# E2 — .tbtn-cd dentro dos 5 botoes (antes de cada img)
for slot, ico in [('r', 'icon_r'), ('q', 'icon_q'), ('e', 'icon_e'), ('w', 'icon_w'), ('atk', 'icon_atk')]:
    old = f'<img src="assets/ui/skin/{ico}.png"'
    new = f'<div class="tbtn-cd" id="cdt-{slot}"></div>\r\n              <img src="assets/ui/skin/{ico}.png"'
    assert h.count(old) == 1, f'E2 {slot}: {h.count(old)}'
    h = h.replace(old, new, 1)
print('[ok] E2: 5 tbtn-cd inseridos')

# E3 — bloco CSS PV4
PV4 = '''\r\n
/* ==== PV4: TOUCH HUD V2 (docs/PIVOT_MOBILE.md §PV4) ====
   Pedido: mapa no topo; HP/chakra cada um de um lado; base APENAS joystick
   (esq) + skills (dir) com CD; banners discretos. Gate: body.touch + partida.
   Zero componente novo — reposiciona/esconde o que ja existe. */
body.touch #hud-screen.active .hud-brand-pill,
body.touch #hud-screen.active .team-group,
body.touch #hud-screen.active .match-goal-txt,
body.touch #hud-screen.active .player-avatar-ring,
body.touch #hud-screen.active .sub-status-line,
body.touch #hud-screen.active .abilities-ribbon { display: none; }

/* top bar: so o cluster central (timer/BR) + ações compactas */
body.touch #hud-screen.active .hud-top-bar { justify-content: center; }
body.touch #hud-screen.active .match-center-cluster { transform: scale(0.82); }
body.touch #hud-screen.active .hud-actions-pill { position: fixed; top: calc(4px + var(--safe-top, 0px)); right: calc(4px + var(--safe-right, 0px)); z-index: 62; gap: 4px; }
body.touch #hud-screen.active .hud-top-btn { padding: 4px 7px; font-size: 9px; letter-spacing: 0.5px; }

/* footer neutro: filhos (minimapa + deck) posicionam sozinhos no viewport */
body.touch #hud-screen.active .hud-bottom-moba { display: contents; }

/* MAPA no topo (esquerda) */
body.touch #hud-screen.active .minimap-bezel { position: fixed; top: calc(4px + var(--safe-top, 0px)); left: calc(4px + var(--safe-left, 0px)); z-index: 60; pointer-events: none; transform: scale(0.6); transform-origin: top left; }

/* HP um lado / CHAKRA o outro (faixa abaixo do mapa) */
body.touch #hud-screen.active .player-command-deck { position: fixed; top: calc(104px + var(--safe-top, 0px)); left: calc(6px + var(--safe-left, 0px)); right: calc(6px + var(--safe-right, 0px)); z-index: 60; pointer-events: none; background: none; border: none; box-shadow: none; padding: 0; width: auto; }
body.touch #hud-screen.active .vitals-strip { gap: 6px; width: 100%; }
body.touch #hud-screen.active .vital-gauges-col { flex-direction: row; flex: 1; gap: 6px; }
body.touch #hud-screen.active .hp-gauge { flex: 1 1 0; }
body.touch #hud-screen.active .chakra-gauge { flex: 1 1 0; }
body.touch #hud-screen.active .gauge-num { font-size: 10px; }

/* banners de sequencia/ulti: discretos, padrao APK (escala menor) */
body.touch #hud-screen.active .streak-banner,
body.touch #hud-screen.active .ougi-banner { transform: scale(0.55); top: 140px; }

/* CD visivel nos botoes touch (espelhado de #cd-* pelo game.js) */
.tbtn { position: relative; }
.tbtn-cd { position: absolute; inset: 0; border-radius: 50%; display: none; align-items: center; justify-content: center; font-family: 'Storm Title', 'Poppins', sans-serif; font-size: 13px; font-weight: 700; color: #fff; text-shadow: 0 1px 3px #000; pointer-events: none; }
'''
c = c.rstrip() + PV4

open(GJ, 'w', encoding='utf-8', newline='').write(g)
open(HTML, 'w', encoding='utf-8', newline='').write(h)
open(CSS, 'w', encoding='utf-8', newline='').write(c)
print('[ok] game.js E1 + styles.css E3')

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
print('PV4 PATCH DONE')
