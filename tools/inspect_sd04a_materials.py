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

print(f"sd04a smaps: {len(smaps)}, sci: {len(sci)}, stypes: {len(stypes)}, snames: {len(snames)}")

for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkTexture":
        print(f"TextureChunk: {ch_name:30s} len={len(payload)} has_NTP3={b'NTP3' in payload}")
    elif tname == "nuccChunkMaterial":
        u32s = struct.unpack(f">{len(payload)//4}I", payload[:(len(payload)//4)*4])
        # Find all texture references
        found_tex = []
        for u in u32s:
            if (pbase + u) < len(sci):
                gi = sci[pbase + u]
                if gi < len(smaps):
                    ti, pi, ni = smaps[gi]
                    if stypes[ti] == "nuccChunkTexture":
                        found_tex.append(snames[ni])
        print(f"Material: {ch_name:30s} -> Textures: {found_tex}")
