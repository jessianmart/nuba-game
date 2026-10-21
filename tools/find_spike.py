import json

with open('public/assets/stage/arena/sd03b.json') as f:
    d = json.load(f)

for i, m in enumerate(d['meshes']):
    p = m['positions']
    xs, ys, zs = p[0::3], p[1::3], p[2::3]
    if len(xs) == 0: continue
    has_origin = any(xs[j] == 0.0 and ys[j] == 0.0 and zs[j] == 0.0 for j in range(len(xs)))
    extent_x = max(xs) - min(xs)
    extent_z = max(zs) - min(zs)
    name = m.get('name', '')
    tex = m.get('texture', '')
    if has_origin and (extent_x > 1000 or extent_z > 1000):
        print('Suspect origin stretch:', i, name, tex, 'verts:', len(xs))
    if 'shadow' in name.lower() or 'kage' in name.lower():
        print('Shadow mesh:', i, name, tex)
    if not tex:
        print('No texture mesh:', i, name, 'verts:', len(xs))
