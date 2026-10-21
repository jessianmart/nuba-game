import json

with open('public/assets/stage/arena/sd03b.json') as f:
    d = json.load(f)

for i, m in enumerate(d['meshes']):
    p = m['positions']
    xs, ys, zs = p[0::3], p[1::3], p[2::3]
    for j in range(len(xs)):
        if xs[j] < -2000 and ys[j] > 200 and zs[j] > 0 and zs[j] < 4000:
            print(f'Match mesh {i}: {m[" name\]} tex={m.get(\texture\)} pt=({xs[j]}, {ys[j]}, {zs[j]})')
 break
