import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES
from tools.test_fk_anm_pose import parse_full_anm, evaluate_fk, quat_mul, quat_inv, quat_rotate_vec


# Exact mapping of canonical bone index (1..19) -> primary NUCC bone suffix
CANONICAL_SUFFIX = {
    1: "pelvis",
    2: "spine",
    3: "spine1",
    4: "neck",
    5: "head",
    6: "l clavicle",
    7: "l upperarm",
    8: "l forearm",
    9: "l hand",
    10: "r clavicle",
    11: "r upperarm",
    12: "r forearm",
    13: "r hand",
    14: "l thigh",
    15: "l calf",
    16: "l foot",
    17: "r thigh",
    18: "r calf",
    19: "r foot",
}


def nucc_vec_to_three(v):
    return (v[0], v[2], -v[1])


def nucc_quat_to_three(q):
    # (X, Y, Z)_Three = (X, Z, -Y)_NUCC -> right-handed basis change maps (qx, qy, qz, qw) -> (qx, qz, -qy, qw)
    return (q[0], q[2], -q[1], q[3])


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

        # Find bone index in coords for each canonical bone 1..19
        cb_to_coord_idx = {}
        for i, (bname, _) in enumerate(coords):
            parts = bname.lower().split(" ", 1)
            suf = parts[1].strip() if len(parts) > 1 else bname.lower()
            for cb, target_suf in CANONICAL_SUFFIX.items():
                if suf == target_suf and cb not in cb_to_coord_idx:
                    cb_to_coord_idx[cb] = i

        bind_pos, bind_rot = evaluate_fk(coords, parents)

        rc = toc_map["1nrtbod1c.xfbin"]
        f_dat.seek(cpk["TocOffset"] + rc["FileOffset"])
        raw_c = decompress_crilayla(f_dat.read(rc["FileSize"]))
        chunks_c, smaps_c, sci_c, stypes_c, snames_c = parse_nucc_chunks(raw_c)
        for tname, ch_name, cmap, pay, pbase in chunks_c:
            if tname == "nuccChunkAnm" and ch_name == "1nrtnut0":
                nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci_c, smaps_c, stypes_c, snames_c)
                anm_pos, anm_rot = evaluate_fk(coords, parents, r_trks, p_trks, frame_idx=0)

                # Compute world-space delta quaternion in Three.js space for each canonical bone:
                # dQ_nucc = anm_rot[i] * inv(bind_rot[i])
                dq_three = {0: (0.0, 0.0, 0.0, 1.0)}
                j_bind_three = {0: (0.0, 0.0, 0.0)}
                for cb in range(1, 20):
                    ci = cb_to_coord_idx[cb]
                    dq_nucc = quat_mul(anm_rot[ci], quat_inv(bind_rot[ci]))
                    dq_three[cb] = nucc_quat_to_three(dq_nucc)
                    j_bind_three[cb] = nucc_vec_to_three(bind_pos[ci])

                # Compute local Three.js quaternion for each canonical bone c:
                # q_local[c] = inv(dq_three[parent(c)]) * dq_three[c]
                q_local_three = {0: (0.0, 0.0, 0.0, 1.0)}
                for cb in range(1, 20):
                    p_cb = CANONICAL_BONES[cb][1]
                    q_local_three[cb] = quat_mul(quat_inv(dq_three[p_cb]), dq_three[cb])

                # Now simulate Three.js 20-bone hierarchy FK!
                three_w_pos = {0: (0.0, 0.0, 0.0)}
                three_w_rot = {0: (0.0, 0.0, 0.0, 1.0)}
                p1_idx = cb_to_coord_idx[1]
                three_w_pos[1] = nucc_vec_to_three(anm_pos[p1_idx])
                three_w_rot[1] = q_local_three[1]
                for cb in range(2, 20):
                    p_cb = CANONICAL_BONES[cb][1]
                    rel_bind = (
                        j_bind_three[cb][0] - j_bind_three[p_cb][0],
                        j_bind_three[cb][1] - j_bind_three[p_cb][1],
                        j_bind_three[cb][2] - j_bind_three[p_cb][2],
                    )
                    rot_rel = quat_rotate_vec(three_w_rot[p_cb], rel_bind)
                    three_w_pos[cb] = (
                        three_w_pos[p_cb][0] + rot_rel[0],
                        three_w_pos[p_cb][1] + rot_rel[1],
                        three_w_pos[p_cb][2] + rot_rel[2],
                    )
                    three_w_rot[cb] = quat_mul(three_w_rot[p_cb], q_local_three[cb])

                print("=== Three.js 20-Bone Skeleton FK vs Full 202-Bone APK FK ===")
                for cb in (1, 2, 3, 4, 5, 7, 8, 9, 11, 12, 13, 14, 15, 16, 17, 18, 19):
                    ci = cb_to_coord_idx[cb]
                    apk_p = nucc_vec_to_three(anm_pos[ci])
                    thr_p = three_w_pos[cb]
                    print(f"  cb={cb:2d} {CANONICAL_BONES[cb][0]:12s}: APK=({apk_p[0]:6.1f},{apk_p[1]:6.1f},{apk_p[2]:6.1f}) | Three20=({thr_p[0]:6.1f},{thr_p[1]:6.1f},{thr_p[2]:6.1f})")
