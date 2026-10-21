import json

with open('public/assets/stage/arena/sd03b.json') as f:
    d = json.load(f)

for i, m in enumerate(d['meshes']):
    name = m.get('name', '')
    if 'trans_obj' in name or 'wallroot' in name:
        p = m['positions']
        xs, ys, zs = p[0::3], p[1::3], p[2::3]
        print(f"{i}: {name} tex={m.get('texture')} verts={len(xs)} X:[{min(xs)}, {max(xs)}] Y:[{min(ys)}, {max(ys)}] Z:[{min(zs)}, {max(zs)}]")
