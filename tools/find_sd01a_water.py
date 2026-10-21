import json

with open('public/assets/stage/arena/sd01a.json') as f:
    d = json.load(f)

scale = d.get('scale', 0.022)
for m in d['meshes']:
    name = m['name'].lower()
    tex = (m.get('texture') or '').lower()
    if 'wat' in name or 'wat' in tex or 'riv' in name or 'sea' in name:
        ys = [y * scale for y in m['positions'][1::3]]
        xs = [x * scale for x in m['positions'][0::3]]
        zs = [z * scale for z in m['positions'][2::3]]
        print(f"Water/River: {m['name']} ({len(ys)}v) X:[{min(xs):.1f},{max(xs):.1f}] Y:[{min(ys):.1f},{max(ys):.1f}] Z:[{min(zs):.1f},{max(zs):.1f}] tex={m.get('texture')}")
