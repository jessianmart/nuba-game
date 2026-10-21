import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES
from tools.inspect_anm_and_eff import curve_byte_size, quat_mul, quat_inv


def euler_xyz_to_quat(rx_deg, ry_deg, rz_deg):
    rx, ry, rz = math.radians(rx_deg)*0.5, math.radians(ry_deg)*0.5, math.radians(rz_deg)*0.5
    qx = (math.sin(rx), 0.0, 0.0, math.cos(rx))
    qy = (0.0, math.sin(ry), 0.0, math.cos(ry))
    qz = (0.0, 0.0, math.sin(rz), math.cos(rz))
    return quat_mul(quat_mul(qx, qy), qz)


def quat_rotate_vec(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx = 2.0 * (y * vz - z * vy)
    ty = 2.0 * (z * vx - x * vz)
    tz = 2.0 * (x * vy - y * vx)
    return (
        vx + w * tx + (y * tz - z * ty),
        vy + w * ty + (z * tx - x * tz),
        vz + w * tz + (x * ty - y * tx),
    )


def parse_full_anm(pay: bytes, pbase: int, sci, smaps, stypes, snames):
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

    rot_tracks = {}
    pos_tracks = {}
    t_pos = pos
    while t_pos + 8 <= len(pay):
        clump_i, coord_i, unk_f, n_curves = struct.unpack(">HHHH", pay[t_pos:t_pos+8])
        if n_curves == 0 or n_curves > 32 or clump_i != 0:
            break
        t_pos += 8
        chdrs = [struct.unpack(">HHHH", pay[t_pos + i*8 : t_pos + (i+1)*8]) for i in range(n_curves)]
        t_pos += 8 * n_curves
        bname = coord_bone_names[coord_i] if coord_i < len(coord_bone_names) else ""

        for c_idx, c_type, k_cnt, sz_f in chdrs:
            bsz = curve_byte_size(c_type, k_cnt, sz_f)
            cdata = pay[t_pos : t_pos + bsz]
            if c_idx == 0 and bname:  # Translation
                vecs = []
                if c_type == 0x0005 and len(cdata) == 12:
                    vecs = [struct.unpack(">3f", cdata)]
                elif c_type == 0x0006 and len(cdata) >= 16:
                    for k in range(k_cnt):
                        _, vx, vy, vz = struct.unpack(">f3f", cdata[k*16:(k+1)*16])
                        vecs.append((vx, vy, vz))
                elif c_type == 0x0007 and len(cdata) >= 12:
                    for k in range(k_cnt):
                        vecs.append(struct.unpack(">3f", cdata[k*12:(k+1)*12]))
                if vecs:
                    pos_tracks[bname.lower()] = vecs
            elif c_idx == 1 and bname:  # Rotation
                quats = []
                if c_type == 0x0008 and len(cdata) == 12:
                    rx_deg, ry_deg, rz_deg = struct.unpack(">3f", cdata)
                    q = euler_xyz_to_quat(rx_deg, ry_deg, rz_deg)
                    quats = [q]
                elif c_type in (0x0009, 0x0011) and len(cdata) >= 8:
                    # 0x0009 / 0x0011 stores row-vector quaternion; conjugate (-qx, -qy, -qz, qw) converts to column-vector qx*qy*qz!
                    if sz_f == k_cnt * 8 or c_type == 0x0009:
                        for k in range(k_cnt):
                            qx, qy, qz, qw = struct.unpack(">4h", cdata[k*8:(k+1)*8])
                            quats.append((-qx/16384.0, -qy/16384.0, -qz/16384.0, qw/16384.0))
                    elif sz_f == k_cnt * 10:
                        for k in range(k_cnt):
                            tk, qx, qy, qz, qw = struct.unpack(">H4h", cdata[k*10:(k+1)*10])
                            if tk != 0xFFFF:
                                quats.append((-qx/16384.0, -qy/16384.0, -qz/16384.0, qw/16384.0))
                if quats:
                    rot_tracks[bname.lower()] = quats
            t_pos += bsz
    return nframes, loop_flg, rot_tracks, pos_tracks


def evaluate_fk(coords, parents, r_trks=None, p_trks=None, frame_idx=0):
    w_pos = [(0.0, 0.0, 0.0)] * len(coords)
    w_rot = [(0.0, 0.0, 0.0, 1.0)] * len(coords)
    for i, (bname, trf) in enumerate(coords):
        px, py, pz, rx, ry, rz, _, _, _ = trf
        low = bname.lower()
        if p_trks and low in p_trks and p_trks[low]:
            vecs = p_trks[low]
            px, py, pz = vecs[min(frame_idx, len(vecs) - 1)]
        if r_trks and low in r_trks and r_trks[low]:
            qs = r_trks[low]
            lq = qs[min(frame_idx, len(qs) - 1)]
        else:
            lq = euler_xyz_to_quat(rx, ry, rz)
        p = parents[i] if i < len(parents) else -1
        if 0 <= p < i:
            rp = quat_rotate_vec(w_rot[p], (px, py, pz))
            w_pos[i] = (w_pos[p][0] + rp[0], w_pos[p][1] + rp[1], w_pos[p][2] + rp[2])
            w_rot[i] = quat_mul(w_rot[p], lq)
        else:
            w_pos[i] = (px, py, pz)
            w_rot[i] = lq
    return w_pos, w_rot


if __name__ == "__main__":
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
            char_clump_pay, char_pbase = next((c[3], c[4]) for c in chunks_b if c[0] == "nuccChunkClump" and c[1].lower().startswith("1nrt"))
            coords = [(c[1], struct.unpack(">9f", c[3][:36])) for c in chunks_b if c[0] == "nuccChunkCoord" and c[4] == char_pbase]
            _, nbones, _ = struct.unpack(">IHH", char_clump_pay[:8])
            parents = struct.unpack(f">{nbones}h", char_clump_pay[8 : 8 + nbones * 2])

            bind_pos, bind_rot = evaluate_fk(coords, parents)

            rc = toc_map["1nrtbod1c.xfbin"]
            f_dat.seek(cpk["TocOffset"] + rc["FileOffset"])
            raw_c = decompress_crilayla(f_dat.read(rc["FileSize"]))
            chunks_c, smaps_c, sci_c, stypes_c, snames_c = parse_nucc_chunks(raw_c)
            for tname, ch_name, cmap, pay, pbase in chunks_c:
                if tname == "nuccChunkAnm" and ch_name == "1nrtnut0":
                    nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci_c, smaps_c, stypes_c, snames_c)
                    anm_pos, anm_rot = evaluate_fk(coords, parents, r_trks, p_trks, frame_idx=0)
                    print("\n=== UNIFIED COLUMN-VECTOR FK: 1nrtnut0 (Idle) vs Bind Pose ===")
                    for i, (bname, _) in enumerate(coords):
                        if bname.split()[-1] in ("pelvis", "spine", "head", "upperarm", "forearm", "hand", "thigh", "calf", "foot"):
                            tx, ty, tz = anm_pos[i][0], anm_pos[i][2], -anm_pos[i][1]
                            bx, by, bz = bind_pos[i][0], bind_pos[i][2], -bind_pos[i][1]
                            print(f"  {bname:22s}: Bind=({bx:6.1f},{by:6.1f},{bz:6.1f}) -> Idle=({tx:6.1f},{ty:6.1f},{tz:6.1f})")
