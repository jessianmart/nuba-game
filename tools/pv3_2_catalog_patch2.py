"""PV3.2-D — adiciona mapMobile das arenas otimizadas e bumpa o fetch do mapa.
Uso: python tools/pv3_2_catalog_patch2.py sd00a sd03b
Idempotente por id: pula quem ja tem mapMobile.
Run: (cwd = repo root)
"""
import json
import shutil
import subprocess
import sys

IDS = sys.argv[1:] or ['sd03b']
AR = 'public/assets/data/arenas.json'
GJ = 'public/game.js'
shutil.copy2(AR, AR + '.bak_pv32d')
shutil.copy2(GJ, GJ + '.bak_pv32d')

a = open(AR, 'r', encoding='utf-8', newline='').read()
sep = '\r\n' if '\r\n' in a else '\n'
added = []
for aid in IDS:
    anchor = f'{sep}   "map": "stage/arena/{aid}.json",{sep}'
    if f'"mapMobile": "stage/arena/{aid}.mobile.json"' in a:
        print(f'[skip] {aid}: mapMobile ja presente')
        continue
    assert a.count(anchor) == 1, f'{aid}: ancora com {a.count(anchor)} ocorrencias'
    new = (f'{sep}   "map": "stage/arena/{aid}.json",{sep}'
           f'   "mapMobile": "stage/arena/{aid}.mobile.json",{sep}')
    a = a.replace(anchor, new, 1)
    added.append(aid)
open(AR, 'w', encoding='utf-8', newline='').write(a)

d = json.load(open(AR, encoding='utf-8'))
for aid in IDS:
    e = next(x for x in d['arenas'] if x['id'] == aid)
    assert e.get('mapMobile') == f'stage/arena/{aid}.mobile.json', f'{aid}: {e.get("mapMobile")}'
print(f'[ok] arenas.json: mapMobile ok para {IDS} (adicionados agora: {added}, total arenas: {len(d["arenas"])})')

g = open(GJ, 'r', encoding='utf-8', newline='').read()
old = 'fetch(`assets/${mapAsset}?v=10`)'
assert g.count(old) == 1, f'ancora fetch v=10: {g.count(old)}'
g = g.replace(old, 'fetch(`assets/${mapAsset}?v=11`)', 1)
open(GJ, 'w', encoding='utf-8', newline='').write(g)
print('[ok] game.js: fetch do mapa ?v=10 -> ?v=11')

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
