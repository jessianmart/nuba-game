
"""Probe {cid}eff1.xfbin content (real VFX?) for all hero #12 candidates."""
import sys, os, zipfile
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime"))
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks

CANDS = ["1sik","1tnd","1knk","1tyo","1kib","1sin","1hkg","1ino","1ten","1guy","1orc","1kmm","1krs"]

with zipfile.ZipFile(APK_PATH) as z:
    f = z.open("assets/data/sim/data.awb")
    cpk = parse_utf(f.read(65536), 16)[0]
    f.seek(cpk["TocOffset"])
    toc = parse_utf(f.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}

    print(f"{'cid':6s} {'raw_bytes':>9s} {'texNTP3':>7s} {'mdlNDP3':>8s} {'shadow_mdl':>10s} {'anm':>4s}")
    for cid in CANDS:
        fn = f"{cid}eff1.xfbin"
        if fn not in toc_map:
            print(f"{cid:6s} MISSING")
            continue
        r = toc_map[fn]
        f.seek(cpk["TocOffset"] + r["FileOffset"])
        raw = decompress_crilayla(f.read(r["FileSize"]))
        chunks, _, _, _, _ = parse_nucc_chunks(raw)
        tex = [c for c in chunks if c[0] == "nuccChunkTexture" and b"NTP3" in c[3]]
        mdl = [c for c in chunks if c[0] == "nuccChunkModel" and b"NDP3" in c[3]]
        mdl_shadow = [c for c in mdl if "shadow" in c[1].lower()]
        anm = [c for c in chunks if c[0] == "nuccChunkAnm"]
        print(f"{cid:6s} {len(raw):9d} {len(tex):7d} {len(mdl):8d} {len(mdl_shadow):10d} {len(anm):4d}")
