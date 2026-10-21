import zipfile
import struct
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.inspect_rig_anm import parse_nucc_exact


def main():
    with zipfile.ZipFile(APK_PATH, "r") as z:
        with z.open("assets/data/sim/stage1.awb") as f_stg:
            cpk = parse_utf(f_stg.read(65536), 16)[0]
            f_stg.seek(cpk["TocOffset"])
            toc = parse_utf(f_stg.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}
            rs = toc_map["sd00a.xfbin"]
            f_stg.seek(cpk["TocOffset"] + rs["FileOffset"])
            sraw = decompress_crilayla(f_stg.read(rs["FileSize"]))
            schunks, smaps, sci, stypes, snames = parse_nucc_exact(sraw)

            for tname, cname, cmap, pay, pbase in schunks:
                if tname == "nuccChunkCoord" and len(pay) >= 40:
                    if any(k in cname for k in ("sd00aflo", "sd00aobj019", "sd00aobj018", "dummy_ki", "river")):
                        px, py, pz, rx, ry, rz, sx, sy, sz_v = struct.unpack(">9f", pay[4:40])
                        print(f"off=4  {cname:24s}: pos=({px:8.1f},{py:8.1f},{pz:8.1f}) rot=({rx:6.1f},{ry:6.1f},{rz:6.1f}) scl=({sx:4.1f},{sy:4.1f},{sz_v:4.1f})")
                        if len(pay) >= 44:
                            px2, py2, pz2, rx2, ry2, rz2, sx2, sy2, sz2 = struct.unpack(">9f", pay[8:44])
                            print(f"off=8  {cname:24s}: pos=({px2:8.1f},{py2:8.1f},{pz2:8.1f}) rot=({rx2:6.1f},{ry2:6.1f},{rz2:6.1f}) scl=({sx2:4.1f},{sy2:4.1f},{sz2:4.1f})")


if __name__ == "__main__":
    main()
