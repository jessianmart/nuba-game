"""PV4.2 — Textos de ult/sequencia LEVES no touch + zoom afastado (pedido do usuario).

Pedidos: "diminuir o peso dos textos de ult na tela e sequencia" +
"afastar o zoom um pouco".

Descoberta do recon: a regra PV4 (transform: scale(0.55) nos banners) NUNCA
teve efeito — as keyframes streakPop/bannerPop e o GSAP sobrescrevem o
transform ao animar, e o banner aparecia no tamanho cheio (kanji 30px,
contador 42px, caixa min-width 340 + border 12 + padding 54). O peso real
cai mudando FONTES/CAIXA/MOLDURA, nao transform. Desktop intacto (gates
body.touch).

Edits:
  E1 styles.css — bloco PV4.2: streak (kanji 30->19, texto 22->13, contador
     42->26, min-width 340->220, padding 54->24, border 12->8, top 84px) e
     center-banner — o "texto de ult" (announce de skill/cast, L4609
     `${heroi}: ${jutsu}!`) — fonte 26->15, padding 60->24, border 14->8,
     top 36%->24%.
  E2 game.js — camDist 13.5 -> 16 (thirdperson, o modo mobile; pitch 0.32
     mantido) + window.__camera exposto p/ telemetria E2E de distancia.
Run: python tools/pv4_2_light_patch.py   (cwd = repo root)
"""
import shutil
import subprocess

CSS = 'public/styles.css'
GJ = 'public/game.js'
shutil.copy2(CSS, CSS + '.bak_pv42')
shutil.copy2(GJ, GJ + '.bak_pv42')

# ---------- E1: styles.css ----------
c = open(CSS, 'r', encoding='utf-8', newline='').read()
# ATENCAO: styles.css tem finais de linha MISTOS (4973 LF + 2 CRLF) — detector
# global de sep e armadilha; as ancoras abaixo foram verificadas em regiao LF.

old_block = """/* banners de sequencia/ulti: discretos, padrao APK (escala menor) */
body.touch #hud-screen.active .streak-banner,
body.touch #hud-screen.active .ougi-banner { transform: scale(0.55); top: 140px; }"""
new_block = """/* PV4.2 — banners de sequencia/ulti LEVES no touch (padrao APK, pedido do usuario).
   A regra PV4 anterior (transform: scale(0.55)) NAO tinha efeito: streakPop/bannerPop
   e o GSAP sobrescrevem o transform ao animar — o banner aparecia no tamanho cheio.
   Agora o peso cai onde vale: fonte, caixa e moldura. Desktop intacto. */
body.touch .streak-banner { top: 84px; min-width: 220px; padding: 6px 24px; gap: 10px; border-width: 8px; }
body.touch .streak-kanji { font-size: 19px; letter-spacing: 3px; }
body.touch .streak-text { font-size: 13px; letter-spacing: 2px; }
body.touch .streak-count { font-size: 26px; }
body.touch .ougi-banner { top: 84px; }
body.touch .center-banner { top: 24%; font-size: 15px; letter-spacing: 1.5px; padding: 8px 24px; border-width: 8px; }"""
assert c.count(old_block) == 1, f'ancora bloco PV4: {c.count(old_block)}'
c = c.replace(old_block, new_block, 1)
open(CSS, 'w', encoding='utf-8', newline='').write(c)
print('[ok] E1 styles.css: banners leves no touch (streak + center-banner)')

# ---------- E2: game.js (LF puro — 0 CRLF) ----------
g = open(GJ, 'r', encoding='utf-8', newline='').read()

old_cam = '    const camDist = 13.5;'
assert g.count(old_cam) == 1, f'ancora camDist: {g.count(old_cam)}'
g = g.replace(old_cam, '    const camDist = 16; // PV4.2: zoom afastado a pedido (era 13.5)', 1)

old_camdef = 'const camera = new THREE.PerspectiveCamera(48, window.innerWidth / window.innerHeight, 0.5, 4000);'
assert g.count(old_camdef) == 1, f'ancora camera def: {g.count(old_camdef)}'
g = g.replace(old_camdef, old_camdef + '\n'
              'window.__camera = camera; // PV4.2: telemetria E2E da distancia da camera', 1)

open(GJ, 'w', encoding='utf-8', newline='').write(g)
print('[ok] E2 game.js: camDist 13.5->16 + window.__camera')

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
print('PV4.2 PATCH DONE')
