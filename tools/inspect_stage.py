import json
import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks

with open("public/assets/stage/stage_3d.json", "r", encoding="utf-8") as f:
    stg = json.load(f)

print(f"Current stage_3d.json: {len(stg['meshes'])} submeshes, {stg['verts']} verts, {stg['tris']} tris")
for i, m in enumerate(stg["meshes"]):
    pos = m["positions"]
    xs = pos[0::3]
    ys = pos[1::3]
    zs = pos[2::3]
    uvs = m["uvs"]
    us = [u for u in uvs[0::2] if not math.isnan(u) and not math.isinf(u)]
    vs = [v for v in uvs[1::2] if not math.isnan(v) and not math.isinf(v)]
    nan_uv = sum(1 for u in uvs if math.isnan(u) or math.isinf(u))
    nan_nrm = sum(1 for n in m["normals"] if math.isnan(n) or math.isinf(n))
    print(
        f"[{i:2d}] {m['name']:28s} tex={str(m.get('texture')):28s} "
        f"v={len(xs):4d} x=[{min(xs):7.1f},{max(xs):7.1f}] y=[{min(ys):7.1f},{max(ys):7.1f}] z=[{min(zs):7.1f},{max(zs):7.1f}] "
        f"u=[{min(us) if us else 0:5.2f},{max(us) if us else 0:5.2f}] nan_uv={nan_uv} nan_nrm={nan_nrm}"
    )
