import json, math

d = json.load(open('public/assets/stage/arena/sd03b.json'))

# Camera is at (0, 48, 85) looking at (0, 4, 0)
# Scale is 0.022. So in stage coordinates:
# Cam pos = (0 / 0.022, 48 / 0.022, 85 / 0.022) = (0, 2181.8, 3863.6)
# Look at = (0, 181.8, 0)

# Check which mesh has triangles that cross near X=[-1000, 0], Y=[0, 1000], Z=[0, 3000]
print(f"Total meshes: {len(d['meshes'])}")
for i, m in enumerate(d['meshes']):
    p = m['positions']
    xs, ys, zs = p[0::3], p[1::3], p[2::3]
    # Check if this mesh has a triangle with one vertex near (0,0,0) and another far away
    max_d = 0
    min_d = 999999
    for j in range(len(xs)):
        dist = math.hypot(xs[j], zs[j])
        if dist > max_d: max_d = dist
        if dist < min_d: min_d = dist
    # If a mesh has vertices near center (dist < 400) and also far (dist > 2500)
    if min_d < 400 and max_d > 2500:
        print(f"STRETCH MESH {i}: {m['name']} min_dist={min_d:.1f} max_dist={max_d:.1f} tex={m.get('texture')}")
