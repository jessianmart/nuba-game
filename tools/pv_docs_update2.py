"""Docs update 2 — Vila Konoha (sa00z) + otimizacao Blender + variante mobile (PV2-A).
Depende de: tools/probe_pv2a_mobile_branch.py ter passado + bateria pv2a verde.
Run: python pv_docs_update2.py   (cwd = repo root)
"""
import os


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


# gate: probes verdes
for f, marker in [('pv2a_probe.log', 'PV2A PROBE DONE'),
                  ('pv2a_suite.log', 'SUITE EXIT: 0'),
                  ('pv2a_verify.log', 'VERIFY EXIT: 0')]:
    assert os.path.exists(f), f'{f} nao existe — rode a bateria primeiro'
    assert marker in rd(f), f'{f} sem marcador {marker}'

# ---------- PROJECT.md ----------
prj = rd('PROJECT.md')
FEAT = '''| 42 | Vila Konoha (sa00z) extraida do APK: cenario BR-ready | Chunk `sa00z` (hub do modo aventura do Storm 1) identificado por anatomia: `hkg` (monumento Hokage), `rock00-03` (paredões), `river01` + `hasi00-03` (rio + 4 pontes), 206 meshes de árvore/folhagem (ki/ha); vinculo `rntf sa00xgimXXX` ↔ `GIMKonohaAct`; 9.92MB de geometria + 15MB de texturas, 261 meshes, 163k verts, raio 140m; 9a arena no catalogo (F23 dinamico) | PV2 (Realeza na Vila) | docs/PIVOT_MOBILE.md §PV2 |
| 43 | Otimizacao Blender da vila: -88% draw calls | `tools/vila_blender_optimize.py` (Blender 5.2 headless): join por textura (261→32 meshes) + decimate por classe (rios/pontes 0.80, Hokage 0.75, rochas 0.65, folhagem 0.45) → 60.8k tris (-53%), 7.05MB (-32%); variante `sa00z.mobile.json` servida via `mapMobile` no catalogo + branch `__DEVICE.isMobile` no `applyArena` (desktop segue no full); validado por probe (UA mobile carrega .mobile) + screenshot 189KB sem erro + bateria 38/38 | PV2 (Realeza na Vila) | docs/PIVOT_MOBILE.md §PV2 |
'''
anchor = '## Milestones'
assert prj.count(anchor) == 1
prj = prj.replace(anchor, FEAT + '\n' + anchor, 1)
wr('PROJECT.md', prj)
print('[ok] PROJECT.md: features 42-43')

# ---------- TEST_READY.md ----------
tr = rd('TEST_READY.md')
assert '## Vila Konoha (PV2-A)' not in tr
SEC = '''

---

## Vila Konoha (PV2-A) — 2026-10-21

**Extracao**: `data/stage/sa00z` (54MB) de `rom_original.cpk` via `tools/cpk_extract.py` para `public/assets/stage/raw/`; build via `tools/build_arena.py sa00z --name AREA_KONOHA_ACT --label "Vila Oculta da Folha (Konoha)"` (261 meshes, 163k verts, 9.92MB + 71 texturas).

**Identificacao (por que sa00z = Konoha)**: `sa00zhkg00/01` = monumento Hokage; `rock00-03` = paredões; `river01` + `hasi00-03` (橋) = rio + 4 pontes; 206 meshes ki/ha (arvore/folha); chunks `rntf sa00xgimXXX` ↔ `GIMKonohaAct` (gimmicks do mapa Konoha). Sp00 = campo/Floresta (sd03a embed), sm00a = area de missao com start/end, sk00a = skybox — descartados.

**Otimizacao Blender** (`tools/vila_blender_optimize.py`, Blender 5.2 headless):
- join por textura (261 → 32 meshes = -88% draw calls) + decimate por classe (river/hasi 0.80, hkg 0.75, rock 0.65, ki/ha 0.45, resto 0.55)
- 128.573 → 60.799 tris (-53%); JSON 10.4MB → 7.05MB (round 3-4 casas em floats)
- schema do loader preservado: positions/normais/uvs flat por vertice, indices triangulado, mat_cmap intacto

**Variante mobile**: campo `mapMobile` no catalog + branch `__DEVICE.isMobile` no `applyArena` (desktop = JSON full; mobile = otimizado); cache-bust arenas/catalogo v9. Probe `tools/probe_pv2a_mobile_branch.py`: UA Pixel/Android → confirma `sa00z.mobile.json?v=9` no resource timing (desktop carrega o full).

**PitfallsBlender 5.2 registrados** (skills: ver skill `blender-headless-assets`):
- `create_normals_split()`/`calc_normals()` foram REMOVIDOS — vertex normals sao auto-avaliados (`v.normal` funciona apos decimate)
- `MLoopTri.loops` devolve 3 INTS (indices), nao objetos: `me.loops[tri.loops[i]].vertex_index`
- `modifier_apply` RECRIA o datablock: rebuscar `me = obj.data` e `uv_layer = me.uv_layers.active` apos apply
- `from_pydata` DESCARTA faces degeneradas: nunca indexar `uv_layer.data` por `li*3+corner`; atribuir por loop real (`lp.index`/`lp.vertex_index`)
- UV em Blender 5.x: `uv_layer.data[lp.index].uv` (nao `lp[uv_layer]`)
- CDPClient da suite nao tem `.on()`; interceptores de fetch nao funcionam — use swap em disco (com backup + restore no finally)
'''
tr = tr.rstrip() + SEC
wr('TEST_READY.md', tr)
print('[ok] TEST_READY.md: secao Vila')

# ---------- docs/PIVOT_MOBILE.md status ----------
pv = rd('docs/PIVOT_MOBILE.md')
pv = pv.replace('### Fase PV2 — Realeza na Vila', '### Fase PV2 — Realeza na Vila — **STATUS: EM ANDAMENTO (mapa da vila extraido + otimizado; layout BR pendente)**', 1)
wr('docs/PIVOT_MOBILE.md', pv)
print('[ok] PIVOT_MOBILE.md: status PV2')
print('DOCS2 DONE')
