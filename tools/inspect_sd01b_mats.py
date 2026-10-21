import zipfile
import struct
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f:
    cpk = ai.parse_utf(f.read(65536), 16)[0]
    f.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f.read(cpk["TocSize"]), 16)
    r = {x["FileName"].lower(): x for x in toc}["sd01b.xfbin"]
    f.seek(cpk["TocOffset"] + r["FileOffset"])
    raw = ai.decompress_crilayla(f.read(r["FileSize"]))
    schunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)

tex_names = [c[1] for c in schunks if c[0] == "nuccChunkTexture"]
print("Available textures in sd01b:", sorted(tex_names))

for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkMaterial":
        u32s = struct.unpack(f">{len(payload)//4}I", payload[:(len(payload)//4)*4])
        found_tex = []
        for u in u32s:
            if (pbase + u) < len(sci):
                gi = sci[pbase + u]
                if gi < len(smaps):
                    ti, pi, ni = smaps[gi]
                    if stypes[ti] == "nuccChunkTexture":
                        found_tex.append(snames[ni])
        print(f"Material: {ch_name:30s} -> Textures: {found_tex}")
