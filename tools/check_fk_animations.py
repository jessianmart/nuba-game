import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES
from tools.inspect_anm_and_eff import curve_byte_size


def inspect_nrt_bind_and_anm():
    with zipfile.ZipFile(APK_PATH, "r") as z:
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            rb = toc_map["1nrtbod1.xfbin"]
            f_dat.seek(cpk["TocOffset"] + rb["FileOffset"])
            raw_b = decompress_crilayla(f_dat.read(rb["FileSize"]))
            chunks_b, _, _, _, _ = parse_nucc_chunks(raw_b)

            char_clump_pay = None
            char_pbase = None
            for tname, ch_name, cmap_idx, payload, pbase in chunks_b:
                if tname == "nuccChunkClump" and ch_name.lower().startswith("1nrt"):
                    char_clump_pay = payload
                    char_pbase = pbase
                    break

            coords = [(c[1], struct.unpack(">9f", c[3][:36])) for c in chunks_b if c[0] == "nuccChunkCoord" and c[4] == char_pbase]
            _, nbones, _ = struct.unpack(">IHH", char_clump_pay[:8])
            parents = struct.unpack(f">{nbones}h", char_clump_pay[8 : 8 + nbones * 2])

            print(f"1nrtbod1: {len(coords)} coords, {nbones} bones in clump")
            for i, (bname, trf) in enumerate(coords):
                cb = match_canonical_bone(bname)
                if cb is not None:
                    px, py, pz, rx, ry, rz, sx, sy, sz = trf
                    p_idx = parents[i] if i < len(parents) else -1
                    p_name = coords[p_idx][0] if 0 <= p_idx < len(coords) else "ROOT"
                    print(f"  bone[{i:3d}] cb={cb:2d} ({CANONICAL_BONES[cb][0]:12s}) name={bname:22s} parent={p_idx:3d}({p_name:18s}) pos=({px:6.2f},{py:6.2f},{pz:6.2f}) rot=({rx:6.1f},{ry:6.1f},{rz:6.1f})")

            # Also list all nuccChunkAnm names across 1nrtbod1c, 1nrtbod1l, 1nrtskl1, 1nrtskl2
            for fn in ("1nrtbod1c.xfbin", "1nrtbod1l.xfbin", "1nrtskl1.xfbin", "1nrtskl2.xfbin"):
                if fn not in toc_map:
                    continue
                r = toc_map[fn]
                f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                anms = [c[1] for c in chunks if c[0] == "nuccChunkAnm"]
                print(f"\n{fn} animations ({len(anms)}): {anms}")


if __name__ == "__main__":
    inspect_nrt_bind_and_anm()
