import json
import os

with open("public/assets/stage/arena/sd03b.json", "r", encoding="utf-8") as f:
    stg = json.load(f)

print(f"sd03b: {len(stg['meshes'])} meshes")
missing = []
for m in stg["meshes"]:
    tex = m.get("texture")
    if tex:
        p1 = os.path.join("public/assets", tex)
        p2 = os.path.join("public/assets/stage", tex)
        if not os.path.exists(p1) and not os.path.exists(p2):
            missing.append(tex)

print(f"Missing textures: {len(set(missing))}")
if missing:
    print(set(missing))
else:
    print("ALL textures for sd03b exist on disk!")
