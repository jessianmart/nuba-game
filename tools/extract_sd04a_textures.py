import os
import struct
import zipfile
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks, write_png_rgba
from tools.fix_stage_and_textures import decode_ntp3_etc2_clean

OUT_STAGE = "public/assets/stage"
os.makedirs(OUT_STAGE, exist_ok=True)

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

saved = 0
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkTexture" and b"NTP3" in payload:
        ntp_pos = payload.find(b"NTP3")
        low_c = ch_name.lower()
        # High quality decoding
        # 512 for main floors/walls/clouds, 256 for props
        max_d = 1024 if any(k in low_c for k in ("flo", "bac", "obj010", "and004")) else 512
        w, h, rgba, _ = decode_ntp3_etc2_clean(payload, ntp_pos + 16, max_dim=max_d)
        png_path = os.path.join(OUT_STAGE, f"{ch_name}.png")
        write_png_rgba(png_path, w, h, rgba)
        saved += 1
        print(f"Decoded [{saved:2d}/55] {ch_name}.png -> {w}x{h} ({len(rgba)} bytes)")

print(f"\nSuccessfully extracted all {saved} Chunin Arena textures to {OUT_STAGE}!")
