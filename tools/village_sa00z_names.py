"""Dump completo dos nomes de mesh do sa00z (candidato a vila Konoha) + bounds por grupo.
Run: python tools/village_sa00z_names.py   (cwd = repo root)
"""
import os
import sys

sys.path.insert(0, os.getcwd())
import tools.build_arena as ba  # noqa: E402

data = ba.build('sa00z', textures=False, catalog_only=True)
names = [m['name'] for m in data['meshes']]
print(f'total meshes: {len(names)}  verts={data.get("verts")} tris={data.get("tris")}')
b = data['bounds']
sc = data.get('scale', 0.022)
print(f"bounds(m): x={(b['max'][0]-b['min'][0])*sc:.1f} y={(b['max'][1]-b['min'][1])*sc:.1f} z={(b['max'][2]-b['min'][2])*sc:.1f}")

tree_like = [n for n in names if n.startswith(('ki', 'ha'))]
others = [n for n in names if not n.startswith(('ki', 'ha'))]
print(f'\n== ARVORES/FOLHAS (ki/ha): {len(tree_like)} ==')
print(f'== DEMAIS ESTRUTURAS: {len(others)} ==')
for n in others:
    # posicao central do mesh em metros
    m = next(mm for mm in data['meshes'] if mm['name'] == n)
    pos = m['positions']
    xs = pos[0::3]
    ys = pos[1::3]
    zs = pos[2::3]
    if xs:
        cx = (max(xs) + min(xs)) / 2 * sc
        cy = (max(ys) + min(ys)) / 2 * sc
        cz = (max(zs) + min(zs)) / 2 * sc
        nv = len(xs)
        print(f'  {n:36} v={nv:6}  centro=({cx:7.1f}, {cy:6.1f}, {cz:7.1f})')
print('\nSA00Z NAMES DONE')
