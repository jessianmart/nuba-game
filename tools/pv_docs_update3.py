"""Docs update 3 — layout BR mapeado (raycast) + santuarios corrigidos.
Gated na bateria vila2 verde. Run: python pv_docs_update3.py   (cwd = repo root)
"""
import json
import os


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


# gate
for f, m in [('vila2_verify.log', 'VERIFY EXIT: 0'), ('vila2_suite.log', 'SUITE EXIT: 0')]:
    assert os.path.exists(f) and m in rd(f), f'bateria vila2 nao verde ({f})'

lay = json.load(open('public/assets/data/br_vila_layout.json', encoding='utf-8'))
assert len(lay['spawnRing']) == 10 and len(lay['chests']) == 12

# PIVOT_MOBILE.md — dados do layout no contrato PV2
pv = rd('docs/PIVOT_MOBILE.md')
OLD = '### Fase PV2 — Realeza na Vila — **STATUS: EM ANDAMENTO (mapa da vila extraido + otimizado; layout BR pendente)**'
NEW = '''### Fase PV2 — Realeza na Vila — **STATUS: MAPA PRONTO (extraido + otimizado + layout raycast); modo BR pendente**

**Mapa (evidência, não estimativa)**: contorno polar raycast 72 ângulos (tools/br_vila_layout_map2.py) — núcleo contíguo r45-80 + braço leste até r130; `zoneRadiusStart=65`. Layout gravado em `public/assets/data/br_vila_layout.json`:
- `spawnRing`: 10 spawns solo no anel REAL da vila (r 35-55): (55,0) (44,32) (15,48) (-17,52) (-44,32) (-55,0) (-44,-32) (-17,-52) (14,-43) (44,-32)
- `zoneCenter (-10,0)`, zona 結界 65 → 6 em 6 fases
- `chests`: 12 baús no núcleo denso (±40)
- Santuários DM corrigidos para DENTRO da vila: blue (-40,-30) / red (45,30) (±95 originais caíam no vazio — player spawnava fora do visual)'''
assert pv.count(OLD) == 1
pv = pv.replace(OLD, NEW, 1)
wr('docs/PIVOT_MOBILE.md', pv)
print('[ok] PIVOT_MOBILE.md: dados do layout no contrato PV2')

# TEST_READY.md — probes do mapeamento
tr = rd('TEST_READY.md')
SEC = '''

### Mapeamento BR da vila (2026-10-21, probes numericos)
- `tools/probe_stage_bounds.py` / `tools/probe_vila_worldpos.py`: worldScale=0.022 em toda a cadeia; posicoes BAKED nos vertices (getWorldPosition de mesh = (0,0,0) — medir por localToWorld de vertice); vila renderiza ate ~±900 world (rio ±814/918) — MUITO maior que o clamp ±140.
- `tools/probe_vila_raycast.py` (grade 10m): 137/841 celulas com geometria acima; nucleo denso centrado (-10,0) densidade 49/49; anel r=80-125 VAZIO → spawns originais ±95 invalidos.
- `tools/br_vila_layout_map2.py` (polar 72 ang): 72/72 com chao, r 45-130 (r60=65) → `br_vila_layout.json` (10 spawns reais, zona 65→6/6 fases, 12 baus).
- `tools/fix_sa00z_sanctuaries.py`: santuarios DM → (-40,-30)/(45,30) dentro do contorno.
- Bateria vila2 (pos-fix): verify 0 + suite 38/38 (vila2_verify.log / vila2_suite.log).
- **Pitfall**: Box3.setFromObject devolveu bounds LOCAIS raw (matrixWorld stale em eval); unidades expõem u.x/u.z (nao u.pos); vision_analyze pode estar indisponivel (endpoint 404) — probes numericos (raycast/localToWorld) sao o caminho.
'''
tr = tr.rstrip() + SEC
wr('TEST_READY.md', tr)
print('[ok] TEST_READY.md: probes de mapeamento')
print('DOCS3 DONE')
