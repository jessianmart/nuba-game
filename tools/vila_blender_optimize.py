# -*- coding: utf-8 -*-
"""Otimizacao da Vila Konoha (sa00z) pra mobile via Blender headless.
Join por textura + decimate por classe; round-trip fiel ao schema do loader
(positions/normals/uvs flat por vertice, indices triangulado, mat_cmap preservado).
Run: blender.exe -b --python tools/vila_blender_optimize.py   (cwd = repo root)
Saida: public/assets/stage/arena/sa00z.mobile.json + vila_optimize_report.json
"""
import bpy  # noqa: F401
import json
import os
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sa00z.json')
OUT = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sa00z.mobile.json')
REPORT = os.path.join(ROOT, 'vila_optimize_report.json')

t0 = time.time()

# ---------- razao de decimate por classe de mesh ----------
RATIOS = [
    (('river', 'hasi'), 0.80),      # rio e pontes: estruturas finas
    (('hkg',), 0.75),               # monumento Hokage: manter nitido
    (('rock',), 0.65),              # paredoes: identidade, cuidado
    (('ki', 'ha'), 0.45),           # arvores/folhagem: fill distante
]


def ratio_for(name):
    for prefixes, r in RATIOS:
        if name.startswith(prefixes):
            return r
    return 0.55                       # fou/sec/obj/art/back/...


# ---------- carrega e agrupa por textura ----------
with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)
groups = {}
for m in data['meshes']:
    groups.setdefault(m['texture'], []).append(m)
print(f'[vila-opt] fonte: {len(data["meshes"])} meshes / {len(groups)} grupos de textura')

# cena limpa
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

out_meshes = []
tris_in = 0
tris_out = 0

for tex, members in groups.items():
    first = members[0]
    r = min(ratio_for(m['name']) for m in members)
    # acumula verts/faces/uvs/normais do grupo
    all_pos, all_uv, all_nrm, all_idx = [], [], [], []
    vbase = 0
    for m in members:
        p = m['positions']
        all_pos.extend((p[i], p[i + 2], -p[i + 1]) for i in range(0, len(p) - 2, 3))  # x,z,-y (convencao repo)
        all_uv.extend(tuple(m['uvs'][i:i + 2]) for i in range(0, len(m['uvs']) - 1, 2))
        nn = m['normals']
        all_nrm.extend((nn[i], nn[i + 2], -nn[i + 1]) for i in range(0, len(nn) - 2, 3))
        idx = m['indices']
        tris_in += len(idx) // 3
        all_idx.extend((idx[i] + vbase, idx[i + 1] + vbase, idx[i + 2] + vbase)
                       for i in range(0, len(idx) - 2, 3))
        vbase += len(p) // 3
    faces = [(f[0], f[1], f[2]) for f in all_idx]

    me = bpy.data.meshes.new(f'g_{os.path.basename(tex)[:-4]}')
    me.from_pydata(all_pos, [], faces)
    uv_layer = me.uv_layers.new(name='UVMap')
    # faces degeneradas podem ser descartadas pelo from_pydata: atribui pelos
    # loops REAIS do mesh (indefeso a contagem), nao por li*3+corner
    for lp in me.loops:
        uv_layer.data[lp.index].uv = all_uv[lp.vertex_index]
    # normais split originais por loop
    # normais: vertex-normais suavizadas calculadas pelo proprio Blender (API estavel;
    # split-normais customizadas mudaram de API no 4.1+ e o decimate as recalcula mesmo)
    for poly in me.polygons:
        poly.use_smooth = True

    obj = bpy.data.objects.new(f'g_{os.path.basename(tex)[:-4]}', me)
    bpy.context.collection.objects.link(obj)

    if r < 1.0:
        bpy.context.view_layer.objects.active = obj
        mod = obj.modifiers.new(name='decim', type='DECIMATE')
        mod.decimate_type = 'COLLAPSE'
        mod.ratio = r
        bpy.ops.object.modifier_apply(modifier=mod.name)

    # exporta de volta: modifier_apply pode RECRIAR o datablock — rebuscar pelo objeto
    me = obj.data
    uv_layer = me.uv_layers.active
    me.calc_loop_triangles()
    out_idx = []
    verts = me.vertices
    tris = [tuple(me.loops[tri.loops[i]].vertex_index for i in range(3)) for tri in me.loop_triangles]
    positions, normals, uvs = [], [], []
    first_loop_of_vert = {}
    for ti, tri in enumerate(me.loop_triangles):
        for i in range(3):
            lp = me.loops[tri.loops[i]]
            vid = lp.vertex_index
            if vid in first_loop_of_vert:
                continue
            first_loop_of_vert[vid] = vid
            positions.append(verts[vid].co)
            normals.append(verts[vid].normal)
            uvs.append(uv_layer.data[lp.index].uv.copy())
    for t in tris:
        out_idx.extend(t)
    tris_out += len(tris)
    stem = os.path.basename(tex)[:-4]
    out_meshes.append({
        'name': f'sa00zm_{stem}',
        'mat_cmap': first['mat_cmap'],
        'texture': first['texture'],
        'positions': [round(c, 3) for v in positions for c in (v.x, -v.z, v.y)],
        'normals': [round(c, 4) for v in normals for c in (v.x, -v.z, v.y)],
        'uvs': [round(c, 4) for v in uvs for c in (v.x, v.y)],
        'indices': out_idx,
    })
    print(f'  {tex:34} {len(members):3} meshes -> 1  ratio {r:.2f}  tris {len(tris)}')

# bounds honestos
mn = [1e9] * 3
mx = [-1e9] * 3
for m in out_meshes:
    p = m['positions']
    for i in range(0, len(p), 3):
        for k in range(3):
            v = p[i + k]
            if v < mn[k]:
                mn[k] = v
            if v > mx[k]:
                mx[k] = v

src_size = os.path.getsize(SRC)
data_out = dict(data)
data_out['meshes'] = out_meshes
data_out['verts'] = sum(len(m['positions']) // 3 for m in out_meshes)
data_out['tris'] = sum(len(m['indices']) // 3 for m in out_meshes)
data_out['bounds'] = {'min': [round(c, 3) for c in mn], 'max': [round(c, 3) for c in mx]}
data_out['note'] = 'mobile-optimized (Blender 5.2: join por textura + decimate)'
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(data_out, f, ensure_ascii=False, separators=(',', ':'))
dst_size = os.path.getsize(OUT)

report = {
    'src': {'meshes': len(data['meshes']), 'verts': data['verts'], 'tris': data['tris'], 'bytes': src_size},
    'out': {'meshes': len(out_meshes), 'verts': data_out['verts'], 'tris': data_out['tris'], 'bytes': dst_size},
    'reducao_meshes': f"{100 - len(data_out['meshes']) * 100 / len(data['meshes']):.0f}%",
    'reducao_tris': f"{100 - data_out['tris'] * 100 / data['tris']:.0f}%",
    'reducao_bytes': f"{100 - dst_size * 100 / src_size:.0f}%",
    'segundos': round(time.time() - t0, 1),
}
with open(REPORT, 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print('[vila-opt] ' + json.dumps(report, ensure_ascii=False))
print('VILA OPTIMIZE DONE')
