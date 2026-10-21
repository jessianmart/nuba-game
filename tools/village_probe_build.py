"""Identifica a vila Konoha entre os chunks candidatos via build_arena.build(catalog_only=True, textures=False).
Disk-safe: NAO decodifica/escreve texturas. So imprime bounds/verts/tris/nomes.
Run: python tools/village_probe_build.py   (cwd = repo root)
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
import tools.build_arena as ba  # noqa: E402

CANDIDATES = ['sm00a', 'sp00', 'sa00z', 'sk00a']

for sid in CANDIDATES:
    print('=' * 24, sid)
    try:
        data = ba.build(sid, textures=False, catalog_only=True)
    except Exception as e:
        print('  BUILD ERR:', repr(e))
        continue
    b = data.get('bounds')
    if b:
        ext = [round((b['max'][i] - b['min'][i]) * data.get('scale', 0.022), 1) for i in range(3)]
        print(f"  bounds(m): x={ext[0]} y={ext[1]} z={ext[2]}  scale={data.get('scale')}")
        print(f"  raw min={b['min']} max={b['max']}")
    print(f"  verts={data.get('verts')} tris={data.get('tris')} meshes={len(data.get('meshes', []))}")
    names = [m['name'] for m in data['meshes']]
    fams = Counter()
    for n in names:
        fams[n.replace('-', '_').split('_')[0][:20]] += 1
    print('  prefixos:', fams.most_common(18))
    print('  amostra :', names[:24])
print('\nPROBE DONE')
