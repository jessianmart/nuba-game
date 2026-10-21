"""Registra a Vila Konoha (sa00z) no catalogo arenas.json — 9a arena, BR-ready.
Convencoes espelhadas do sd00a (hint de radius do build_arena: 140m).
Run: python tools/add_sa00z_arena.py   (cwd = repo root)
"""
import shutil

P = 'public/assets/data/arenas.json'
shutil.copy2(P, P + '.bak_vila')
s = open(P, 'r', encoding='utf-8', newline='').read()

ANCHOR = '"meshes": 122\r\n  },'
assert s.count(ANCHOR) == 1, 'ancora sd00a (meshes 122) nao encontrada'

ENTRY = '"meshes": 122\r\n  },\r\n  {\r\n' \
        '   "id": "sa00z",\r\n' \
        '   "area": "AREA_KONOHA_ACT",\r\n' \
        '   "label": "Vila Oculta da Folha (Konoha)",\r\n' \
        '   "short": "Vila",\r\n' \
        '   "shape": "box",\r\n' \
        '   "radius": 140,\r\n' \
        '   "cameraLimit": 146,\r\n' \
        '   "playerLimit": 148,\r\n' \
        '   "sanctuaryBlue": {\r\n' \
        '    "x": -95,\r\n' \
        '    "z": -95\r\n' \
        '   },\r\n' \
        '   "sanctuaryRed": {\r\n' \
        '    "x": 95,\r\n' \
        '    "z": 95\r\n' \
        '   },\r\n' \
        '   "bounds": {\r\n' \
        '    "minX": -140,\r\n' \
        '    "maxX": 140,\r\n' \
        '    "minZ": -140,\r\n' \
        '    "maxZ": 140\r\n' \
        '   },\r\n' \
        '   "lighting": {\r\n' \
        '    "ambient": "0xffffff",\r\n' \
        '    "ambientIntensity": 0.4,\r\n' \
        '    "directional": "0xfff6e8",\r\n' \
        '    "dirIntensity": 1.7,\r\n' \
        '    "hemiIntensity": 1.4\r\n' \
        '   },\r\n' \
        '   "built": true,\r\n' \
        '   "map": "stage/arena/sa00z.json",\r\n' \
        '   "mesh": "assets/stage/arena/sa00z.json",\r\n' \
        '   "verts": 162992,\r\n' \
        '   "tris": 128573,\r\n' \
        '   "meshes": 261\r\n' \
        '  },'

s = s.replace(ANCHOR, ENTRY, 1)
open(P, 'w', encoding='utf-8', newline='').write(s)
import json  # noqa: E402
data = json.load(open(P, encoding='utf-8'))
ids = [a['id'] for a in data['arenas']]
assert 'sa00z' in ids and len(ids) == 9, ids
print('[ok] arenas.json: sa00z registrado — catalogo:', ids)
