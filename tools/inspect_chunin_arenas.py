import zipfile
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f:
    cpk = ai.parse_utf(f.read(65536), 16)[0]
    f.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f.read(cpk["TocSize"]), 16)
    toc_map = {x["FileName"].lower(): x for x in toc}

    for name in ["sd03a.xfbin", "sd03b.xfbin", "sd03c.xfbin", "sd01b.xfbin"]:
        r = toc_map[name]
        f.seek(cpk["TocOffset"] + r["FileOffset"])
        raw = ai.decompress_crilayla(f.read(r["FileSize"]))
        schunks, _, _, _, _ = parse_nucc_chunks(raw)
        models = [c[1] for c in schunks if c[0] == "nuccChunkModel"]
        textures = [c[1] for c in schunks if c[0] == "nuccChunkTexture"]
        print(f"=== {name} ({len(raw)} bytes) ===")
        print("  Models:", models[:15])
        print("  Textures:", textures[:15])
