"""W2.2: extract 12th hero (Orochimaru / 1orc) model+anims+skill_vfx end-to-end.
(First candidate 1sik/Shikamaru discarded: 1sikeff1.xfbin is a 422-byte stub with zero
hero VFX models/textures - shadow jutsu are engine-driven; see attempt_1sik_partial/.)

Replicates the production pipeline tools from goofy-mendeleev/tools, but with
OUT_DIR redirected to the w22 workspace and ROSTER narrowed to the new hero.
NOTHING under <repo>/public is written.

Stages (run individually):
  A  model      -> w22_out/assets/models/1orc.json + textures
  B  normalize  -> 5.4m canonical bones (fix_and_normalize_models logic)
  C  faithful   -> databook rescale + FK bone positions + data/animations.json
  D  vfx        -> skills/skill_vfx.json + textures
"""
import json
import os
import struct
import sys
import time
import zipfile

REPO = r"C:\Users\jessi\Documents\antigravity\goofy-mendeleev"
W22 = r"C:\Users\jessi\Documents\antigravity\fearless-davinci\w22_out"
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "runtime"))

from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla  # noqa: E402
import tools.extract_moba_assets as em  # noqa: E402

CID = "1orc"
HERO_NAME = "Orochimaru"
ROSTER_ENTRY = (CID, HERO_NAME, "Legendary Sannin • Snake Master", "Assassin / Zone Control", "#84cc16")
OUT_DIR = os.path.join(W22, "assets")
DATABOOK_CM = 179.4  # Orochimaru, Part I (To no Sho: 179.4 cm)


def t0():
    return time.time()


