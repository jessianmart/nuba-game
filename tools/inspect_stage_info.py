import zipfile
import tools.apk_inspect as ai

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f_stg:
    cpk = ai.parse_utf(f_stg.read(65536), 16)[0]
    f_stg.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f_stg.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}
    
    r = toc_map["stageareainfo.bin.xfbin"]
    f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
    sraw = ai.decompress_crilayla(f_stg.read(r["FileSize"]))
    print(f"StageAreaInfo: {len(sraw)} bytes")
    # print readable strings
    import re
    strings = re.findall(rb'[a-zA-Z0-9_\-]{4,}', sraw)
    for s in strings:
        print(" ", s.decode('ascii', errors='ignore'))
