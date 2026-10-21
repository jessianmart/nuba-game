
"""Peek at chunks inside 1sikeff1.xfbin."""
import sys, os, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime"))
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks

with zipfile.ZipFile(APK_PATH) as z:
    f = z.open("assets/data/sim/data.awb")
    cpk = parse_utf(f.read(65536), 16)[0]
    f.seek(cpk["TocOffset"])
    toc = parse_utf(f.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}

    for fn in ["1sikeff1.xfbin", "1sikeff2.xfbin"]:
        if fn not in toc_map:
            print(fn, "NOT in toc"); continue
        r = toc_map[fn]
        f.seek(cpk["TocOffset"] + r["FileOffset"])
        raw = decompress_crilayla(f.read(r["FileSize"]))
        chunks, _, _, _, _ = parse_nucc_chunks(raw)
        print(f"### {fn}: {len(chunks)} chunks, raw={len(raw)}")
        for t, name, cmap, pay, pbase in chunks:
            print(f"  {t:22s} {name:34s} NDP3={b'NDP3' in pay} NTP3={b'NTP3' in pay} len={len(pay)}")
        print()