def stage_A_model():
    t = t0()
    em.OUT_DIR = OUT_DIR
    from tools.extract_moba_assets import (
        CANONICAL_BONES, map_bone_to_canonical, parse_nucc_chunks,
        decode_ndp3_mesh, decode_ntp3_texture, write_png_rgba,
    )
    os.makedirs(os.path.join(OUT_DIR, "models"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "textures"), exist_ok=True)

    cname = HERO_NAME
    with zipfile.ZipFile(APK_PATH, "r") as z:
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            bod_name = f"{CID}bod1.xfbin"
            assert bod_name in toc_map, f"{bod_name} missing from data.awb"
            r = toc_map[bod_name]
            f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
            raw = f_dat.read(r["FileSize"])
            if raw[:8] == b"CRILAYLA":
                raw = decompress_crilayla(raw)
            chunks, maps, ci, types, names = parse_nucc_chunks(raw)
            print(f"[A] {bod_name}: {len(chunks)} chunks, {len(raw)} bytes decompressed", flush=True)

            # textures
            tex_files = {}
            for tname, ch_name, cmap_idx, payload, pbase in chunks:
                if tname == "nuccChunkTexture" and b"NTP3" in payload:
                    low_t = ch_name.lower()
                    if any(s in low_t for s in ("lod", "blur", "gmc", "wnc", "byakugan", "icpr")):
                        continue
                    ntp_pos = payload.find(b"NTP3")
                    _, num_tex = struct.unpack(">HH", payload[ntp_pos + 4:ntp_pos + 8])
                    tp = ntp_pos + 16
                    for sub_t in range(num_tex):
                        w, h, rgba, tot_sz = decode_ntp3_texture(payload, tp, max_dim=512)
                        key = f"{ch_name}_{sub_t}" if num_tex > 1 else ch_name
                        rel_path = f"textures/{CID}_{key}.png"
                        write_png_rgba(os.path.join(OUT_DIR, "textures", f"{CID}_{key}.png"), w, h, rgba)
                        tex_files[key] = rel_path
                        tp += tot_sz
            print(f"[A] textures: {list(tex_files.keys())}", flush=True)

            # main clump
            char_clump_pay = None
            char_pbase = None
            for tname, ch_name, cmap_idx, payload, pbase in chunks:
                if tname == "nuccChunkClump" and ch_name.lower().startswith(CID):
                    char_clump_pay, char_pbase = payload, pbase
                    break
            if char_clump_pay is None:
                for tname, ch_name, cmap_idx, payload, pbase in chunks:
                    if tname == "nuccChunkClump":
                        char_clump_pay, char_pbase = payload, pbase
                        break
            assert char_clump_pay is not None, "no clump found"

            coords_in_page = [c[1] for c in chunks if c[0] == "nuccChunkCoord" and c[4] == char_pbase]
            _, nbones, _ = struct.unpack(">IHH", char_clump_pay[:8])
            parents = struct.unpack(f">{nbones}h", char_clump_pay[8:8 + nbones * 2])
            bone_lut = [map_bone_to_canonical(i, coords_in_page, parents) for i in range(len(coords_in_page))]

            mat_info = {}
            for tname, ch_name, cmap_idx, payload, pbase in chunks:
                if tname == "nuccChunkMaterial" and pbase == char_pbase:
                    uv_off_u, uv_off_v, uv_scl_u, uv_scl_v = 0.0, 0.0, 1.0, 1.0
                    if len(payload) >= 28:
                        u0, v0, su, sv = struct.unpack(">4f", payload[12:28])
                        if 0.0 < su <= 2.0 and 0.0 < sv <= 2.0:
                            uv_off_u, uv_off_v, uv_scl_u, uv_scl_v = u0, v0, su, sv
                    mat_info[cmap_idx] = (ch_name.lower(), (uv_off_u, uv_off_v, uv_scl_u, uv_scl_v))

            body_tex = tex_files.get(f"{CID}body_0") or next((v for k, v in tex_files.items() if "body" in k.lower()), None)
            mant_tex = tex_files.get(f"{CID}mant_0")
            eye_l_tex = tex_files.get(f"{CID}eyeL") or tex_files.get(f"{CID}eye_0") or tex_files.get(f"{CID}eye") or next((v for k, v in tex_files.items() if "eye" in k.lower()), body_tex)
            eye_r_tex = tex_files.get(f"{CID}eyeR") or tex_files.get(f"{CID}eye_0") or tex_files.get(f"{CID}eye") or eye_l_tex

            selected_meshes = []
            for tname, ch_name, cmap_idx, payload, pbase in chunks:
                if tname != "nuccChunkModel" or pbase != char_pbase or b"NDP3" not in payload:
                    continue
                low = ch_name.lower()
                if not low.startswith(f"{CID}00t0"):
                    continue
                if any(s in low for s in ("blur", "shadow", "_lod1", "_lod2", "tongue", "teeth", "byakugan", "icp", "hatigane02", "weapon")):
                    continue
                subs = decode_ndp3_mesh(payload, ch_name, is_character=True, bone_lut=bone_lut)
                for sm in subs:
                    mcmap = sm["mat_cmap"]
                    mname, (u0, v0, su, sv) = mat_info.get(mcmap, ("", (0.0, 0.0, 1.0, 1.0)))
                    if "eye" in low or "eye" in mname:
                        sm["texture"] = eye_l_tex if ("_l" in low or " l" in low or "_l" in mname) else eye_r_tex
                        if su != 1.0 or sv != 1.0 or u0 != 0.0 or v0 != 0.0:
                            new_uvs = []
                            for i in range(0, len(sm["uvs"]), 2):
                                new_uvs.append(round(sm["uvs"][i] * su + u0, 4))
                                new_uvs.append(round(sm["uvs"][i + 1] * sv + v0, 4))
                            sm["uvs"] = new_uvs
                    else:
                        sm["texture"] = body_tex
                    selected_meshes.append(sm)

            sums = {i: [0.0, 0.0, 0.0, 0.0] for i in range(len(CANONICAL_BONES))}
            for sm in selected_meshes:
                pos_arr, si_arr, sw_arr = sm["positions"], sm["skinIndices"], sm["skinWeights"]
                nv = len(pos_arr) // 3
                for v in range(nv):
                    vx, vy, vz = pos_arr[v * 3], pos_arr[v * 3 + 1], pos_arr[v * 3 + 2]
                    for k in range(4):
                        bi = si_arr[v * 4 + k]
                        wi = sw_arr[v * 4 + k]
                        if wi > 0.1:
                            sums[bi][0] += vx * wi
                            sums[bi][1] += vy * wi
                            sums[bi][2] += vz * wi
                            sums[bi][3] += wi
            bones_out = []
            for bi, (bname, bparent, default_pos) in enumerate(CANONICAL_BONES):
                sx_v, sy_v, sz_v, sw_v = sums[bi]
                if bi in (0, 1, 2, 3, 4, 5):
                    jy = (sy_v / sw_v) if sw_v > 5.0 else default_pos[1]
                    if bi == 0:
                        jy = 0.0
                    if bi == 5:
                        jy = max(116.0, min(126.0, jy - 6.0))
                    jpos = [0.0, round(jy, 2), 0.0]
                elif sw_v > 5.0:
                    jpos = [round(sx_v / sw_v, 2), round(sy_v / sw_v, 2), round(sz_v / sw_v, 2)]
                else:
                    jpos = list(default_pos)
                bones_out.append({"name": bname, "parent": bparent, "pos": jpos})

            model_out_path = os.path.join(OUT_DIR, "models", f"{CID}.json")
            tot_v = sum(len(m["positions"]) // 3 for m in selected_meshes)
            tot_t = sum(len(m["indices"]) // 3 for m in selected_meshes)
            with open(model_out_path, "w", encoding="utf-8") as mf:
                json.dump({"id": CID, "name": cname, "bones": bones_out, "meshes": selected_meshes}, mf, separators=(",", ":"))
            print(f"[A] Saved {CID}.json: {len(selected_meshes)} meshes, {tot_v} verts, {tot_t} tris, 20 bones ({time.time()-t:.1f}s)")
            return {"meshes": len(selected_meshes), "verts": tot_v, "tris": tot_t,
                    "textures": list(tex_files.values()), "t_s": time.time() - t}


def stage_B_normalize():
    t = t0()
    import tools.fix_and_normalize_models as fnm  # noqa: E402
    fnm.MODELS_DIR = os.path.join(OUT_DIR, "models")
    fnm.process_all_models()
    print(f"[B] normalized ({time.time()-t:.1f}s)")
    return {"t_s": time.time() - t}


def stage_C_faithful():
    t = t0()
    import tools.extract_faithful_fk_animations as efk  # noqa: E402
    efk.OUT_DIR = OUT_DIR
    efk.ROSTER = [ROSTER_ENTRY]
    if CID not in efk.DATABOOK_HEIGHTS_CM:
        efk.DATABOOK_HEIGHTS_CM[CID] = DATABOOK_CM
    efk.extract_all_faithful_animations()
    print(f"[C] faithful FK animations done ({time.time()-t:.1f}s)")
    return {"t_s": time.time() - t}


def stage_D_vfx():
    t = t0()
    import tools.extract_all_storm_skills as ess  # noqa: E402
    ess.OUT_DIR = OUT_DIR
    ess.ROSTER = [ROSTER_ENTRY]
    ess.extract_vfx_and_models()
    print(f"[D] skill vfx done ({time.time()-t:.1f}s)")
    return {"t_s": time.time() - t}


if __name__ == "__main__":
    stage = sys.argv[1]
    out = {"A": stage_A_model, "B": stage_B_normalize, "C": stage_C_faithful, "D": stage_D_vfx}[stage]()
    with open(os.path.join(W22, f"checkpoint_{stage}.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(f"checkpoint saved: w22_out/checkpoint_{stage}.json")
