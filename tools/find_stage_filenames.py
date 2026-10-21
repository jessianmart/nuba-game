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

# Let's search for "sd0" or "sk0" or "sp0" in sraw
import re
matches = re.finditer(rb's[a-z0-9_]{3,}', sraw)
for m in matches:
    start = max(0, m.start() - 32)
    end = min(len(sraw), m.end() + 32)
    print(m.group().decode('ascii', errors='ignore'), "at", m.start(), "context:", sraw[start:end])
