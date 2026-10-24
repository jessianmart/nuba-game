# -*- coding: utf-8 -*-
"""W-REAL F2: catalogo por model -> submeshes (name, verts, texture).
Detecta texturas shadow/blur (invisiveis em additive) e mostra o par
modelo->textura pra montar o mapa REAL por skill."""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

d = json.load(io.open('public/assets/skills/skill_vfx.json', encoding='utf-8'))

BAD = ('shadow', 'blur', 'dst', 'dark')

print('=== CATALOGO: grupo/model -> [subs] ===')
for grp in sorted(d.keys()):
    models = d[grp].get('models', {}) if isinstance(d[grp], dict) else {}
    if not models:
        continue
    for name in sorted(models.keys()):
        subs = models[name]
        if not isinstance(subs, list):
            continue
        parts = []
        for s in subs:
            if not isinstance(s, dict):
                continue
            v = len(s.get('positions', [])) // 3
            tex = (s.get('texture') or '?').split('/')[-1]
            flag = ' <<SHADOW' if any(b in tex.lower() for b in BAD) else ''
            parts.append(f"{s.get('name', '?')[:28]}:{v}v:{tex}{flag}")
        print(f'{grp}/{name}:')
        for pr in parts:
            print(f'    {pr}')
