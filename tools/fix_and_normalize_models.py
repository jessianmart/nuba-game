import glob
import json
import os

MODELS_DIR = os.path.join("public", "assets", "models")
TARGET_HEIGHT = 5.4  # Standard MOBA hero height in Three.js world units (meters)


def process_all_models():
    for path in sorted(glob.glob(os.path.join(MODELS_DIR, "*.json"))):
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)

        cid = d["id"]
        meshes = d["meshes"]

        # Check current bounding box Y
        min_y = float("inf")
        max_y = float("-inf")
        for sm in meshes:
            pos = sm["positions"]
            for i in range(1, len(pos), 3):
                y = pos[i]
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

        raw_height = max(0.001, max_y - min_y)
        # Scale factor to normalize model into [0 .. TARGET_HEIGHT] meters
        scale = TARGET_HEIGHT / raw_height

        # Normalize all vertex positions to [0 .. 5.4] meters first
        for sm in meshes:
            pos = sm["positions"]
            for i in range(0, len(pos), 3):
                pos[i] = round(pos[i] * scale, 4)
                pos[i + 1] = round((pos[i + 1] - min_y) * scale, 4)
                pos[i + 2] = round(pos[i + 2] * scale, 4)

        # Helper to find shared boundary vertices between two bones (now in 0..5.4m space)
        def shared_verts(b_a, b_b):
            pts = []
            for sm in meshes:
                pos = sm["positions"]
                si = sm.get("skinIndices", [])
                sw = sm.get("skinWeights", [])
                nv = len(pos) // 3
                for v in range(nv):
                    idxs = si[v * 4 : v * 4 + 4]
                    wgts = sw[v * 4 : v * 4 + 4]
                    act = {idxs[k]: wgts[k] for k in range(4) if wgts[k] > 0.04}
                    if b_a in act and b_b in act:
                        pts.append((pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]))
            return pts

        def bone_verts(b_id):
            pts = []
            for sm in meshes:
                pos = sm["positions"]
                si = sm.get("skinIndices", [])
                sw = sm.get("skinWeights", [])
                nv = len(pos) // 3
                for v in range(nv):
                    if si[v * 4] == b_id and sw[v * 4] > 0.25:
                        pts.append((pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]))
            return pts

        def avg_pt(pts, default):
            if not pts:
                return list(default)
            n = len(pts)
            return [
                round(sum(p[0] for p in pts) / n, 4),
                round(sum(p[1] for p in pts) / n, 4),
                round(sum(p[2] for p in pts) / n, 4),
            ]

        sh_l = shared_verts(6, 7) or shared_verts(3, 7)
        sh_x = abs(avg_pt(sh_l, [0.52, 3.85, 0.0])[0]) if sh_l else 0.52

        # Reassign any arm accessory (e.g. Naruto's acce01/02 armband) or sleeve vertices
        # that were parented to clavicle (6 or 10) or spine (2 or 3) out on the arm (|x| > sh_x + 0.14)
        fixed_cnt = 0
        for sm in meshes:
            pos = sm["positions"]
            si = sm.get("skinIndices", [])
            nv = len(pos) // 3
            for v in range(nv):
                vx, vy, vz = pos[v * 3], pos[v * 3 + 1], pos[v * 3 + 2]
                if cid == "1gar" and vz < -0.2:
                    continue
                for k in range(4):
                    b_curr = si[v * 4 + k]
                    if b_curr in (6, 3, 2) and vx > sh_x + 0.14 and vy > 2.5:
                        si[v * 4 + k] = 7 if vx < sh_x + 0.48 else 8
                        fixed_cnt += 1
                    elif b_curr in (10, 3, 2) and vx < -(sh_x + 0.14) and vy > 2.5:
                        si[v * 4 + k] = 11 if vx > -(sh_x + 0.48) else 12
                        fixed_cnt += 1

        # Compute exact anatomical joint pivots at bone boundaries in [0 .. 5.4] meter space
        p_pelvis = avg_pt(bone_verts(1), [0.0, 2.65, 0.0])
        p_spine = avg_pt(shared_verts(1, 2) or bone_verts(2), [0.0, 3.10, 0.0])
        p_spine1 = avg_pt(shared_verts(2, 3) or bone_verts(3), [0.0, 3.65, 0.0])
        p_neck = avg_pt(shared_verts(3, 4) or bone_verts(4), [0.0, 4.25, 0.0])
        p_head = [0.0, round(p_neck[1] + 0.18, 4), 0.0]

        p_l_clav = avg_pt(shared_verts(3, 6) or bone_verts(6), [0.30, round(p_spine1[1] + 0.25, 4), -0.04])
        p_l_up = avg_pt(shared_verts(6, 7) or shared_verts(3, 7), [0.52, round(p_l_clav[1] - 0.05, 4), -0.04])
        p_l_fore = avg_pt(shared_verts(7, 8), [0.98, round(p_l_up[1] - 0.52, 4), -0.07])
        p_l_hand = avg_pt(shared_verts(8, 9), [1.45, round(p_l_fore[1] - 0.48, 4), -0.07])

        p_l_thigh = avg_pt(shared_verts(1, 14) or shared_verts(2, 14), [0.36, round(p_pelvis[1] - 0.35, 4), 0.0])
        p_l_calf = avg_pt(shared_verts(14, 15), [0.50, 1.32, 0.04])
        p_l_foot = avg_pt(shared_verts(15, 16), [0.66, 0.34, -0.04])

        cx = max(0.22, min(0.45, abs(p_l_clav[0])))
        ux = max(cx + 0.14, abs(p_l_up[0]))
        fx = max(ux + 0.28, abs(p_l_fore[0]))
        hx = max(fx + 0.28, abs(p_l_hand[0]))
        tx = max(0.24, abs(p_l_thigh[0]))
        kx = max(0.28, abs(p_l_calf[0]))
        ax = max(0.32, abs(p_l_foot[0]))

        new_bones = [
            {"name": "root",       "parent": -1, "pos": [0.0, 0.0, 0.0]},
            {"name": "pelvis",     "parent": 0,  "pos": [0.0, round(p_pelvis[1], 4), 0.0]},
            {"name": "spine",      "parent": 1,  "pos": [0.0, round(p_spine[1], 4), 0.0]},
            {"name": "spine1",     "parent": 2,  "pos": [0.0, round(p_spine1[1], 4), 0.0]},
            {"name": "neck",       "parent": 3,  "pos": [0.0, round(p_neck[1], 4), 0.0]},
            {"name": "head",       "parent": 4,  "pos": [0.0, round(p_head[1], 4), 0.0]},
            {"name": "l_clavicle", "parent": 3,  "pos": [round(cx, 4), round(p_l_clav[1], 4), round(p_l_clav[2], 4)]},
            {"name": "l_upperarm", "parent": 6,  "pos": [round(ux, 4), round(p_l_up[1], 4), round(p_l_up[2], 4)]},
            {"name": "l_forearm",  "parent": 7,  "pos": [round(fx, 4), round(p_l_fore[1], 4), round(p_l_fore[2], 4)]},
            {"name": "l_hand",     "parent": 8,  "pos": [round(hx, 4), round(p_l_hand[1], 4), round(p_l_hand[2], 4)]},
            {"name": "r_clavicle", "parent": 3,  "pos": [round(-cx, 4), round(p_l_clav[1], 4), round(p_l_clav[2], 4)]},
            {"name": "r_upperarm", "parent": 10, "pos": [round(-ux, 4), round(p_l_up[1], 4), round(p_l_up[2], 4)]},
            {"name": "r_forearm",  "parent": 11, "pos": [round(-fx, 4), round(p_l_fore[1], 4), round(p_l_fore[2], 4)]},
            {"name": "r_hand",     "parent": 12, "pos": [round(-hx, 4), round(p_l_hand[1], 4), round(p_l_hand[2], 4)]},
            {"name": "l_thigh",    "parent": 1,  "pos": [round(tx, 4), round(p_l_thigh[1], 4), round(p_l_thigh[2], 4)]},
            {"name": "l_calf",     "parent": 14, "pos": [round(kx, 4), round(p_l_calf[1], 4), round(p_l_calf[2], 4)]},
            {"name": "l_foot",     "parent": 15, "pos": [round(ax, 4), round(p_l_foot[1], 4), round(p_l_foot[2], 4)]},
            {"name": "r_thigh",    "parent": 1,  "pos": [round(-tx, 4), round(p_l_thigh[1], 4), round(p_l_thigh[2], 4)]},
            {"name": "r_calf",     "parent": 17, "pos": [round(-kx, 4), round(p_l_calf[1], 4), round(p_l_calf[2], 4)]},
            {"name": "r_foot",     "parent": 18, "pos": [round(-ax, 4), round(p_l_foot[1], 4), round(p_l_foot[2], 4)]},
        ]
        d["bones"] = new_bones
        d["normalizedHeight"] = TARGET_HEIGHT

        with open(path, "w", encoding="utf-8") as f_out:
            json.dump(d, f_out, separators=(",", ":"))
        print(
            f"Normalized & fixed {cid}: height={TARGET_HEIGHT}m, fixed_clav_verts={fixed_cnt}, "
            f"shoulder={new_bones[7]['pos']}, elbow={new_bones[8]['pos']}, wrist={new_bones[9]['pos']}"
        )


if __name__ == "__main__":
    process_all_models()
