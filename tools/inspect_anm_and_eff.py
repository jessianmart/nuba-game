import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES


def curve_byte_size(ctype: int, kcnt: int, sz_field: int) -> int:
    if ctype == 0x0005: return 12
    if ctype == 0x0006: return kcnt * 16
    if ctype == 0x0007: return kcnt * 12
    if ctype == 0x0008: return 12
    if ctype == 0x0009: return kcnt * 8
    if ctype == 0x000b: return 4
    if ctype == 0x000c: return kcnt * 8
    if ctype == 0x000d: return kcnt * 4
    if ctype in (0x0010, 0x0011): return sz_field if sz_field > 0 else kcnt * 8
    return sz_field


def quat_mul(q1, q2):
    x1, y1, z1, w1 = q1
    x2, y2, z2, w2 = q2
    return (
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
    )


def quat_inv(q):
    x, y, z, w = q
    n = x*x + y*y + z*z + w*w
    if n <= 1e-8:
        return (0.0, 0.0, 0.0, 1.0)
    return (-x/n, -y/n, -z/n, w/n)


def euler_deg_to_quat(rx_deg, ry_deg, rz_deg):
    rx, ry, rz = math.radians(rx_deg)*0.5, math.radians(ry_deg)*0.5, math.radians(rz_deg)*0.5
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    # ZYX or XYZ
    return (
        sx*cy*cz - cx*sy*sz,
        cx*sy*cz + sx*cy*sz,
        cx*cy*sz - sx*sy*cz,
        cx*cy*cz + sx*sy*sz,
    )


def extract_canonical_bone_quats(pay: bytes, bone_names):
    dur, frame_step, unk1, loop_flg, n_entries, n_other_entries, n_coords = struct.unpack(">IIHHHHI", pay[:20])
    nframes = max(1, dur // max(1, frame_step) + 1)
    pos = 20
    for _ in range(n_entries):
        _, n_refs, n_oth = struct.unpack(">IHH", pay[pos:pos+8])
        pos += 8 + (n_refs + n_oth) * 4
    pos += n_other_entries * 4 + n_coords * 8

    tracks = {}
    t_pos = pos
    while t_pos + 8 <= len(pay):
        clump_i, coord_i, unk_f, n_curves = struct.unpack(">HHHH", pay[t_pos:t_pos+8])
        if n_curves == 0 or n_curves > 10 or clump_i != 0:
            break
        t_pos += 8
        chdrs = []
        for _ in range(n_curves):
            chdrs.append(struct.unpack(">HHHH", pay[t_pos:t_pos+8]))
            t_pos += 8
        bname = bone_names[coord_i] if coord_i < len(bone_names) else ""
        cb = match_canonical_bone(bname)
        for c_idx, c_type, k_cnt, sz_f in chdrs:
            bsz = curve_byte_size(c_type, k_cnt, sz_f)
            cdata = pay[t_pos : t_pos + bsz]
            if cb is not None and c_idx == 1 and cb not in tracks:
                quats = []
                if c_type == 0x0008 and len(cdata) == 12:
                    i0, i1, i2 = struct.unpack(">3i", cdata)
                    q = euler_deg_to_quat(i0 * 180.0 / 2147483648.0, i1 * 180.0 / 2147483648.0, i2 * 180.0 / 2147483648.0)
                    quats = [q]
                elif c_type in (0x0009, 0x0011) and len(cdata) >= 8:
                    if sz_f == k_cnt * 8 or c_type == 0x0009:
                        for k in range(k_cnt):
                            qx, qy, qz, qw = struct.unpack(">4h", cdata[k*8:(k+1)*8])
                            quats.append((qx/16384.0, qy/16384.0, qz/16384.0, qw/16384.0))
                    elif sz_f == k_cnt * 10:
                        for k in range(k_cnt):
                            tk, qx, qy, qz, qw = struct.unpack(">H4h", cdata[k*10:(k+1)*10])
                            if tk != 0xFFFF:
                                quats.append((qx/16384.0, qy/16384.0, qz/16384.0, qw/16384.0))
                if quats:
                    tracks[cb] = quats
            t_pos += bsz
    return nframes, loop_flg, tracks


def main():
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
            bone_names = [c[1] for c in chunks_b if c[0] == "nuccChunkCoord"]

            for fn, wanted in [
                ("1nrtbod1c.xfbin", ("1nrtnut0", "1nrtdsh0l")),
                ("1nrtbod1l.xfbin", ("1nrtcmb00", "1nrtcmb01")),
                ("1nrtskl1.xfbin", ("1nrtcha10", "1nrtcha11")),
                ("1nrtskl2.xfbin", ("1nrtcha20",)),
            ]:
                r = toc_map[fn]
                f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                chunks, _, _, _, _ = parse_nucc_chunks(raw)
                for tname, cname, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkAnm" and cname in wanted:
                        nf, lp, trks = extract_canonical_bone_quats(pay, bone_names)
                        print(f"Animation {cname:12s}: nframes={nf:3d} loop={lp} canonical_bones_animated={sorted(trks.keys())}")
                        for cb in sorted(trks.keys())[:6]:
                            qs = trks[cb]
                            q0 = qs[0]
                            qmid = qs[len(qs)//2]
                            dq = quat_mul(quat_inv(q0), qmid)
                            print(f"  bone[{cb:2d}] {CANONICAL_BONES[cb][0]:12s}: keys={len(qs):2d} q0=({q0[0]:.2f},{q0[1]:.2f},{q0[2]:.2f},{q0[3]:.2f}) dq_mid=({dq[0]:.2f},{dq[1]:.2f},{dq[2]:.2f},{dq[3]:.2f})")


if __name__ == "__main__":
    main()
