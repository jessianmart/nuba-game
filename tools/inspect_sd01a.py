import json

with open('public/assets/stage/arena/sd01a.json') as f:
    d = json.load(f)

print(f"Total meshes in sd01a: {len(d['meshes'])}")
scale = d.get('scale', 0.022)
print(f"Scale: {scale}")

for m in d['meshes']:
    name = m['name'].lower()
    xs = m['positions'][0::3]
    ys = m['positions'][1::3]
    zs = m['positions'][2::3]
    if any(k in name for k in ['flo', 'wat', 'riv', 'gnd', 'sd01a', 'obj', 'bld']):
        print(f"{m['name']}: {len(ys)}v, X:[{min(xs)*scale:.1f}, {max(xs)*scale:.1f}], Y:[{min(ys)*scale:.1f}, {max(ys)*scale:.1f}], Z:[{min(zs)*scale:.1f}, {max(zs)*scale:.1f}], tex={m.get('texture')}")
