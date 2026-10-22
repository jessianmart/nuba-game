"""Docs PV3.2 (arena merge sd00a + sd03b).
Run: python tools/pv3_2_docs_update.py   (cwd = repo root)
"""
F47 = '| 47 | PV3.2 — arena merge mobile (sd00a + sd03b) | Pipeline GENERICO `tools/arena_blender_optimize.py -- <arenaId>` (Blender 5.2 headless): join por textura + decimate por classe calibrado por censo (obj 0.58 · ha/eda 0.50 · ki/flo/bac 0.45 · sd 0.60 · iwa/rock 0.65 · river/hasi 0.80), classe extraida do BASENAME DA TEXTURA (o nome da mesh embute o id da arena: sd00aobj008_sub0); sd00a 122→33 meshes (-73%) 3.58→2.53MB; **sd03b (arena default REAL de toda partida — descoberta por instrumentacao `window.__ARENA_LOADED`: dm_3v3 nao define `arena`, entao roda no palco default do lobby) 294→17 meshes (-94%) 93k→49.7k tris 8.02→5.48MB (-32%)**; `mapMobile` no catalogo + bump do fetch de dados `?v=11` (fetch embutido NAO e coberto pelo auto-cache-buster); probe_pv3_2_arena_v2 9/9 em 2 processos Edge independentes (mobile 17 meshes/109 draw calls/128k tris vs desktop 294/390/180k = -72% draw calls) + bateria 38/38 zero erros | PV3 (perf) | docs/PIVOT_MOBILE.md §PV3 |'

PIVOT = 'docs/PIVOT_MOBILE.md'
d = open(PIVOT, encoding='utf-8', newline='').read()
old_row = '| PV3.2 Arena merge (sd00a 122 meshes → ~20) | PENDENTE | pipeline Blender disponivel (`tools/vila_blender_optimize.py`) |'
new_row = ('| PV3.2 Arena merge mobile | **ENTREGUE** | `tools/arena_blender_optimize.py -- <id>`: **sd03b 294→17 meshes (-94%)**, '
           'sd00a 122→33 (-73%); `mapMobile` + `?v=11`; probe 9/9 — mobile **109 draw calls** vs desktop **390** (-72%) |')
assert d.count(old_row) == 1, f'ancora PV3.2: {d.count(old_row)}'
d = d.replace(old_row, new_row, 1)
open(PIVOT, 'w', encoding='utf-8', newline='').write(d)

p = open('PROJECT.md', encoding='utf-8', newline='').read()
a46 = ' | PV3 (perf/polimento) | docs/PIVOT_MOBILE.md §PV3 |'
assert p.count(a46) == 1, f'ancora 46: {p.count(a46)}'
p = p.replace(a46, a46 + '\r\n' + F47, 1)
open('PROJECT.md', 'w', encoding='utf-8', newline='').write(p)

t = open('TEST_READY.md', encoding='utf-8', newline='').read()
t += '''

### PV3.2 — ARENA MERGE MOBILE (sd00a + sd03b) — validado 2026-10-21
- **Descoberta que mudou o alvo**: instrumentando `window.__ARENA_LOADED` (asset +
  meshes carregados) descobriu-se que **a partida 3v3 roda no `sd03b` (294 meshes)**,
  nao no `sd00a`: `dm_3v3` nao define `arena`, entao o modo cai no palco default do
  lobby. Otimizar o sd00a era util (arena selecionavel), mas o sd03b e o mapa de
  TODA partida — 8,02 MB e o mais pesado do jogo.
- `tools/arena_blender_optimize.py -- <arenaId>` (generico, headless):
  - **sd03b: 294 → 17 meshes (-94%) | 93.164 → 49.714 tris (-47%) | 8,02 → 5,48 MB (-32%)**
  - sd00a: 122 → 33 meshes (-73%) | 40.111 → 22.228 tris (-45%) | 3,58 → 2,53 MB (-29%)
  - classe da mesh = basename da TEXTURA (nomes embutem o id: `sd00aobj008_sub0` →
    tira o prefixo do id e le as letras iniciais); ratios calibrados pelo censo real
    (obj 0.58 · ha/eda 0.50 · ki/flo/bac 0.45 · sd 0.60 · iwa/rock 0.65 · river/hasi 0.80).
- Catalogo: `mapMobile` em sd00a e sd03b + bump do fetch de dados `?v=9 → 11`
  (fetch embutido em codigo NAO e coberto pelo auto-cache-buster do index.html).
- `tools/probe_pv3_2_arena_v2.py` 9/9 — **2 processos Edge INDEPENDENTES** (o run no
  mesmo processo invertia os numeros: estado/ordem compartilhada): mobile carrega
  `sd03b.mobile.json` (17 meshes, **109 draw calls**, 128.981 tris) e desktop mantem
  `sd03b.json` (294 meshes, **390 draw calls**, 179.990 tris) → **-72% draw calls**.
- Bateria `pv32`: verify EXIT 0 + suite 38/38 zero console errors.
- Pitfalls: (1) `dm_3v3` sem `arena` roda no palco DEFAULT do lobby — nunca assuma
  qual arena a partida usa, instrumente; (2) `performance.getEntriesByType('resource')`
  estoura o buffer de 250 entradas no boot (a arena sai da lista) — use telemetria no
  jogo; (3) rodar as duas sessoes no MESMO processo Edge inverte/contamina os numeros.
- Novos `.bak`: arenas.json.bak_pv32/.bak_pv32d · game.js.bak_pv32/.bak_pv32c/.bak_pv32d.
'''
open('TEST_READY.md', 'w', encoding='utf-8', newline='').write(t)
print('[ok] docs PV3.2: PROJECT.md #47, PIVOT status ENTREGUE, TEST_READY secao PV3.2')
