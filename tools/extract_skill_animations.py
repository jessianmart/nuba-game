import zipfile
import struct
import json
import os
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import (
    OUT_DIR,
    ROSTER,
    parse_nucc_chunks,
    decode_ntp3_texture,
    decode_ndp3_mesh,
    write_png_rgba,
)
from tools.test_anm_names import parse_anm_tracks, quat_to_euler_rad
from tools.inspect_anm_and_eff import quat_mul, quat_inv


def sample_clip_curves(trks, ref_trks=None, max_samples=16):
    # Convert quaternion tracks into compact keyframe curves for each canonical bone
    # Relative to ref_trks[cb][0] (if provided, e.g. idle frame 0) or trks[cb][0]
    sampled_bones = {}
    any_track = next(iter(trks.values()), [])
    total_k = max((len(v) for v in trks.values()), default=1)
    step = max(1, total_k // max_samples)
    frame_indices = list(range(0, total_k, step))
    if frame_indices[-1] != total_k - 1:
        frame_indices.append(total_k - 1)

    for cb, qs in trks.items():
        if not qs:
            continue
        q_base = ref_trks[cb][0] if (ref_trks and cb in ref_trks and ref_trks[cb]) else qs[0]
        q_base_inv = quat_inv(q_base)
        frames = []
        for fi in frame_indices:
            q_curr = qs[min(fi, len(qs) - 1)]
            dq = quat_mul(q_base_inv, q_curr)
            rx, ry, rz = quat_to_euler_rad(dq)
            # Clamp extreme Euler wrap-around artifacts
            rx = max(-1.6, min(1.6, rx))
            ry = max(-1.6, min(1.6, ry))
            rz = max(-1.8, min(1.8, rz))
            frames.append([round(rx, 3), round(ry, 3), round(rz, 3)])
        sampled_bones[str(cb)] = frames
    return {"numFrames": len(frame_indices), "bones": sampled_bones}


def extract_skills_and_animations():
    os.makedirs(os.path.join(OUT_DIR, "data"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "skills"), exist_ok=True)

    all_animations = {}
    skill_vfx_models = {}

    with zipfile.ZipFile(APK_PATH, "r") as z:
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            for cid, cname, _, _, _ in ROSTER:
                char_clips = {}
                idle_trks = None

                # 1. Core movement animations from {cid}bod1c.xfbin
                fn_c = f"{cid}bod1c.xfbin"
                if fn_c in toc_map:
                    r = toc_map[fn_c]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkAnm":
                            if ch_name == f"{cid}nut0":
                                nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                                idle_trks = trks
                                char_clips["idle"] = {
                                    "name": ch_name,
                                    "source": fn_c,
                                    "loop": True,
                                    **sample_clip_curves(trks, trks, max_samples=14),
                                }
                            elif ch_name == f"{cid}dsh0l":
                                nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                                char_clips["run"] = {
                                    "name": ch_name,
                                    "source": fn_c,
                                    "loop": True,
                                    **sample_clip_curves(trks, idle_trks or trks, max_samples=12),
                                }

                # 2. Attack combo animations from {cid}bod1l.xfbin
                fn_l = f"{cid}bod1l.xfbin"
                if fn_l in toc_map:
                    r = toc_map[fn_l]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkAnm" and ch_name == f"{cid}cmb00":
                            nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                            char_clips["attack"] = {
                                "name": ch_name,
                                "source": fn_l,
                                "loop": False,
                                **sample_clip_curves(trks, idle_trks or trks, max_samples=14),
                            }
                            break

                # 3. Skill 1 (Ninjutsu) animations from {cid}skl1.xfbin
                fn_s1 = f"{cid}skl1.xfbin"
                if fn_s1 in toc_map:
                    r = toc_map[fn_s1]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkAnm" and ch_name in (f"{cid}cha10", f"{cid}cha11"):
                            nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                            if len(trks) >= 6:
                                char_clips["jutsu"] = {
                                    "name": ch_name,
                                    "source": fn_s1,
                                    "loop": False,
                                    **sample_clip_curves(trks, idle_trks or trks, max_samples=14),
                                }
                                if ch_name == f"{cid}cha10":
                                    break

                # 4. Skill 2 / Ultimate Jutsu animations from {cid}skl2.xfbin
                fn_s2 = f"{cid}skl2.xfbin"
                if fn_s2 in toc_map:
                    r = toc_map[fn_s2]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkAnm" and ch_name.startswith(f"{cid}cha2"):
                            nf, lp, trks = parse_anm_tracks(pay, pbase, sci, smaps, stypes, snames)
                            if len(trks) >= 6:
                                char_clips["ult"] = {
                                    "name": ch_name,
                                    "source": fn_s2,
                                    "loop": False,
                                    **sample_clip_curves(trks, idle_trks or trks, max_samples=14),
                                }
                                break

                # 5. Extract 3D Skill Effect Models & Textures from {cid}eff1.xfbin
                fn_eff = f"{cid}eff1.xfbin"
                if fn_eff in toc_map:
                    r = toc_map[fn_eff]
                    f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = decompress_crilayla(f_dat.read(r["FileSize"]))
                    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                    eff_texs = {}
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkTexture" and b"NTP3" in pay:
                            ntp_pos = pay.find(b"NTP3")
                            w, h, rgba, _ = decode_ntp3_texture(pay, ntp_pos + 16, max_dim=256)
                            rel = f"skills/{cid}_{ch_name}.png"
                            write_png_rgba(os.path.join(OUT_DIR, "skills", f"{cid}_{ch_name}.png"), w, h, rgba)
                            eff_texs[ch_name] = rel
                    eff_meshes = []
                    for tname, ch_name, cmap, pay, pbase in chunks:
                        if tname == "nuccChunkModel" and b"NDP3" in pay and "shadow" not in ch_name.lower():
                            subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
                            for sm in subs:
                                sm["texture"] = next(iter(eff_texs.values()), None)
                                eff_meshes.append(sm)
                    if eff_meshes or eff_texs:
                        skill_vfx_models[cid] = {
                            "source": fn_eff,
                            "textures": list(eff_texs.values()),
                            "meshes": eff_meshes[:4],
                        }

                all_animations[cid] = char_clips
                print(f"Extracted animations for {cid}: {list(char_clips.keys())}")

    with open(os.path.join(OUT_DIR, "data", "animations.json"), "w", encoding="utf-8") as af:
        json.dump(all_animations, af, separators=(",", ":"))
    with open(os.path.join(OUT_DIR, "skills", "skill_vfx.json"), "w", encoding="utf-8") as vf:
        json.dump(skill_vfx_models, vf, separators=(",", ":"))
    print("Saved animations.json and skill_vfx.json!")


if __name__ == "__main__":
    extract_skills_and_animations()
