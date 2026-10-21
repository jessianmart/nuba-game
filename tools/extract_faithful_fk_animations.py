import os
import json
import math
import struct
import zipfile
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import OUT_DIR, ROSTER, CANONICAL_BONES, parse_nucc_chunks
from tools.test_fk_anm_pose import parse_full_anm, evaluate_fk, quat_mul, quat_inv
from tools.apply_databook_heights import DATABOOK_HEIGHTS_CM, CM_TO_WORLD

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
    return (q[0], q[2], -q[1], q[3])


def bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, clip_segments, world_scale, min_y_cm, loop=False, max_frames=28):
    # Collect all raw frames across chained segments [(nf, r_trks, p_trks), ...]
    raw_frames = []
    for nf, r_trks, p_trks in clip_segments:
        actual_nf = max(1, max((len(v) for v in r_trks.values()), default=nf))
        for fi in range(actual_nf):
            raw_frames.append((fi, r_trks, p_trks))

    if not raw_frames:
        return None

    total_f = len(raw_frames)
    if total_f <= max_frames:
        sampled_indices = list(range(total_f))
    else:
        sampled_indices = [int(round(i * (total_f - 1) / (max_frames - 1))) for i in range(max_frames)]

    p1_ci = cb_to_coord_idx.get(1, 2)
    bind_p1_three = nucc_vec_to_three(bind_pos[p1_ci])

    pelvis_pos_frames = []
    bone_quat_frames = {str(cb): [] for cb in range(1, 20)}

    for idx in sampled_indices:
        fi, r_trks, p_trks = raw_frames[idx]
        anm_pos, anm_rot = evaluate_fk(coords, parents, r_trks, p_trks, frame_idx=fi)

        dq_three = {0: (0.0, 0.0, 0.0, 1.0)}
        for cb in range(1, 20):
            ci = cb_to_coord_idx.get(cb)
            if ci is not None:
                dq_nucc = quat_mul(anm_rot[ci], quat_inv(bind_rot[ci]))
                dq_three[cb] = nucc_quat_to_three(dq_nucc)
            else:
                p_cb = CANONICAL_BONES[cb][1]
                dq_three[cb] = dq_three.get(p_cb, (0.0, 0.0, 0.0, 1.0))

        for cb in range(1, 20):
            p_cb = CANONICAL_BONES[cb][1]
            qloc = quat_mul(quat_inv(dq_three[p_cb]), dq_three[cb])
            # Normalize quaternion
            nrm = math.sqrt(sum(c * c for c in qloc)) or 1.0
            qloc = [round(c / nrm, 4) for c in qloc]
            bone_quat_frames[str(cb)].append(qloc)

        anm_p1_three = nucc_vec_to_three(anm_pos[p1_ci])
        # Clamp horizontal root motion & vertical aerial leap so character stays inside MOBA camera frame
        dx = max(-18.0, min(18.0, anm_p1_three[0] - bind_p1_three[0])) * world_scale
        raw_y_cm = max(12.0, min((bind_p1_three[1] - min_y_cm) + 38.0, anm_p1_three[1] - min_y_cm))
        y_abs = raw_y_cm * world_scale
        dz = max(-22.0, min(22.0, anm_p1_three[2] - bind_p1_three[2])) * world_scale
        pelvis_pos_frames.append([round(dx, 3), round(y_abs, 3), round(dz, 3)])

    return {
        "numFrames": len(sampled_indices),
        "loop": loop,
        "pelvisPos": pelvis_pos_frames,
        "bones": bone_quat_frames,
    }


