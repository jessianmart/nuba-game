# -*- coding: utf-8 -*-
"""SPP Blender audit: orientacao dos modelos VFX extraidos (skill_vfx.json).
Headless: blender.exe -b --python tools/spp_blender_audit.py
Saída: spp_blender_report.json (bbox/eixo/forward/suggestedYaw por modelo)."""
import bpy, json, os, math

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VFX = os.path.join(ROOT, 'public', 'assets', 'skills', 'skill_vfx.json')
OUT_JSON = os.path.join(ROOT, 'spp_blender_report.json')

SKILL_VFX_MAP = {
    '1nrt': ['rasengan', 'smoke', '1efc_log01', 'giant_rasengan'],
    '1ssk': ['chidori_spark', 'fireball', '1sskeff1_sharin01', '1sskeff1_aura01'],
    '1skr': ['shatter', 'heal_chakra', '1efc_log01', 'shatter'],
    '1kks': ['raikiri_spark', 'water_dragon', 'raikiri_spark', '1kkseff1_sharin01'],
    '1roc': ['whirlwind', 'air_tornado', 'leaf_flurry', 'air_tornado'],
    '1itc': ['amaterasu_flame', 'crow_smoke', 'crow_smoke', 'amaterasu_flame'],
    '1gar': ['1gareff1_bd_snd02', '1gareff1_hnd01_body', 'sand_dust', '1gareff1_snd15'],
    '1hnt': ['palms_rotation', 'lion_chakra', 'palms_rotation', 'lion_chakra'],
    '1nej': ['kaiten_dome', 'air_palm', 'kaiten_dome', 'kaiten_dome'],
    '1jry': ['toad_fire', '1jryeff01', '1efc_log01', 'chou_rasengan'],
}

def build_mesh(entry):
    me = bpy.data.meshes.new(entry.get('name', 'vfx'))
    pos = entry.get('positions') or []
    idx = entry.get('indices') or []
    verts = [(pos[i], pos[i+2], -pos[i+1]) for i in range(0, len(pos) - 2, 3)]
    faces = [(idx[i], idx[i+1], idx[i+2]) for i in range(0, len(idx) - 2, 3)]
    me.from_pydata(verts, [], faces)
    me.validate()
    ob = bpy.data.objects.new(me.name, me)
    bpy.context.collection.objects.link(ob)
    return ob

def analyze(ob):
    ob.update_tag()
    n = max(1, len(ob.data.vertices))
    sx = sy = sz = 0.0
    minx = miny = minz = 1e9
    maxx = maxy = maxz = -1e9
    for v in ob.data.vertices:
        w = ob.matrix_world @ v.co
        sx += w.x; sy += w.y; sz += w.z
        minx = min(minx, w.x); maxx = max(maxx, w.x)
        miny = min(miny, w.y); maxy = max(maxy, w.y)
        minz = min(minz, w.z); maxz = max(maxz, w.z)
    cen = (sx/n, sy/n, sz/n)
    dims = (round(maxx-minx, 3), round(maxy-miny, 3), round(maxz-minz, 3))
    axis = ['X', 'Y', 'Z'][max(range(3), key=lambda i: dims[i])]
    off = math.hypot(cen[0], cen[1])
    yaw = math.atan2(-cen[0], -cen[1]) if off > 0.05 else 0.0
    return {'dims': dims, 'principalAxis': axis, 'centroid': (round(cen[0], 3), round(cen[1], 3), round(cen[2], 3)),
            'offsetMag': round(off, 3), 'suggestedYawRad': round(yaw, 3), 'directional': off > 0.05}

data = json.load(open(VFX, encoding='utf-8'))
report = {'models': {}, 'notes': 'suggestedYawRad: rotacao Y extra por modelo p/ alinhar ao facing do caster; directional=false = radial/simetrico'}
seen = set()

for hero, models in SKILL_VFX_MAP.items():
    hdef = data.get(hero) or {}
    hmodels = hdef.get('models') or {}
    for mname in models:
        key = hero + '/' + mname
        if key in seen or mname not in hmodels:
            continue
        seen.add(key)
        entries = hmodels[mname]
        if not isinstance(entries, list):
            entries = [entries]
        obs = [build_mesh(e) for e in entries if e.get('positions')]
        if not obs:
            continue
        maxdims = [0.0, 0.0, 0.0]
        best = None
        for ob in obs:
            a = analyze(ob)
            for i in range(3):
                maxdims[i] = max(maxdims[i], a['dims'][i])
            if best is None or a['offsetMag'] > best['offsetMag']:
                best = a
        report['models'][key] = {
            'nMeshes': len(obs),
            'dims': [round(d, 3) for d in maxdims],
            'principalAxis': best['principalAxis'],
            'mostOffset': {'centroid': best['centroid'], 'offsetMag': best['offsetMag'], 'suggestedYawRad': best['suggestedYawRad']},
            'directional': best['offsetMag'] > 0.05,
        }

json.dump(report, open(OUT_JSON, 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
directional = dict((k, v['mostOffset']) for k, v in report['models'].items() if v['directional'])
print('SPP BLENDER AUDIT:', len(report['models']), 'modelos |', len(directional), 'directionais')
print(json.dumps(directional, indent=1))
