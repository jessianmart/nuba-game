import json, math

d = json.load(open('public/assets/stage/arena/sd01a.json'))
scale = d.get('scale', 0.022)

# Check all meshes between X=[-35, 75] and Z=[-75, 25] at Y > 2.0
# to ensure there is NO solid rock on top of the water!
obstructions = []
for m in d['meshes']:
    name = m['name'].lower()
    if 'water' in name or 'river' in name: continue
    xs = [x * scale for x in m['positions'][0::3]]
    ys = [y * scale for y in m['positions'][1::3]]
    zs = [z * scale for z in m['positions'][2::3]]
    for i in range(len(ys)):
        if -30 <= xs[i] <= 70 and -70 <= zs[i] <= 20 and 0.5 <= ys[i] <= 5.0:
            obstructions.append((m['name'], xs[i], ys[i], zs[i]))

print(f"Obstructions in water fighting zone: {len(obstructions)}")
if obstructions:
    print("Sample:", obstructions[:5])
else:
    print("100% CLEAR FIGHTING ZONE ON WATER!")
