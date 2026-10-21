import json
with open("public/assets/stage/stage_3d.json") as f:
    stg = json.load(f)

for m in stg["meshes"]:
    if any(k in m["name"] for k in ("com001", "sd01bobj001", "sd01bobj002", "sd01bobj003", "sd01bobj004", "sd01bobj006", "fire")):
        xs = m["positions"][0::3]
        ys = m["positions"][1::3]
        zs = m["positions"][2::3]
        print(f"{m['name']:25s} x=[{min(xs):6.1f},{max(xs):6.1f}] y=[{min(ys):6.1f},{max(ys):6.1f}] z=[{min(zs):6.1f},{max(zs):6.1f}] tex={m.get('texture')}")
