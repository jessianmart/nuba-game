"""Atualiza PROJECT.md / docs/PIVOT_MOBILE.md / TEST_READY.md com o PV4.
Run: python tools/pv4_docs_update.py   (cwd = repo root)
"""
F45 = '| 45 | PV4 — Touch HUD V2 (HUD mobile) | Reordenacao do HUD no gate `body.touch` + `#hud-screen.active`: minimapa fixo no topo-esquerda (scale 0.6), faixa de vitais com HP e chakra em lados opostos (row, metade cada), base APENAS joystick (esq) + cluster touch (dir); escondidos no touch: brand-pill, team-groups, goal txt, avatar ring, abilities-ribbon desktop, sub-status KDA; banners streak/ougi em scale 0.55 (padrao APK, discretos); CD nos botoes touch: 5x `.tbtn-cd` (conic + segundos) espelhados da fonte unica `#cd-*` pelo updater existente; zero componente novo no DOM, zero asset novo; probe_pv4_hud 13/13 checks (844x390) + probe_responsive 5/5 landscapes + BR + battery 38/38 | PV4 (HUD touch) | docs/PIVOT_MOBILE.md §PV4 |'

FASE = '''

### Fase PV4 — Touch HUD V2 (entregue 2026-10-21, pedido do usuario)

| # | Tarefa | Implementacao | Validacao |
|---|---|---|---|
| PV4.1 | HUD touch enxuto: mapa no topo, HP/chakra cada um de um lado, base so joystick+skills | Gates `body.touch #hud-screen.active` em styles.css (reposiciona via `position:fixed`/`display:contents`, esconde o que nao faz sentido) + 5 divs `.tbtn-cd` nos tbtns + espelho de CD no updater de `game.js` | probe_pv4_hud 13/13 + probe_responsive 5/5 |
'''

PIVOT_ANCHOR = '| PV3.4 | Smoke dispositivo real (user): LAN `http://<ip>:8080` (ou tunnel) — checklist | — | evidência do usuário (screenshot) |'
assert open('docs/PIVOT_MOBILE.md', encoding='utf-8').read().count(PIVOT_ANCHOR) == 1

PROJ = open('PROJECT.md', encoding='utf-8').read()
P44_TAIL = ' | PV2 (Realeza na Vila) | docs/PIVOT_MOBILE.md §PV2 |'
n = PROJ.count(P44_TAIL)
assert n >= 1, f'anchor 44: {n}'
PROJ = PROJ.replace(P44_TAIL, P44_TAIL + '\r\n' + F45, 1)
open('PROJECT.md', 'w', encoding='utf-8', newline='').write(PROJ)

D = open('docs/PIVOT_MOBILE.md', encoding='utf-8').read()
D = D.replace(PIVOT_ANCHOR, PIVOT_ANCHOR + FASE.replace('\n', '\r\n'), 1)
open('docs/PIVOT_MOBILE.md', 'w', encoding='utf-8', newline='').write(D)

T = open('TEST_READY.md', encoding='utf-8').read()
T += '''

### PV4 — TOUCH HUD V2 — validado 2026-10-21
- `tools/probe_pv4_hud.py` 13/13 checks em 844x390 landscape: minimapa no topo (`t=4`),
  HP à esquerda (`l=142`) e chakra à direita (`r=702`) na MESMA faixa (±30px), base
  apenas joystick (l<1/3) + cluster (r>2/3); escondidos por design no touch: brand pill,
  team-groups, goal txt, avatar ring, abilities-ribbon desktop, sub-status KDA.
- CD nos botoes touch: `#cdt-{q,w,e,r,atk}` espelham `#cd-*` (display + conic-gradient +
  texto de segundos) pelo updater existente de game.js — fonte unica, sem logica duplicada.
  Probe poe Q em CD e le `4.3s` + `conic-gradient` no botao.
- Banners streak/ougi: `transform: scale(0.55)` + `top: 140px` — discretos (padrao APK).
- `tools/probe_responsive.py` (pos-PV4): 5/5 landscapes OK — SE-land 568x320 (que
  estourava pre-PV4: team-group.red em 612..759, agora escondido) scrollW 568/568 sem
  overflow; top bar 46px (<52); tap targets 62-88px (>=44); portrait overlay ATIVO nos
  2 portraits; BR VIVOS/FASE visivel; 0 console errors.
- Novos `.bak`: game.js.bak_pv4, index.html.bak_pv4, styles.css.bak_pv4,
  probe_responsive.py.bak_pv4.
'''
open('TEST_READY.md', 'w', encoding='utf-8', newline='').write(T)
print('[ok] docs PV4: PROJECT.md #45, PIVOT_MOBILE §PV4, TEST_READY seção PV4')
