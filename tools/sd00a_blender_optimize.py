# -*- coding: utf-8 -*-
"""PV3.2 — Otimizacao da arena sd00a (campo de treino, arena DEFAULT do jogo)
para mobile via Blender headless. Mesmo pipeline da vila (sa00z): join por
textura + decimate por classe, round-trip fiel ao schema do loader.

Diferenca do sd00a: os nomes dos meshes sao 'sd00aobj008_sub0' (classe embutida
DEPOIS do id da arena), nao 'obj...' — a classe e extraida do BASENAME DA TEXTURA,
que e o criterio real de agrupamento (cada grupo tem 1 textura -> 1 classe).

Run: blender.exe -b --python tools/sd00a_blender_optimize.py   (cwd = repo root)
Saida: public/assets/stage/arena/sd00a.mobile.json + sd00a_optimize_report.json
"""
import bpy  # noqa: F401
import json
import os
import re
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sd00a.json')
OUT = os.path.join(ROOT, 'public', 'assets', 'stage', 'arena', 'sd00a.mobile.json')
REPORT = os.path.join(ROOT, 'sd00a_optimize_report.json')

t0 = time.time()

# ---------- razao de decimate por classe (calibrada pelo censo real) ----------
# sd00a: 122 meshes / 40k tris -> obj 24934 tris (62%), flo 8073, ha 3654,
# sd 2200, bac 1244. Objetos dominam -> ratio moderado para nao destruir
# legibilidade do cenario; folhagem/background sao fill distante.
RATIOS = [
    (('river',), 0.80),          # agua: superficie fina, corte agressivo abre buraco
    (('iwa',), 0.65),            # rochas: identidade
    (('sd',), 0.60),             # estrutura da arena
    (('obj',), 0.58),            # objetos do cenario: maior massa de tris
    (('ha',), 0.50),             # chao/terra
    (('eda',), 0.50),            # galhos
    (('ki',), 0.45),             # arvores
    (('flo', 'bac'), 0.45),      # folhagem + background: fill distante
]


def class_of(tex_path):
    b = os.path.basename(tex_path).rsplit('.', 1)[0]
    if b.startswith('sd00a'):
        b = b[5:].lstrip('_')
    m = re.match(r'^([a-z]+)', b)
    return (m.group(1) if m else b) or 'sd'


def ratio_for(tex_path):
    c = class_of(tex_path)
    for prefixes, r in RATIOS:
        if c.startswith(prefixes):
            return r
    return 0.55                   # default: artefatos diversos


# ---------- carrega e agrupa por textura ----------
with open(SRC, 'r', encoding='utf-8') as f:
    data = json.load(f)
groups = {}
for m in data['meshes']:
    groups.setdefault(m['texture'], []).append(m)
print(f'[sd00a-opt] fonte: {len(data["meshes"])} meshes / {len(groups)} grupos de textura')

# cena limpa
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

out_meshes = []
tris_in = 0
tris_out = 0

for tex, members in groups.items():
    first = members[0]
    r = ratio_for(tex)
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
    # UV pelos loops REAIS do mesh (from_pydata pode descartar degeneradas)
    for lp in me.loops:
        uv_layer.data[lp.index].uv = all_uv[lp.vertex_index]
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

    # modifier_apply pode RECRIAR o datablock — rebuscar pelo objeto
    me = obj.data
    uv_layer = me.uv_layers.active
    me.calc_loop_triangles()
    out_idx = []
    verts = me.vertices
    tris = [tuple(me.loops[tri.loops[i]].vertex_index for i in range(3)) for tri in me.loop_triangles]
    positions, normals, uvs = [], [], []
    seen = set()
    for tri in me.loop_triangles:
        for i in range(3):
            lp = me.loops[tri.loops[i]]
            vid = lp.vertex_index
            if vid in seen:
                continue
            seen.add(vid)
            positions.append(verts[vid].co)
            normals.append(verts[vid].normal)
            uvs.append(uv_layer.data[lp.index].uv.copy())
    for t in tris:
        out_idx.extend(t)
    tris_out += len(tris)
    stem = os.path.basename(tex)[:-4]
    out_meshes.append({
        'name': f'sd00am_{stem}',
        'mat_cmap': first['mat_cmap'],
        'texture': first['texture'],
        'positions': [round(c, 3) for v in positions for c in (v.x, -v.z, v.y)],
        'normals': [round(c, 4) for v in normals for c in (v.x, -v.z, v.y)],
        'uvs': [round(c, 4) for v in uvs for c in (v.x, v.y)],
        'indices': out_idx,
    })
    print(f'  {class_of(tex):6} {tex[-28:]:28} {len(members):3} meshes -> 1  ratio {r:.2f}  tris {len(tris)}')

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
data_out['note'] = 'mobile-optimized sd00a (Blender 5.2: join por textura + decimate)'
with open(OUT, 'w', encoding='utf-8') as f:
    json.dump(data_out, f, ensure_ascii=False, separators=(',', ':'))
dst_size = os.path.getsize(OUT)

report = {
    'src': {'meshes': len(data['meshes']), 'verts': data['verts'], 'tris': data['tris'],
            'bytes': src_size, 'mb': round(src_size / 1048576, 2)},
    'out': {'meshes': len(out_meshes), 'verts': data_out['verts'], 'tris': data_out['tris'],
            'bytes': dst_size, 'mb': round(dst_size / 1048576, 2)},
    'reducao_meshes': f"{100 - len(out_meshes) * 100 / len(data['meshes']):.0f}%",
    'reducao_tris': f"{100 - data_out['tris'] * 100 / data['tris']:.0f}%",
    'reducao_bytes': f"{100 - dst_size * 100 / src_size:.0f}%",
    'classes': sorted({class_of(t) for t in groups}),
    'segundos': round(time.time() - t0, 1),
}
with open(REPORT, 'w', encoding='utf-8') as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(f'[sd00a-opt] {len(data["meshes"])} -> {len(out_meshes)} meshes | '
      f'{data["tris"]} -> {data_out["tris"]} tris | {src_size/1048576:.2f} -> {dst_size/1048576:.2f} MB | '
      f'{report["segundos"]}s')
print('SD00A OPT DONE')
