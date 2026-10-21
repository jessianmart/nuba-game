import zipfile
import struct
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks, match_canonical_bone, CANONICAL_BONES
from tools.inspect_anm_and_eff import curve_byte_size, quat_mul, quat_inv


def euler_zyx_or_xyz_to_quat(rx_deg, ry_deg, rz_deg, order="XYZ"):
    rx, ry, rz = math.radians(rx_deg)*0.5, math.radians(ry_deg)*0.5, math.radians(rz_deg)*0.5
    qx = (math.sin(rx), 0.0, 0.0, math.cos(rx))
    qy = (0.0, math.sin(ry), 0.0, math.cos(ry))
    qz = (0.0, 0.0, math.sin(rz), math.cos(rz))
    if order == "XYZ":
        return quat_mul(quat_mul(qx, qy), qz)
    elif order == "ZYX":
        return quat_mul(quat_mul(qz, qy), qx)


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

        for order in ("XYZ", "ZYX"):
            print(f"\n=== Testing FK Bind Pose Order={order} ===")
            w_pos = [(0.0, 0.0, 0.0)] * len(coords)
            w_rot = [(0.0, 0.0, 0.0, 1.0)] * len(coords)
            for i, (bname, trf) in enumerate(coords):
                px, py, pz, rx, ry, rz, sx, sy, sz = trf
                lq = euler_zyx_or_xyz_to_quat(rx, ry, rz, order=order)
                p = parents[i] if i < len(parents) else -1
                if 0 <= p < i:
                    rp = quat_rotate_vec(w_rot[p], (px, py, pz))
                    w_pos[i] = (w_pos[p][0] + rp[0], w_pos[p][1] + rp[1], w_pos[p][2] + rp[2])
                    w_rot[i] = quat_mul(w_rot[p], lq)
                else:
                    w_pos[i] = (px, py, pz)
                    w_rot[i] = lq
                cb = match_canonical_bone(bname)
                if cb is not None and bname.split()[-1] in ("pelvis", "spine", "head", "upperarm", "forearm", "hand", "thigh", "calf", "foot"):
                    # Convert NUCC (x, y, z) -> Three.js (x, z, -y)
                    tx, ty, tz = w_pos[i][0], w_pos[i][2], -w_pos[i][1]
                    print(f"  cb={cb:2d} {bname:22s}: ThreeJS_pos=({tx:6.2f}, {ty:6.2f}, {tz:6.2f}) w_quat=({w_rot[i][0]:5.2f},{w_rot[i][1]:5.2f},{w_rot[i][2]:5.2f},{w_rot[i][3]:5.2f})")
