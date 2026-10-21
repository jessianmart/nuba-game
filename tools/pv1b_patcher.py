# -*- coding: utf-8 -*-
"""PV1.1b: conserta a duplicacao do 1o run parcial (index/styles gravados antes do
game.js falhar; 2o run duplicou). Remove TODAS as copias do bloco touch e insere
UMA; adiciona pointer-events:auto (hud-screen herda none). Rollback: .bak_pv1b"""
import io, sys, shutil

def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new, expect in patches:
        c = s.count(old)
        if c != expect:
            print(f'ANCHOR FAIL [{path}:{name}]: {c} occ (esperado {expect})'); return False
        s = s.replace(old, new)
        print(f'  [OK] {path}:{name} (removidas {expect}, inserida 1 copia limpa)' if expect >= 1 else f'  [OK] {path}:{name}')
    shutil.copyfile(path, path + '.bak_pv1b')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

DOM_BLOCK = '''    <!-- PV1.3/PV1.4: controles touch (aditivos — visíveis apenas em body.touch) -->
    <div id="touch-joystick" class="touch-only" aria-hidden="true">
      <div id="touch-joystick-base"></div>
      <div id="touch-joystick-knob"></div>
    </div>
    <div id="touch-cluster" class="touch-only" aria-hidden="true">
      <button type="button" id="tc-atk" class="tc-btn tc-atk" data-slot="atk" aria-label="Ataque Básico (segure)">ATK</button>
      <button type="button" id="tc-q" class="tc-btn" data-slot="q" aria-label="Jutsu 1">Q</button>
      <button type="button" id="tc-w" class="tc-btn" data-slot="w" aria-label="Jutsu 2">W</button>
      <button type="button" id="tc-e" class="tc-btn tc-kawarimi" data-slot="e" aria-label="Kawarimi">K</button>
      <button type="button" id="tc-r" class="tc-btn tc-ult" data-slot="r" aria-label="Ultimate">R</button>
    </div>'''

DOM_CLEAN = DOM_BLOCK + '\n'  # unica copia apos o dedup

CSS_BLOCK = '''
/* ==================== PV1 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==================== */
#touch-joystick { position: fixed; left: 0; bottom: 0; width: 42%; height: 62%; z-index: 90; touch-action: none; display: none; }
#touch-joystick-base { position: fixed; width: 128px; height: 128px; border-radius: 50%; border: 2px solid rgba(201,162,39,.55); background: rgba(8,9,15,.35); opacity: 0; transform: translate(-50%,-50%); transition: opacity .12s; pointer-events: none; }
#touch-joystick-knob { position: fixed; width: 56px; height: 56px; border-radius: 50%; background: rgba(201,162,39,.85); box-shadow: 0 0 18px rgba(201,162,39,.4); opacity: 0; transform: translate(-50%,-50%); transition: opacity .12s; pointer-events: none; }
#touch-joystick.live #touch-joystick-base, #touch-joystick.live #touch-joystick-knob { opacity: 1; }
#touch-cluster { position: fixed; right: calc(14px + env(safe-area-inset-right)); bottom: calc(108px + env(safe-area-inset-bottom)); z-index: 90; display: none; grid-template-columns: repeat(2, 76px); grid-auto-rows: 76px; gap: 10px; touch-action: none; }
body.touch #touch-joystick { display: block; }
body.touch #touch-cluster { display: grid; }
.tc-btn { width: 76px; height: 76px; border-radius: 50%; border: 2px solid rgba(201,162,39,.5); background: rgba(18,20,28,.72); color: #fbbf24; font-family: 'Barlow Condensed', sans-serif; font-size: 21px; letter-spacing: 1px; cursor: pointer; }
.tc-atk { grid-row: span 2; width: 96px; height: 96px; background: rgba(139,26,26,.55); border-color: rgba(201,162,39,.8); font-size: 18px; align-self: end; }
.tc-ult { border-color: rgba(255,80,0,.75); color: #ff9d5c; }
.tc-kawarimi { border-color: rgba(163,230,53,.5); color: #d4f99b; }
.tc-btn:active { transform: scale(.92); }
body.touch .ability-key { display: none; } /* §2.4: badges de tecla escondidos no touch */'''

CSS_CLEAN = CSS_BLOCK + '\n'

ok1 = apply('public/index.html', [
    # remove AMBAS as copias duplicadas do bloco touch e insere UMA apos a linha do hud-screen
    ('dedup DOM touch (2 copias -> 0, depois 1)',
     DOM_BLOCK + '\n' + DOM_BLOCK + '\n',
     '',
     1),
    ('inserir copia unica',
     '  <div id="hud-screen" class="screen">\n',
     '  <div id="hud-screen" class="screen">\n' + DOM_CLEAN,
     1),
])

ok2 = apply('public/styles.css', [
    ('dedup CSS PV1 (2 copias -> 0, depois 1)',
     CSS_BLOCK + '\n' + CSS_BLOCK,
     '',
     1),
    ('inserir CSS unico + pointer-events',
     "body.touch .ability-key { display: none; } /* §2.4: badges de tecla escondidos no touch */".replace('§2.4: badges de tecla escondidos no touch', 'PLACEHOLDER_NUNCA_EXISTE') if False else ".aj-keys kbd { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px; color: #fbbf24; background: rgba(201, 162, 39, 0.08); border: 1px solid rgba(201, 162, 39, 0.3); border-radius: 4px; padding: 3px 7px; min-width: 52px; text-align: center; }",
     ".aj-keys kbd { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px; color: #fbbf24; background: rgba(201, 162, 39, 0.08); border: 1px solid rgba(201, 162, 39, 0.3); border-radius: 4px; padding: 3px 7px; min-width: 52px; text-align: center; }\n" + CSS_BLOCK.replace('touch-action: none; display: none; }', 'touch-action: none; display: none; pointer-events: auto; }', 1).replace('grid-auto-rows: 76px; gap: 10px; touch-action: none; }', 'grid-auto-rows: 76px; gap: 10px; touch-action: none; pointer-events: auto; }', 1),
     1),
])

print('PV1b:', 'APLICADO' if (ok1 and ok2) else 'ABORTADO')
sys.exit(0 if (ok1 and ok2) else 1)
