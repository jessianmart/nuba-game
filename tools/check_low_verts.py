import json

d = json.load(open('public/assets/stage/arena/sd03b.json'))
for i, m in enumerate(d['meshes']):
    p = m['positions']
    nv = len(p) // 3
    if nv <= 10:
        print(f"{i}: {m['name']} ({nv} verts) pos={p}")
