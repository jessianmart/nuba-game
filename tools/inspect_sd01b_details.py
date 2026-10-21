import zipfile
import struct
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks, decode_ndp3_mesh

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f:
    cpk = ai.parse_utf(f.read(65536), 16)[0]
    f.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f.read(cpk["TocSize"]), 16)
    r = {x["FileName"].lower(): x for x in toc}["sd01b.xfbin"]
    f.seek(cpk["TocOffset"] + r["FileOffset"])
    raw = ai.decompress_crilayla(f.read(r["FileSize"]))
    schunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)

coord_map = {}
for t, name, c, pay, pb in schunks:
    if t == "nuccChunkCoord" and len(pay) >= 36:
        coord_map[(pb, name)] = struct.unpack(">9f", pay[:36])

print("=== sd01b Submeshes ===")
for t, name, c, pay, pb in schunks:
    if t == "nuccChunkModel" and b"NDP3" in pay:
        trf = coord_map.get((pb, name))
        subs = decode_ndp3_mesh(pay, name, is_character=False, coord_transform=trf)
        for s in subs:
            pos = s["positions"]
            xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
            print(f"{s['name']:28s} v={len(xs):4d} x=[{min(xs):7.1f},{max(xs):7.1f}] y=[{min(ys):7.1f},{max(ys):7.1f}] z=[{min(zs):7.1f},{max(zs):7.1f}]")
