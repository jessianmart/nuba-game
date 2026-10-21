import os
import json
import math
import struct
import zipfile
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import (
    OUT_DIR,
    ROSTER,
    CANONICAL_BONES,
    parse_nucc_chunks,
    decode_ndp3_mesh,
    decode_ntp3_texture,
    write_png_rgba,
)
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
            nrm = math.sqrt(sum(c * c for c in qloc)) or 1.0
            qloc = [round(c / nrm, 4) for c in qloc]
            bone_quat_frames[str(cb)].append(qloc)

        anm_p1_three = nucc_vec_to_three(anm_pos[p1_ci])
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


def extract_animations():
    print("=== Extracting Authentic Storm Animations for all 10 heroes ===")
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

                foot_y_cm = min(nucc_vec_to_three(bind_pos[cb_to_coord_idx[16]])[1], nucc_vec_to_three(bind_pos[cb_to_coord_idx[19]])[1]) - 8.15
                head_y_cm = nucc_vec_to_three(bind_pos[cb_to_coord_idx[5]])[1] + 24.5
                raw_h_cm = max(120.0, head_y_cm - foot_y_cm)

                databook_cm = DATABOOK_HEIGHTS_CM.get(cid, 155.0)
                target_h_m = round(databook_cm * CM_TO_WORLD, 3)
                world_scale = target_h_m / raw_h_cm

                # Load all animation chunks across all character packages:
                anm_bank = {}
                for suffix in ("bod1c", "bod1l", "skl1", "skl2", "skl3", "skl4", "bod1s", "awa"):
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
                            if len(r_trks) >= 12:
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
                run_candidates = [f"{cid}run1", f"{cid}run0", f"{cid}dsh0l"] if cid == "1itc" else [f"{cid}run0", f"{cid}run1", f"{cid}dsh0l"]
                run_seg = None
                run_name = f"{cid}run0"
                for cand in run_candidates:
                    seg = anm_bank.get(cand)
                    if seg:
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

                # 4. Authentic Primary Ninjutsu (`jutsu`) [Q]
                jutsu_segs = []
                if cid == "1nrt":
                    # Rasengan charge + rush from skl2
                    for k in (f"{cid}cha20", f"{cid}cha24"):
                        if k in anm_bank: jutsu_segs.append(anm_bank[k][:3])
                elif cid == "1ssk":
                    # Chidori rush from skl1
                    if f"{cid}cha10" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha10"][:3])
                elif cid == "1skr":
                    # Oukashou ground slam from skl2
                    if f"{cid}cha20" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1kks":
                    # Raikiri rush from skl1
                    for k in (f"{cid}cha10", f"{cid}cha14"):
                        if k in anm_bank: jutsu_segs.append(anm_bank[k][:3])
                elif cid == "1roc":
                    # Konoha Senpuu whirlwind kicks from skl1
                    if f"{cid}cha10" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha10"][:3])
                elif cid == "1itc":
                    # Amaterasu eye ignition from skl1
                    if f"{cid}cha10" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha10"][:3])
                elif cid == "1gar":
                    # Sabaku Kyuu sand coffin grasp from skl1
                    if f"{cid}cha10" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha10"][:3])
                elif cid == "1hnt":
                    # Shugohakke 64 palms chakra rotation from skl1
                    if f"{cid}cha10" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha10"][:3])
                elif cid == "1nej":
                    # Hakkeshou Kaiten 360 rotation from skl2
                    if f"{cid}cha20" in anm_bank: jutsu_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1jry":
                    # Gamayu Endan / flame burst from skl2
                    for k in (f"{cid}cha20", f"{cid}cha22"):
                        if k in anm_bank: jutsu_segs.append(anm_bank[k][:3])

                if not jutsu_segs:
                    jutsu_segs = [v[:3] for k, v in sorted(anm_bank.items()) if "cha1" in k and len(v[1]) >= 30][:2]

                char_clips["jutsu"] = {
                    "name": f"{cid}_jutsu_primary",
                    "source": "authentic_apk_skl",
                    **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, jutsu_segs, world_scale, foot_y_cm, loop=False, max_frames=32),
                }

                # 5. Authentic Secondary Ninjutsu (`jutsu2`) [E]
                jutsu2_segs = []
                if cid == "1nrt":
                    # Kage Bunshin cross hand seal stance from bod1s
                    for k in (f"{cid}sup00", f"{cid}dsc00"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1ssk":
                    # Katon Goukakyuu fire breath from skl2
                    if f"{cid}cha20" in anm_bank: jutsu2_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1skr":
                    # Ninjutsu Medico healing hand stance from bod1s
                    for k in (f"{cid}sup01", f"{cid}sup00"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1kks":
                    # Suiton Suiryuudan water dragon from skl2
                    if f"{cid}cha20" in anm_bank: jutsu2_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1roc":
                    # Omote Renge high-speed rush from bod1s
                    for k in (f"{cid}sup00", f"{cid}dsc00"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1itc":
                    # Crow Clone explosion / Katon from bod1s
                    for k in (f"{cid}sup03", f"{cid}sup00"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1gar":
                    # Suna no Tate sand shield absolute defense from bod1s
                    for k in (f"{cid}sup00", f"{cid}sup01"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1hnt":
                    # Twin Lion Fists strike from skl2
                    if f"{cid}cha20" in anm_bank: jutsu2_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1nej":
                    # Hakke Kuusho air palm blast from bod1s
                    for k in (f"{cid}sup00", f"{cid}sup01"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break
                elif cid == "1jry":
                    # Hari Jizo / needle hair stance from bod1s
                    for k in (f"{cid}sup00", f"{cid}dsc00"):
                        if k in anm_bank:
                            jutsu2_segs.append(anm_bank[k][:3])
                            break

                if not jutsu2_segs:
                    jutsu2_segs = [v[:3] for k, v in sorted(anm_bank.items()) if ("sup" in k or "cha2" in k) and len(v[1]) >= 20][:1]

                char_clips["jutsu2"] = {
                    "name": f"{cid}_jutsu_secondary",
                    "source": "authentic_apk_skl",
                    **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, jutsu2_segs, world_scale, foot_y_cm, loop=False, max_frames=32),
                }

                # 6. Authentic Ultimate Ougi (`ult`) [R]
                ult_segs = []
                if cid == "1nrt":
                    # Oodama Rasengan barrage from skl1
                    for k in (f"{cid}cha10", f"{cid}cha14"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1ssk":
                    # Kirin / Chidori Blade from skl3
                    for k in (f"{cid}cha30", f"{cid}cha34"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1skr":
                    # Inner Sakura Byakugou mega punch from skl1
                    for k in (f"{cid}cha10", f"{cid}cha14"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1kks":
                    # Kamui Mangekyou space collapse from skl3
                    if f"{cid}cha30" in anm_bank: ult_segs.append(anm_bank[f"{cid}cha30"][:3])
                elif cid == "1roc":
                    # Ura Renge 8 Gates Inner Hidden Lotus from skl2
                    for k in (f"{cid}cha20", f"{cid}cha24"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1itc":
                    # Tsukuyomi / Susanoo from skl2
                    if f"{cid}cha20" in anm_bank: ult_segs.append(anm_bank[f"{cid}cha20"][:3])
                elif cid == "1gar":
                    # Sabaku Taisou Sand Tsunami from skl2
                    for k in (f"{cid}cha20", f"{cid}cha22"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1hnt":
                    # Supreme 8 Trigrams Twin Lion Fists from skl2
                    if f"{cid}cha21" in anm_bank: ult_segs.append(anm_bank[f"{cid}cha21"][:3])
                elif cid == "1nej":
                    # 64 Palms from skl1
                    for k in (f"{cid}cha10", f"{cid}cha14"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])
                elif cid == "1jry":
                    # Chou Oodama Rasengan from skl1
                    for k in (f"{cid}cha10", f"{cid}cha14"):
                        if k in anm_bank: ult_segs.append(anm_bank[k][:3])

                if not ult_segs:
                    ult_segs = [v[:3] for k, v in sorted(anm_bank.items()) if ("cha3" in k or "cha2" in k or "cha1" in k) and len(v[1]) >= 30][:2]

                char_clips["ult"] = {
                    "name": f"{cid}_ult_ougi",
                    "source": "authentic_apk_ougi",
                    **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, ult_segs, world_scale, foot_y_cm, loop=False, max_frames=36),
                }

                # 7. Downed / Knockout Death Animation (bod1c.xfbin: dow0 / dow1 / dmg0f)
                down_seg = anm_bank.get(f"{cid}dow0") or anm_bank.get(f"{cid}dow1") or anm_bank.get(f"{cid}dmg0f")
                if down_seg:
                    char_clips["down"] = {
                        "name": f"{cid}dow0",
                        "source": f"{cid}bod1c.xfbin",
                        **bake_fk_clip_to_threejs(coords, parents, bind_pos, bind_rot, cb_to_coord_idx, [down_seg[:3]], world_scale, foot_y_cm, loop=False, max_frames=24),
                    }

                all_animations[cid] = char_clips
                print(f"[{cid}] {cname:16s}: baked clips { {k: v['numFrames'] for k, v in char_clips.items()} }")

    out_anm_path = os.path.join(OUT_DIR, "data", "animations.json")
    with open(out_anm_path, "w", encoding="utf-8") as af:
        json.dump(all_animations, af, separators=(",", ":"))
    print(f"-> Successfully saved animations.json ({len(all_animations)} heroes)")


def extract_vfx_and_models():
    print("\n=== Extracting Authentic Storm 3D Skill VFX & Meshes from APK ===")
    os.makedirs(os.path.join(OUT_DIR, "skills"), exist_ok=True)
    skill_vfx_data = {}

    with zipfile.ZipFile(APK_PATH, "r") as z:
        # 1. Extract common Storm VFX models & textures from installTime.awb -> 1efcmn.xfbin
        with z.open("assets/data/sim/installTime.awb") as f_inst:
            cpk = parse_utf(f_inst.read(65536), 16)[0]
            f_inst.seek(cpk["TocOffset"])
            toc = parse_utf(f_inst.read(cpk["TocSize"]), 16)
            r_cmn = next((r for r in toc if r["FileName"] == "1efcmn.xfbin"), None)
            if r_cmn:
                f_inst.seek(cpk["TocOffset"] + r_cmn["FileOffset"])
                raw_cmn = decompress_crilayla(f_inst.read(r_cmn["FileSize"]))
                chunks, _, _, _, _ = parse_nucc_chunks(raw_cmn)

                cmn_textures = {}
                for tname, ch_name, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkTexture" and b"NTP3" in pay:
                        ntp_pos = pay.find(b"NTP3")
                        try:
                            w, h, rgba, _ = decode_ntp3_texture(pay, ntp_pos + 16, max_dim=256)
                            rel = f"skills/{ch_name}.png"
                            out_p = os.path.join(OUT_DIR, "skills", f"{ch_name}.png")
                            write_png_rgba(out_p, w, h, rgba)
                            cmn_textures[ch_name] = rel
                        except Exception as e:
                            pass

                cmn_models = {}
                for tname, ch_name, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkModel" and b"NDP3" in pay:
                        try:
                            subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
                            vcount = sum(len(s["positions"]) // 3 for s in subs)
                            if vcount > 0:
                                for s in subs:
                                    matched_tex = None
                                    if ch_name in cmn_textures:
                                        matched_tex = cmn_textures[ch_name]
                                    else:
                                        c1 = ch_name.rsplit("_", 1)[0]
                                        if c1 in cmn_textures:
                                            matched_tex = cmn_textures[c1]
                                        else:
                                            c2 = ch_name.replace("1efc_bd_", "1efc_").rsplit("_", 1)[0]
                                            if c2 in cmn_textures:
                                                matched_tex = cmn_textures[c2]
                                            else:
                                                for k in sorted(cmn_textures.keys(), key=len, reverse=True):
                                                    if k in ch_name:
                                                        matched_tex = cmn_textures[k]
                                                        break
                                    s["texture"] = matched_tex or cmn_textures.get("1efc_chakra00") or next(iter(cmn_textures.values()), None)
                                cmn_models[ch_name] = subs
                        except Exception as e:
                            pass

                skill_vfx_data["common"] = {
                    "source": "1efcmn.xfbin",
                    "textures": cmn_textures,
                    "models": cmn_models,
                }
                print(f"Extracted common VFX: {len(cmn_models)} 3D models, {len(cmn_textures)} textures")

        # 2. Extract hero-specific VFX from data.awb ({cid}eff1.xfbin)
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            for cid, cname, _, _, _ in ROSTER:
                hero_vfx = {
                    "source": f"{cid}eff1.xfbin",
                    "textures": [],
                    "meshes": [],
                    "models": {},
                }
                fn_eff = f"{cid}eff1.xfbin"
                if fn_eff in toc_map:
                    r = toc_map[fn_eff]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, _, _, _, _ = parse_nucc_chunks(raw)

                    eff_texs = {}
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkTexture" and b"NTP3" in pay:
                            ntp_pos = pay.find(b"NTP3")
                            try:
                                w, h, rgba, _ = decode_ntp3_texture(pay, ntp_pos + 16, max_dim=256)
                                rel = f"skills/{cid}_{ch_name}.png"
                                out_p = os.path.join(OUT_DIR, "skills", f"{cid}_{ch_name}.png")
                                write_png_rgba(out_p, w, h, rgba)
                                eff_texs[ch_name] = rel
                            except Exception:
                                pass

                    eff_meshes = []
                    eff_models = {}
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkModel" and b"NDP3" in pay and "shadow" not in ch_name.lower():
                            try:
                                subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
                                vcount = sum(len(s["positions"]) // 3 for s in subs)
                                if vcount > 0:
                                    for sm in subs:
                                        sm["texture"] = next(iter(eff_texs.values()), None)
                                        eff_meshes.append(sm)
                                    eff_models[ch_name] = subs
                            except Exception:
                                pass

                    hero_vfx["textures"] = list(eff_texs.values())
                    hero_vfx["meshes"] = eff_meshes[:6]
                    hero_vfx["models"] = eff_models

                # Map relevant common Storm 3D models into hero's skill kit
                if "common" in skill_vfx_data:
                    cmn_m = skill_vfx_data["common"]["models"]
                    if cid == "1nrt":
                        # Rasengan chakra sphere & smoke puff
                        if "1efc_chakra00" in cmn_m: hero_vfx["models"]["rasengan"] = cmn_m["1efc_chakra00"]
                        if "1efc_smk01" in cmn_m: hero_vfx["models"]["smoke"] = cmn_m["1efc_smk01"]
                        if "1efc_chakra10a" in cmn_m: hero_vfx["models"]["giant_rasengan"] = cmn_m["1efc_chakra10a"]
                    elif cid == "1ssk":
                        # Chidori lightning sparks & Katon fireball
                        if "1efc_spk01" in cmn_m: hero_vfx["models"]["chidori_spark"] = cmn_m["1efc_spk01"]
                        if "1efc_fire03" in cmn_m: hero_vfx["models"]["fireball"] = cmn_m["1efc_fire03"]
                    elif cid == "1skr":
                        # Ground shatter & chakra healing
                        if "1efc_brk01_02" in cmn_m: hero_vfx["models"]["shatter"] = cmn_m["1efc_brk01_02"]
                        if "1efc_chakra01" in cmn_m: hero_vfx["models"]["heal_chakra"] = cmn_m["1efc_chakra01"]
                    elif cid == "1kks":
                        # Raikiri sparks & Suiton water
                        if "1efc_spk03" in cmn_m: hero_vfx["models"]["raikiri_spark"] = cmn_m["1efc_spk03"]
                        if "1efc_wtr02" in cmn_m: hero_vfx["models"]["water_dragon"] = cmn_m["1efc_wtr02"]
                    elif cid == "1roc":
                        # Konoha whirlwind & Omote Renge air tornado
                        if "1efc_wind01" in cmn_m: hero_vfx["models"]["whirlwind"] = cmn_m["1efc_wind01"]
                        if "1efc_wind02" in cmn_m: hero_vfx["models"]["air_tornado"] = cmn_m["1efc_wind02"]
                        if "1efc_leaf01" in cmn_m: hero_vfx["models"]["leaf_flurry"] = cmn_m["1efc_leaf01"]
                    elif cid == "1itc":
                        # Amaterasu black flames & Crow clone smoke
                        if "1efc_fire03" in cmn_m: hero_vfx["models"]["amaterasu_flame"] = cmn_m["1efc_fire03"]
                        if "1efc_smk01" in cmn_m: hero_vfx["models"]["crow_smoke"] = cmn_m["1efc_smk01"]
                    elif cid == "1gar":
                        # Sand shield & sand coffin
                        if "1efc_nor_dst01" in cmn_m: hero_vfx["models"]["sand_dust"] = cmn_m["1efc_nor_dst01"]
                    elif cid == "1hnt":
                        # Shugohakke chakra rotation & twin lion fists
                        if "1efc_wind01" in cmn_m: hero_vfx["models"]["palms_rotation"] = cmn_m["1efc_wind01"]
                        if "1efc_chakra00" in cmn_m: hero_vfx["models"]["lion_chakra"] = cmn_m["1efc_chakra00"]
                    elif cid == "1nej":
                        # Kaiten 360 rotation dome & air palm
                        if "1efc_wind01" in cmn_m: hero_vfx["models"]["kaiten_dome"] = cmn_m["1efc_wind01"]
                        if "1efc_slash01" in cmn_m: hero_vfx["models"]["air_palm"] = cmn_m["1efc_slash01"]
                    elif cid == "1jry":
                        # Gamayu Endan oil fire & spiky needle
                        if "1efc_fire03" in cmn_m: hero_vfx["models"]["toad_fire"] = cmn_m["1efc_fire03"]
                        if "1efc_chakra10a" in cmn_m: hero_vfx["models"]["chou_rasengan"] = cmn_m["1efc_chakra10a"]

                # If hero has no primary meshes yet, fall back to first assigned common model
                if not hero_vfx["meshes"] and hero_vfx["models"]:
                    first_m = next(iter(hero_vfx["models"].values()))
                    hero_vfx["meshes"] = first_m[:4]

                skill_vfx_data[cid] = hero_vfx
                print(f"[{cid}] {cname:16s}: {len(hero_vfx['meshes'])} mesh parts, models: {list(hero_vfx['models'].keys())}")

        # 3. Also extract Naruto's special Rasengan models from installTimeDisc.awb -> 1nrtspl1e1.xfbin
        with z.open("assets/data/disc/installTimeDisc.awb") as f_disc:
            cpk = parse_utf(f_disc.read(65536), 16)[0]
            f_disc.seek(cpk["TocOffset"])
            toc = parse_utf(f_disc.read(cpk["TocSize"]), 16)
            r_spl = next((r for r in toc if r["FileName"] == "1nrtspl1e1.xfbin"), None)
            if r_spl:
                f_disc.seek(cpk["TocOffset"] + r_spl["FileOffset"])
                raw_spl = decompress_crilayla(f_disc.read(r_spl["FileSize"]))
                chunks, _, _, _, _ = parse_nucc_chunks(raw_spl)
                for tname, ch_name, cmap, pay, pbase in chunks:
                    if tname == "nuccChunkModel" and b"NDP3" in pay and "08" in ch_name:
                        try:
                            subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
                            if subs and "1nrt" in skill_vfx_data:
                                skill_vfx_data["1nrt"]["models"]["spl_rasengan"] = subs
                                print(f"Added authentic spl_rasengan to 1nrt ({sum(len(s['positions'])//3 for s in subs)} verts)")
                        except Exception:
                            pass

    out_vfx_path = os.path.join(OUT_DIR, "skills", "skill_vfx.json")
    with open(out_vfx_path, "w", encoding="utf-8") as vf:
        json.dump(skill_vfx_data, vf, separators=(",", ":"))
    print(f"-> Successfully saved skill_vfx.json ({len(skill_vfx_data)} entries)")


if __name__ == "__main__":
    extract_animations()
    extract_vfx_and_models()
