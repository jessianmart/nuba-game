import zipfile
import struct
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f_stg:
    cpk = ai.parse_utf(f_stg.read(65536), 16)[0]
    f_stg.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f_stg.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}
    r = toc_map["sd04a.xfbin"]
    f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
    sraw = ai.decompress_crilayla(f_stg.read(r["FileSize"]))
    schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)

print("=== All Models in sd04a ===")
models = []
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkModel":
        models.append(ch_name)
for m in sorted(models):
    print(" ", m)

print("\n=== All Coords in sd04a ===")
coords = []
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkCoord":
        if len(payload) >= 36:
            vals = struct.unpack(">9f", payload[:36])
            coords.append((ch_name, vals))
        else:
            coords.append((ch_name, None))

for cname, vals in sorted(coords, key=lambda x: x[0]):
    if any(k in cname.lower() for k in ("tree", "ki", "dummy", "gate", "obj", "hokage", "pav")):
        print(f"  {cname:28s} {vals}")
