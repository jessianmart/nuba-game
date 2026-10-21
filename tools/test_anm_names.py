import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES
from tools.inspect_anm_and_eff import curve_byte_size, euler_deg_to_quat, quat_mul, quat_inv


def quat_to_euler_rad(q):
    x, y, z, w = q
    # Roll (x-axis)
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    rx = math.atan2(sinr_cosp, cosr_cosp)
    # Pitch (y-axis)
    sinp = 2.0 * (w * y - z * x)
    ry = math.copysign(math.pi / 2, sinp) if abs(sinp) >= 1.0 else math.asin(sinp)
    # Yaw (z-axis)
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    rz = math.atan2(siny_cosp, cosy_cosp)
    return (round(rx, 3), round(ry, 3), round(rz, 3))


def parse_anm_tracks(pay: bytes, pbase: int, sci, smaps, stypes, snames):
    dur, frame_step, unk1, loop_flg, n_entries, n_other_entries, n_coords = struct.unpack(">IIHHHHI", pay[:20])
    nframes = max(1, dur // max(1, frame_step) + 1)
    pos = 20
    coord_bone_names = []
    for e in range(n_entries):
        clump_cmap, n_refs, n_oth = struct.unpack(">IHH", pay[pos:pos+8])
        pos += 8
        refs = struct.unpack(f">{n_refs}I", pay[pos : pos + n_refs * 4])
        pos += (n_refs + n_oth) * 4
        if e == 0:
            for r_cmap in refs:
                gi = sci[pbase + r_cmap]
                ti, _, ni = smaps[gi]
                if stypes[ti] == "nuccChunkCoord":
                    coord_bone_names.append(snames[ni])
    pos += n_other_entries * 4 + n_coords * 8

    tracks = {}
    t_pos = pos
    while t_pos + 8 <= len(pay):
        clump_i, coord_i, unk_f, n_curves = struct.unpack(">HHHH", pay[t_pos:t_pos+8])
        if n_curves == 0 or n_curves > 32 or clump_i != 0:
            break
        t_pos += 8
        chdrs = [struct.unpack(">HHHH", pay[t_pos + i*8 : t_pos + (i+1)*8]) for i in range(n_curves)]
        t_pos += 8 * n_curves
        bname = coord_bone_names[coord_i] if coord_i < len(coord_bone_names) else ""
        # Match only primary bone names (not face01/face02)
        low = bname.lower()
        parts = low.split(" ", 1)
        b_clean = parts[1].strip() if len(parts) > 1 else low
        cb = None
        if b_clean == "pelvis": cb = 1
        elif b_clean == "spine": cb = 2
        elif b_clean == "spine1": cb = 3
        elif b_clean == "neck": cb = 4
        elif b_clean == "head": cb = 5
        elif b_clean == "l clavicle": cb = 6
        elif b_clean == "l upperarm": cb = 7
        elif b_clean == "l forearm": cb = 8
        elif b_clean == "l hand": cb = 9
        elif b_clean == "r clavicle": cb = 10
        elif b_clean == "r upperarm": cb = 11
        elif b_clean == "r forearm": cb = 12
        elif b_clean == "r hand": cb = 13
        elif b_clean == "l thigh": cb = 14
        elif b_clean == "l calf": cb = 15
        elif b_clean == "l foot": cb = 16
        elif b_clean == "r thigh": cb = 17
        elif b_clean == "r calf": cb = 18
        elif b_clean == "r foot": cb = 19

        for c_idx, c_type, k_cnt, sz_f in chdrs:
            bsz = curve_byte_size(c_type, k_cnt, sz_f)
            cdata = pay[t_pos : t_pos + bsz]
            if cb is not None and c_idx == 1:
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

            for fn, wanted in [
                ("1nrtbod1c.xfbin", ("1nrtnut0", "1nrtdsh0l")),
                ("1nrtbod1l.xfbin", ("1nrtcmb00",)),
                ("1nrtskl1.xfbin", ("1nrtcha10", "1nrtcha11")),
                ("1nrtskl2.xfbin", ("1nrtcha20",)),
            ]:
                r = toc_map[fn]
                f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                for tname, cname, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkAnm" and cname in wanted:
                        nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                        print(f"Animation {cname:12s}: nframes={nf:3d} loop={lp} canonical_bones={sorted(trks.keys())}")
                        for cb in (2, 3, 5, 7, 8, 11, 12, 14, 15, 17, 18):
                            if cb in trks:
                                qs = trks[cb]
                                q0 = qs[0]
                                dqs = [quat_to_euler_rad(quat_mul(quat_inv(q0), q)) for q in qs[::max(1, len(qs)//4)]]
                                print(f"  [{cb:2d}] {CANONICAL_BONES[cb][0]:12s}: delta_eulers={dqs}")


if __name__ == "__main__":
    main()
