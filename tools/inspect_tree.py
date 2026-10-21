import json

with open('public/assets/stage/arena/sd03b.json') as f:
    d = json.load(f)

for i, m in enumerate(d['meshes']):
    p = m['positions']
    name = m.get('name', '')
    tex = m.get('texture', '')
    if 'ki00' in name:
        xs, ys, zs = p[0::3], p[1::3], p[2::3]
        print(f"Tree mesh {i}: {name} tex={tex} verts={len(xs)} X:[{min(xs)}, {max(xs)}] Y:[{min(ys)}, {max(ys)}] Z:[{min(zs)}, {max(zs)}]")