def extract_all_faithful_animations():
    all_animations = {}

    with zipfile.ZipFile(APK_PATH, "r") as z:
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            for cid, cname, _, _, _ in ROSTER:
                bod_fn = f"{cid}bod1.xfbin"
                if bod_fn not in toc_map:
                    continue
                rb = toc_map[bod_fn]
                f_dat.seek(cpk["TocOffset"] + rb["FileOffset"])
                raw_b = decompress_crilayla(f_dat.read(rb["FileSize"]))
                chunks_b, _, _, _, _ = parse_nucc_chunks(raw_b)

                char_clump_pay, char_pbase = next(
                    ((c[3], c[4]) for c in chunks_b if c[0] == "nuccChunkClump" and c[1].lower().startswith(cid)),
                    next((c[3], c[4]) for c in chunks_b if c[0] == "nuccChunkClump"),
                )
                coords = [(c[1], struct.unpack(">9f", c[3][:36])) for c in chunks_b if c[0] == "nuccChunkCoord" and c[4] == char_pbase]
                _, nbones, _ = struct.unpack(">IHH", char_clump_pay[:8])
                parents = struct.unpack(f">{nbones}h", char_clump_pay[8 : 8 + nbones * 2])

                cb_to_coord_idx = {}
                for i, (bname, _) in enumerate(coords):
                    parts = bname.lower().split(" ", 1)
                    suf = parts[1].strip() if len(parts) > 1 else bname.lower()
                    for cb, target_suf in CANONICAL_SUFFIX.items():
                        if suf == target_suf and cb not in cb_to_coord_idx:
                            cb_to_coord_idx[cb] = i

                bind_pos, bind_rot = evaluate_fk(coords, parents)

                # Update character model JSON with exact nuccChunkCoord FK joint positions and Databook height!
                model_path = os.path.join(OUT_DIR, "models", f"{cid}.json")
                with open(model_path, "r", encoding="utf-8") as mf:
                    mdata = json.load(mf)

                # Measure current model height in Three.js units
                min_y_m = min(min(sm["positions"][1::3]) for sm in mdata["meshes"] if sm["positions"])
                max_y_m = max(max(sm["positions"][1::3]) for sm in mdata["meshes"] if sm["positions"])
                cur_h_m = max(0.01, max_y_m - min_y_m)

                # Also compute raw cm height from bind_pos head + top vs foot
                foot_y_cm = min(nucc_vec_to_three(bind_pos[cb_to_coord_idx[16]])[1], nucc_vec_to_three(bind_pos[cb_to_coord_idx[19]])[1]) - 8.15
                head_y_cm = nucc_vec_to_three(bind_pos[cb_to_coord_idx[5]])[1] + 24.5
                raw_h_cm = max(120.0, head_y_cm - foot_y_cm)

                databook_cm = DATABOOK_HEIGHTS_CM.get(cid, 155.0)
                target_h_m = round(databook_cm * CM_TO_WORLD, 3)
                world_scale = target_h_m / raw_h_cm
                mesh_ratio = target_h_m / cur_h_m

                for sm in mdata["meshes"]:
                    pos = sm["positions"]
                    for idx in range(0, len(pos), 3):
                        pos[idx] = round(pos[idx] * mesh_ratio, 4)
                        pos[idx + 1] = round((pos[idx + 1] - min_y_m) * mesh_ratio, 4)
                        pos[idx + 2] = round(pos[idx + 2] * mesh_ratio, 4)

                # Set bones[cb].pos to exact nuccChunkCoord FK bind positions in Three.js world meters!
                mdata["bones"][0]["pos"] = [0.0, 0.0, 0.0]
                for cb in range(1, 20):
                    ci = cb_to_coord_idx.get(cb)
                    if ci is not None:
                        vx, vy, vz = nucc_vec_to_three(bind_pos[ci])
                        mdata["bones"][cb]["pos"] = [
                            round(vx * world_scale, 4),
                            round((vy - foot_y_cm) * world_scale, 4),
                            round(vz * world_scale, 4),
                        ]
                mdata["armBindZ"] = 0.0
                mdata["databookHeightCm"] = databook_cm
                mdata["worldHeight"] = target_h_m

                with open(model_path, "w", encoding="utf-8") as mf:
                    json.dump(mdata, mf, separators=(",", ":"))

                # Load all animation chunks from bod1c, bod1l, bod1s, bod1r, skl1, skl2
                anm_bank = {}
                for suffix in ("bod1c", "bod1l", "bod1s", "bod1r", "skl1", "skl2"):
                    fn = f"{cid}{suffix}.xfbin"
                    if fn not in toc_map:
                        continue
                    r = toc_map[fn]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkAnm":
                            nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci, smaps, stypes, snames)
                            if len(r_trks) >= 12 or "spk0" in ch_name.lower() or "sup0" in ch_name.lower():
                                anm_bank[ch_name.lower()] = (nf, r_trks, p_trks, suffix)

                char_clips = {}

                # 1. Idle (nut0)
                idle_seg = anm_bank.get(f"{cid}nut0") or anm_bank.get(f"{cid}nut0f") or next((v for k, v in anm_bank.items() if "nut" in k), None)
                if idle_seg:
                    char_clips["idle"] = {
                        "name": f"{cid}nut0",
                        "source": f"{cid}bod1c.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [idle_seg[:3]], world_scale, foot_y_cm, loop=True, max_frames=20),
                    }

                # 2. Authentic Ground Ninja Run (run1 / run0) & Speed Dash (dsh0l)
                # For heroes like Itachi (1itc), run0 is stiff upper-body coat idle, while run1 contains the full 19-bone ninja leg run cycle!
                run_candidates = [f"{cid}run1", f"{cid}run0", f"{cid}dsh0l"] if cid == "1itc" else [f"{cid}run0", f"{cid}run1", f"{cid}dsh0l"]
                run_seg = None
                run_name = f"{cid}run0"
                for cand in run_candidates:
                    seg = anm_bank.get(cand)
                    if seg:
                        # Check if bone 14 or 17 has animated rotation
                        r_trks = seg[1]
                        if 14 in r_trks or 17 in r_trks or len(r_trks) >= 16:
                            run_seg = seg
                            run_name = cand
                            break
                if not run_seg:
                    run_seg = anm_bank.get(f"{cid}run0") or anm_bank.get(f"{cid}run1") or anm_bank.get(f"{cid}dsh0l")
                    run_name = f"{cid}run0"

                if run_seg:
                    char_clips["run"] = {
                        "name": run_name,
                        "source": f"{cid}bod1c.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [run_seg[:3]], world_scale, foot_y_cm, loop=True, max_frames=20),
                    }
                dash_seg = anm_bank.get(f"{cid}dsh0l") or run_seg
                if dash_seg:
                    char_clips["dash"] = {
                        "name": f"{cid}dsh0l",
                        "source": f"{cid}bod1c.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [dash_seg[:3]], world_scale, foot_y_cm, loop=True, max_frames=16),
                    }

                # 3. Taijutsu Combo Attacks (attack, attack2, attack3 from bod1l.xfbin)
                cmb_candidates = [
                    (k, v) for k, v in sorted(anm_bank.items())
                    if k.startswith(f"{cid}cmb") and len(v[1]) >= 45
                ]
                if len(cmb_candidates) < 3:
                    cmb_candidates = [
                        (k, v) for k, v in sorted(anm_bank.items())
                        if (k.startswith(f"{cid}cmb") or k.startswith(f"{cid}cma")) and len(v[1]) >= 28
                    ]

                for idx_c, clip_key in enumerate(("attack", "attack2", "attack3")):
                    if idx_c < len(cmb_candidates):
                        ck_name, seg = cmb_candidates[idx_c]
                        char_clips[clip_key] = {
                            "name": ck_name,
                            "source": f"{cid}bod1l.xfbin",
                            **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [seg[:3]], world_scale, foot_y_cm, loop=False, max_frames=24),
                        }

                # 4. Skill 1 / Ninjutsu (skl1.xfbin: chain cha10 + cha11 + cha14 or longest cha1* sequence)
                skl1_segs = []
                for k in (f"{cid}cha10", f"{cid}cha11", f"{cid}cha14"):
                    if k in anm_bank and len(anm_bank[k][1]) >= 30:
                        skl1_segs.append(anm_bank[k][:3])
                if not skl1_segs:
                    skl1_all = [v[:3] for k, v in sorted(anm_bank.items()) if v[3] == "skl1" and "cut" not in k and "chd" not in k]
                    skl1_segs = skl1_all[:2] if skl1_all else ([idle_seg[:3]] if idle_seg else [])
                if skl1_segs:
                    char_clips["jutsu"] = {
                        "name": f"{cid}cha10_full",
                        "source": f"{cid}skl1.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, skl1_segs, world_scale, foot_y_cm, loop=False, max_frames=32),
                    }

                # 4b. Secondary Ninjutsu (bod1s.xfbin: sup00 support jutsu or cat10 / cha11)
                sup_seg = anm_bank.get(f"{cid}sup00") or anm_bank.get(f"{cid}cat10") or anm_bank.get(f"{cid}cha11") or (skl1_segs[0] if skl1_segs else None)
                if sup_seg:
                    src_suffix = sup_seg[3] if len(sup_seg) > 3 else "bod1s"
                    char_clips["jutsu2"] = {
                        "name": f"{cid}sup00",
                        "source": f"{cid}{src_suffix}.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [sup_seg[:3]], world_scale, foot_y_cm, loop=False, max_frames=32),
                    }

                # 5. Skill 2 / Ultimate Jutsu (skl2.xfbin: chain cha20 + cha21 + cha22/cha24)
                skl2_segs = []
                for k in (f"{cid}cha20", f"{cid}cha21", f"{cid}cha22", f"{cid}cha24"):
                    if k in anm_bank and anm_bank[k][0] >= 8 and len(anm_bank[k][1]) >= 30:
                        skl2_segs.append(anm_bank[k][:3])
                if not skl2_segs:
                    skl2_all = [v[:3] for k, v in sorted(anm_bank.items()) if v[3] == "skl2" and "chd" not in k]
                    skl2_segs = skl2_all[:2] if skl2_all else skl1_segs
                if skl2_segs:
                    char_clips["ult"] = {
                        "name": f"{cid}cha20_full",
                        "source": f"{cid}skl2.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, skl2_segs, world_scale, foot_y_cm, loop=False, max_frames=36),
                    }

                # 6. Downed / Knockout Death Animation (bod1c.xfbin: dow0 / dow1 / dmg0f)
                down_seg = anm_bank.get(f"{cid}dow0") or anm_bank.get(f"{cid}dow1") or anm_bank.get(f"{cid}dmg0f")
                if down_seg:
                    char_clips["down"] = {
                        "name": f"{cid}dow0",
                        "source": f"{cid}bod1c.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [down_seg[:3]], world_scale, foot_y_cm, loop=False, max_frames=24),
                    }

                # 7. Authentic Chakra Charge Crouch Stance (bod1c.xfbin or bod1r.xfbin: spk0 / spk0f)
                spk_seg = anm_bank.get(f"{cid}spk0") or anm_bank.get(f"{cid}spk0f")
                if spk_seg:
                    src_suffix = spk_seg[3] if len(spk_seg) > 3 else "bod1c"
                    char_clips["charge"] = {
                        "name": f"{cid}spk0",
                        "source": f"{cid}{src_suffix}.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [spk_seg[:3]], world_scale, foot_y_cm, loop=True, max_frames=20),
                    }

                all_animations[cid] = char_clips
                print(f"[{cid}] {cname:16s} (Databook {databook_cm}cm -> {target_h_m:.2f}m): baked FK clips { {k: v['numFrames'] for k, v in char_clips.items()} }")

    out_anm_path = os.path.join(OUT_DIR, "data", "animations.json")
    with open(out_anm_path, "w", encoding="utf-8") as af:
        json.dump(all_animations, af, separators=(",", ":"))
    print(f"Saved faithful FK animations to {out_anm_path}!")


if __name__ == "__main__":
    extract_all_faithful_animations()
