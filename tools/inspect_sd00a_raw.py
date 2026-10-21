import json
import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks

with open("public/assets/stage/stage_3d.json", "r", encoding="utf-8") as f:
    stg = json.load(f)

for i in range(min(46, len(stg["meshes"]))):
    m = stg["meshes"][i]
    pos = m["positions"]
    xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
    uvs = m["uvs"]
    us = [u for u in uvs[0::2] if not math.isnan(u) and not math.isinf(u)]
    print(
        f"[{i:2d}] {m['name']:28s} tex={str(m.get('texture')):28s} "
        f"v={len(xs):4d} x=[{min(xs):7.1f},{max(xs):7.1f}] y=[{min(ys):7.1f},{max(ys):7.1f}] z=[{min(zs):7.1f},{max(zs):7.1f}] "
        f"u=[{min(us) if us else 0:5.2f},{max(us) if us else 0:5.2f}]"
    )
