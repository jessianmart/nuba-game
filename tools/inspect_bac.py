import json

d = json.load(open('public/assets/stage/arena/sd03b.json'))
m = [x for x in d['meshes'] if x['name'] == 'sd03bbac001_sub0'][0]
p = m['positions']
print(f"sd03bbac001_sub0 total verts: {len(p)//3}")
near_center = []
for i in range(0, len(p), 3):
    x, y, z = p[i], p[i+1], p[i+2]
    if x*x + z*z < 500*500:
        near_center.append((i//3, x, y, z))
print("Vertices near center:", near_center)
