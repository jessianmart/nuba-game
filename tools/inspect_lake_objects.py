import json

d = json.load(open('public/assets/stage/arena/sd01a.json'))
scale = d.get('scale', 0.022)

for m in d['meshes']:
    name = m['name']
    if 'obj00' in name or 'sd01a01' in name or 'sd01a06' in name:
        xs = [x * scale for x in m['positions'][0::3]]
        ys = [y * scale for y in m['positions'][1::3]]
        zs = [z * scale for z in m['positions'][2::3]]
        print(f"{name}: {len(ys)}v, X:[{min(xs):.1f},{max(xs):.1f}] Y:[{min(ys):.1f},{max(ys):.1f}] Z:[{min(zs):.1f},{max(zs):.1f}] tex={m.get('texture')}")
