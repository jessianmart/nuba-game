"""PV3.2-B — registra o sd00a.mobile.json no catalogo e bumpa o fetch do mapa.
O fetch de dados (`assets/${mapAsset}?v=9`) NAO e coberto pelo auto-cache-buster
do index.html -> bump manual obrigatorio, senao o browser do usuario serve o
JSON velho do cache.
Run: python tools/pv3_2_catalog_patch.py   (cwd = repo root)
"""
import json
import shutil
import subprocess

AR = 'public/assets/data/arenas.json'
GJ = 'public/game.js'
shutil.copy2(AR, AR + '.bak_pv32')
shutil.copy2(GJ, GJ + '.bak_pv32')

a = open(AR, 'r', encoding='utf-8', newline='').read()
sep = '\r\n' if '\r\n' in a else '\n'

anchor = f'{sep}   "map": "stage/arena/sd00a.json",{sep}'
assert a.count(anchor) == 1, f'ancora map sd00a: {a.count(anchor)}'
new = f'{sep}   "map": "stage/arena/sd00a.json",{sep}   "mapMobile": "stage/arena/sd00a.mobile.json",{sep}'
a = a.replace(anchor, new, 1)
open(AR, 'w', encoding='utf-8', newline='').write(a)

# valida que o JSON continua parseavel e a entrada ganhou mapMobile
d = json.load(open(AR, encoding='utf-8'))
e = next(x for x in d['arenas'] if x['id'] == 'sd00a')
assert e.get('mapMobile') == 'stage/arena/sd00a.mobile.json', e.get('mapMobile')
print(f'[ok] arenas.json: sd00a.mapMobile={e["mapMobile"]} (arenas: {len(d["arenas"])})')

g = open(GJ, 'r', encoding='utf-8', newline='').read()
old = 'fetch(`assets/${mapAsset}?v=9`)'
assert g.count(old) == 1, f'ancora fetch v=9: {g.count(old)}'
g = g.replace(old, 'fetch(`assets/${mapAsset}?v=10`)', 1)
open(GJ, 'w', encoding='utf-8', newline='').write(g)
print('[ok] game.js: fetch do mapa ?v=9 -> ?v=10')

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
print('PV3.2 CATALOG PATCH DONE')
