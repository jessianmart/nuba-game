import zipfile
import struct
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks

with zipfile.ZipFile(APK_PATH, "r") as z:
    with z.open("assets/data/sim/stage1.awb") as f_stg:
        cpk = parse_utf(f_stg.read(64 * 1024), 16)[0]
        f_stg.seek(cpk["TocOffset"])
        toc = parse_utf(f_stg.read(cpk["TocSize"]), 16)
        toc_map = {r["FileName"].lower(): r for r in toc}
        r = toc_map["sd00a.xfbin"]
        f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
        sraw = decompress_crilayla(f_stg.read(r["FileSize"]))
        schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)

        print("=== TEXTURES IN sd00a.xfbin ===")
        for tname, ch_name, cmap_idx, payload, pbase in schunks:
            if tname == "nuccChunkTexture" and b"NTP3" in payload:
                ntp_pos = payload.find(b"NTP3")
                tot_sz, unk, dat_sz, hdr_sz, unk2, mips, pfmt, w, h = struct.unpack(">IIIHHHHHH", payload[ntp_pos+16:ntp_pos+40])
                print(f"  tex {ch_name:28s} pfmt=0x{pfmt:02x} {w}x{h} dat_sz={dat_sz}")

        print("\n=== ALL MODELS & CLUMPS IN sd00a.xfbin ===")
        for tname, ch_name, cmap_idx, payload, pbase in schunks:
            if tname == "nuccChunkClump":
                _, nbones, nmodels = struct.unpack(">IHH", payload[:8])
                coords = [c[1] for c in schunks if c[0] == "nuccChunkCoord" and c[4] == pbase]
                models = [c[1] for c in schunks if c[0] == "nuccChunkModel" and c[4] == pbase]
                print(f"  CLUMP {ch_name:24s} pbase={pbase:4d} nbones={nbones:3d} coords={coords[:8]} models={models}")
