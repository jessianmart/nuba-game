import zipfile
import struct
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

# Let's inspect all strings and structure in stageareainfo
pos = 0
while True:
    idx = sraw.find(b"STAGE_", pos)
    if idx == -1: break
    end = sraw.find(b"\x00", idx)
    stg_name = sraw[idx:end].decode("ascii", errors="ignore")
    # find surrounding bytes
    context = sraw[max(0, idx-64):min(len(sraw), idx+128)]
    import re
    words = re.findall(rb'[a-zA-Z0-9_\.]{3,}', context)
    print(stg_name, "->", [w.decode('ascii', errors='ignore') for w in words])
    pos = end + 1
