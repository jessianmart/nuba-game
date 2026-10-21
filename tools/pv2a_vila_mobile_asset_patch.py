"""PV2-A: variante mobile do arena sa00z — campo mapMobile + branch por device no loader.
Desktop continua no JSON full; __DEVICE.isMobile carrega o otimizado (Blender).
Run: python pv2a_vila_mobile_asset_patch.py   (cwd = repo root)
"""
import shutil

# ---------- arenas.json ----------
AJ = 'public/assets/data/arenas.json'
shutil.copy2(AJ, AJ + '.bak_pv2a')
s = open(AJ, 'r', encoding='utf-8', newline='').read()

A_MAP = '"map": "stage/arena/sa00z.json",'
if 'mapMobile' in s:
    print('[skip] arenas.json: mapMobile ja presente')
else:
    assert s.count(A_MAP) == 1, 'ancora map sa00z'
    s = s.replace(A_MAP, '   "mapMobile": "stage/arena/sa00z.mobile.json",\r\n' + A_MAP, 1)
    open(AJ, 'w', encoding='utf-8', newline='').write(s)
    print('[ok] arenas.json: mapMobile registrado no sa00z')

# ---------- game.js ----------
GJ = 'public/game.js'
shutil.copy2(GJ, GJ + '.bak_pv2a')
g = open(GJ, 'r', encoding='utf-8', newline='').read()

ANCHOR = "  // Load the arena map from assets/${entry.map}\n  if (entry.map) {\n    try {\n      const res = await fetch(`assets/${entry.map}?v=8`).then(r => r.json());"
assert g.count(ANCHOR) == 1, 'ancora loader game.js'
NEW = "  // Load the arena map (mobile carrega a variante otimizada do Blender)\n  const mapAsset = (entry.mapMobile && window.__DEVICE && window.__DEVICE.isMobile) ? entry.mapMobile : entry.map;\n  if (mapAsset) {\n    try {\n      const res = await fetch(`assets/${mapAsset}?v=9`).then(r => r.json());"
g = g.replace(ANCHOR, NEW, 1)
# cache-bust v9: catalogo arenas.json agora tem mapMobile — navegador com cache v8
# ficaria sem a vila
CAT = "fetch('assets/data/arenas.json?v=8')"
assert g.count(CAT) == 1, 'ancora fetch arenas.json'
g = g.replace(CAT, "fetch('assets/data/arenas.json?v=9')", 1)
open(GJ, 'w', encoding='utf-8', newline='').write(g)
print('[ok] game.js: branch mapMobile + cache-bust arenas v9')

import subprocess  # noqa: E402
r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')

import json  # noqa: E402
d = json.load(open(AJ, encoding='utf-8'))
e = next(a for a in d['arenas'] if a['id'] == 'sa00z')
assert e.get('mapMobile') == 'stage/arena/sa00z.mobile.json', e
print('[ok] sa00z:', e['map'], '+', e['mapMobile'])
print('PV2A DONE')
