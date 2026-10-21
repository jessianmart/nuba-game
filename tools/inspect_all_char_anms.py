import zipfile
import struct
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import ROSTER, parse_nucc_chunks
from tools.test_fk_anm_pose import parse_full_anm

with zipfile.ZipFile(APK_PATH, "r") as z:
    with z.open("assets/data/sim/data.awb") as f_dat:
        cpk = parse_utf(f_dat.read(65536), 16)[0]
        f_dat.seek(cpk["TocOffset"])
        toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
        toc_map = {r["FileName"].lower(): r for r in toc}

        for cid, cname, _, _, _ in ROSTER:
            print(f"=== {cid} ({cname}) ===")
            for suffix in ("bod1c", "bod1l", "skl1", "skl2"):
                fn = f"{cid}{suffix}.xfbin"
                if fn not in toc_map:
                    continue
                r = toc_map[fn]
                f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                summary = []
                for tname, ch_name, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkAnm":
                        nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci, smaps, stypes, snames)
                        if len(r_trks) >= 10:
                            summary.append(f"{ch_name}(f={nf},b={len(r_trks)})")
                print(f"  {suffix:5s}: {', '.join(summary[:18])}")
