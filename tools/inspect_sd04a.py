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
    
    for stage_name in ["sd04a.xfbin", "sd01b.xfbin"]:
        r = toc_map[stage_name]
        f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
        sraw = ai.decompress_crilayla(f_stg.read(r["FileSize"]))
        schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)
        
        print(f"=== {stage_name} (Decompressed: {len(sraw)} bytes) ===")
        print(f"Total chunks: {len(schunks)}")
        
        type_counts = {}
        models = []
        textures = []
        coords = []
        for tname, ch_name, cmap_idx, payload, pbase in schunks:
            type_counts[tname] = type_counts.get(tname, 0) + 1
            if tname == "nuccChunkModel":
                models.append(ch_name)
            elif tname == "nuccChunkTexture":
                textures.append(ch_name)
            elif tname == "nuccChunkCoord":
                coords.append(ch_name)
                
        print("Chunk types:", type_counts)
        print(f"Models ({len(models)}):", models[:30])
        print(f"Textures ({len(textures)}):", textures[:30])
        print(f"Coords ({len(coords)}):", coords[:30])
