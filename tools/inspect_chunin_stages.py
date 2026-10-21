import json, sys

sys.stdout.reconfigure(encoding='utf-8')

for aid in ['sd04a', 'sd03b', 'sd01b']:
    p = f'public/assets/stage/arena/{aid}.json'
    d = json.load(open(p, 'r', encoding='utf-8'))
    names = [m.get('name', '') for m in d.get('meshes', [])]
    texs = [m.get('texture', '') for m in d.get('meshes', [])]
    print(f'=== {aid} ===')
    print('Scale:', d.get('scale'))
    print('Mesh count:', len(names))
    print('First 10 meshes:', names[:10])
    print('First 10 textures:', texs[:10])
    
    # Check mesh bounding box
    xs, ys, zs = [], [], []
    for m in d.get('meshes', []):
        pos = m.get('positions', [])
        for i in range(0, len(pos), 3):
            xs.append(pos[i])
            ys.append(pos[i+1])
            zs.append(pos[i+2])
    if xs:
        scale = d.get('scale', 0.022)
        print(f'World bounds at scale {scale}:')
        print(f'  X: [{min(xs)*scale:.1f}, {max(xs)*scale:.1f}]')
        print(f'  Y: [{min(ys)*scale:.1f}, {max(ys)*scale:.1f}]')
        print(f'  Z: [{min(zs)*scale:.1f}, {max(zs)*scale:.1f}]')
