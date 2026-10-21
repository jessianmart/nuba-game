import os
import json
import math
import struct
import zipfile
import texture2ddecoder
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import (
    OUT_DIR,
    ROSTER,
    parse_nucc_chunks,
    decode_ndp3_mesh,
    downsample_rgba,
    write_png_rgba,
)


def decode_ntp3_etc2_clean(data: bytes, t_pos: int, max_dim: int = 512):
    tot_sz, unk, dat_sz, hdr_sz, unk2, mips, pfmt, w, h = struct.unpack(">IIIHHHHHH", data[t_pos:t_pos+24])
    pix = data[t_pos + hdr_sz : t_pos + hdr_sz + dat_sz]

    if pfmt == 0x17:  # ETC2 RGB8
        bgra = bytearray(texture2ddecoder.decode_etc2(pix, w, h))
        rgba = bytearray(len(bgra))
        rgba[0::4] = bgra[2::4]
        rgba[1::4] = bgra[1::4]
        rgba[2::4] = bgra[0::4]
        rgba[3::4] = bgra[3::4]
    elif pfmt == 0x15:  # ETC2 RGBA8
        bgra = bytearray(texture2ddecoder.decode_etc2a8(pix, w, h))
        rgba = bytearray(len(bgra))
        rgba[0::4] = bgra[2::4]
        rgba[1::4] = bgra[1::4]
        rgba[2::4] = bgra[0::4]
        rgba[3::4] = bgra[3::4]
    elif pfmt == 0x00:  # DXT1
        bgra = bytearray(texture2ddecoder.decode_bc1(pix, w, h))
        rgba = bytearray(len(bgra))
        rgba[0::4] = bgra[2::4]
        rgba[1::4] = bgra[1::4]
        rgba[2::4] = bgra[0::4]
        rgba[3::4] = bgra[3::4]
    elif pfmt == 0x02:  # DXT5
        bgra = bytearray(texture2ddecoder.decode_bc3(pix, w, h))
        rgba = bytearray(len(bgra))
        rgba[0::4] = bgra[2::4]
        rgba[1::4] = bgra[1::4]
        rgba[2::4] = bgra[0::4]
        rgba[3::4] = bgra[3::4]
    elif pfmt == 0x0E:  # ARGB8888
        rgba = bytearray(w * h * 4)
        for i in range(0, w * h * 4, 4):
            rgba[i] = pix[i + 1]
            rgba[i + 1] = pix[i + 2]
            rgba[i + 2] = pix[i + 3]
            rgba[i + 3] = pix[i]
    elif pfmt == 0x08:  # RGB565
        rgba = bytearray(w * h * 4)
        words = struct.unpack(f">{w*h}H", pix[:w*h*2])
        for i, v in enumerate(words):
            dst = i * 4
            rgba[dst] = ((v >> 11) & 31) * 255 // 31
            rgba[dst + 1] = ((v >> 5) & 63) * 255 // 63
            rgba[dst + 2] = (v & 31) * 255 // 31
            rgba[dst + 3] = 255
    else:
        rgba = bytearray(w * h * 4)

    out_w, out_h = w, h
    if max_dim and (w > max_dim or h > max_dim):
        scale = max_dim / max(w, h)
        out_w = max(4, int(round(w * scale)))
        out_h = max(4, int(round(h * scale)))
        rgba = downsample_rgba(bytes(rgba), w, h, out_w, out_h)
    return out_w, out_h, bytes(rgba), tot_sz


def bake_water_ripple_texture(floor_rgba: bytes, normal_rgba: bytes, w: int, h: int) -> bytes:
    # Blend sd00a_river01_floor (river stones) with Konoha cerulean water tint and sd00a_river01_normal_watar ripples
    out = bytearray(w * h * 4)
    for i in range(w * h):
        idx = i * 4
        fr, fg, fb = floor_rgba[idx], floor_rgba[idx + 1], floor_rgba[idx + 2]
        nr, ng = normal_rgba[idx], normal_rgba[idx + 1]
        # Highlight from normal map wave crest
        wave = max(0, (nr - 128) + (ng - 128))
        spec = min(75, int(wave * 0.65))
        # Blend 48% riverbed stone + 52% turquoise Konoha stream water (42, 148, 195) + wave highlight
        r = min(255, int(fr * 0.45 + 38 * 0.55 + spec))
        g = min(255, int(fg * 0.48 + 148 * 0.52 + spec))
        b = min(255, int(fb * 0.42 + 205 * 0.58 + int(spec * 1.1)))
        out[idx] = r
        out[idx + 1] = g
        out[idx + 2] = b
        out[idx + 3] = 255
    return bytes(out)


def fix_stage_and_all_textures():
    os.makedirs(os.path.join(OUT_DIR, "stage"), exist_ok=True)
    os.makedirs(os.path.join(OUT_DIR, "textures"), exist_ok=True)

    with zipfile.ZipFile(APK_PATH, "r") as z:
        stage_textures = {}
        stage_meshes = []
        with z.open("assets/data/sim/stage1.awb") as f_stg:
            cpk = parse_utf(f_stg.read(65536), 16)[0]
            f_stg.seek(cpk["TocOffset"])
            toc = parse_utf(f_stg.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}
            r = toc_map["sd00a.xfbin"]
            f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
            sraw = decompress_crilayla(f_stg.read(r["FileSize"]))
            schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)

            river_floor_rgba = None
            river_norm_rgba = None
            for tname, ch_name, cmap_idx, payload, pbase in schunks:
                if tname == "nuccChunkTexture" and b"NTP3" in payload:
                    low_c = ch_name.lower()
                    ntp_pos = payload.find(b"NTP3")
                    if low_c == "sd00a_river01_normal_watar":
                        _, _, river_norm_rgba, _ = decode_ntp3_etc2_clean(payload, ntp_pos + 16, max_dim=512)
                        continue
                    if "shadow" in low_c or "normal" in low_c or "height" in low_c or "sky_cube" in low_c:
                        continue
                    max_d = 512 if ("flo" in low_c or "bac" in low_c or "river" in low_c or "obj001" in low_c or "obj002" in low_c) else 256
                    w, h, rgba, _ = decode_ntp3_etc2_clean(payload, ntp_pos + 16, max_dim=max_d)
                    if low_c == "sd00a_river01_floor":
                        river_floor_rgba = rgba
                    write_png_rgba(os.path.join(OUT_DIR, "stage", f"{ch_name}.png"), w, h, rgba)
                    stage_textures[ch_name] = f"stage/{ch_name}.png"

            if river_floor_rgba and river_norm_rgba:
                baked_water = bake_water_ripple_texture(river_floor_rgba, river_norm_rgba, 512, 512)
                write_png_rgba(os.path.join(OUT_DIR, "stage", "sd00a_river01_floor.png"), 512, 512, baked_water)
                print("Baked turquoise Konoha water + ripples + riverbed stones into sd00a_river01_floor.png!")

            # Resolve nuccChunkMaterial -> diffuse nuccChunkTexture
            mat_to_tex = {}
            for tname, ch_name, cmap_idx, payload, pbase in schunks:
                if tname == "nuccChunkMaterial":
                    u32s = struct.unpack(f">{len(payload)//4}I", payload[:(len(payload)//4)*4])
                    resolved_tex = None
                    for u in u32s:
                        if 0 < u < 250 and (pbase + u) < len(sci):
                            gi = sci[pbase + u]
                            if gi < len(smaps):
                                ti, pi, ni = smaps[gi]
                                if stypes[ti] == "nuccChunkTexture":
                                    cand = snames[ni]
                                    if cand in stage_textures:
                                        resolved_tex = stage_textures[cand]
                                        break
                    if not resolved_tex:
                        for tk, tv in stage_textures.items():
                            if tk in ch_name:
                                resolved_tex = tv
                                break
                    mat_to_tex[(pbase, cmap_idx)] = resolved_tex

            coord_map = {}
            for tname, ch_name, cmap_idx, payload, pbase in schunks:
                if tname == "nuccChunkCoord" and len(payload) >= 36:
                    coord_map[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

            # Extract complete tree prototype from CLUMP ki02 (trunk ki02_miki + branch/leaf canopy eda00..eda28)
            ki02_parts = []
            for tname, ch_name, cmap_idx, payload, pbase in schunks:
                if tname == "nuccChunkModel" and b"NDP3" in payload:
                    low = ch_name.lower()
                    if low == "ki02_miki" or (low.startswith("eda") and "_lod" not in low):
                        local_trf = coord_map.get((pbase, ch_name))
                        subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=local_trf)
                        for sm in subs:
                            if low.startswith("eda"):
                                sm["texture"] = stage_textures.get("ha000") or stage_textures.get("ha001")
                            else:
                                sm["texture"] = mat_to_tex.get((pbase, sm["mat_cmap"])) or stage_textures.get("sd00aobj008")
                            ki02_parts.append(sm)

            tree_placements = []
            for (pbase, kname), trf in coord_map.items():
                if kname.startswith("dummy_ki"):
                    tree_placements.append((kname, trf))

            # Compress the overly wide empty river gap (z_raw in [-3650..-900]) into a scenic 750cm Konoha stream
            # so the grassy Konoha Training Field & northern cliff wall frame the MOBA arena without a huge dead zone!
            def warp_stage_z(z_raw: float) -> float:
                if z_raw < -3650.0:
                    # Northern cliff wall & trees on the far shore: bring closer by +2000 cm
                    return round(z_raw + 700.0, 2)
                elif z_raw < -900.0:
                    # Compress river channel [-3650..-900] (2750cm) -> [-2950..-2200] (750cm scenic stream)
                    t = (z_raw - (-3650.0)) / 2750.0
                    return round(-2950.0 + t * 750.0, 2)
                else:
                    # Main grassy training ground [-900..+2900] -> shift by -1300cm so [-2200..+1600] is centered around Z=0!
                    return round(z_raw - 1300.0, 2)

            for tname, ch_name, cmap_idx, payload, pbase in schunks:
                if tname != "nuccChunkModel" or b"NDP3" not in payload:
                    continue
                low = ch_name.lower()
                if any(skip in low for skip in (
                    "hashadow", "mikishadow", "kage", "_lod1", "trans", "bug", "hit", "mdl0", "sun", "cam_",
                    "ki02_miki", "ki03_miki", "ki05_miki", "ki06_miki", "ki07_miki", "ki08_miki", "eda"
                )):
                    continue

                trf = coord_map.get((pbase, ch_name))
                subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=trf)
                for sm in subs:
                    tex = mat_to_tex.get((pbase, sm["mat_cmap"]))
                    if "river" in low:
                        tex = stage_textures.get("sd00a_river01_floor")
                    elif not tex:
                        if "dome" in low:
                            tex = stage_textures.get("sd00abac002")
                        elif "flo001" in low:
                            tex = stage_textures.get("sd00aflo001")
                        elif "flo002" in low or "iwa" in low:
                            tex = stage_textures.get("sd00aflo002")
                        elif "flo003" in low:
                            tex = stage_textures.get("sd00aflo003")
                        elif "flo004" in low:
                            tex = stage_textures.get("sd00aflo004")
                        else:
                            tex = stage_textures.get("sd00aflo001")
                    sm["texture"] = tex

                    pos = sm["positions"]
                    is_sky = "dome" in low or "bac" in low
                    for idx in range(0, len(pos), 3):
                        if not is_sky:
                            pos[idx + 2] = warp_stage_z(pos[idx + 2])
                    if "river" in low:
                        sm["uvs"] = [
                            round(pos[i*3] * 0.0022, 4) if k == 0 else round(pos[i*3+2] * 0.0022, 4)
                            for i in range(len(pos)//3) for k in range(2)
                        ]
                    stage_meshes.append(sm)

            # Instantiate full 3D trees (trunk + leaf canopy) at each dummy_ki world placement
            for dname, trf in tree_placements:
                px, py, pz, rx, ry, rz, sx_m, sy_m, sz_m = trf
                wx, wy, wz = px, pz, warp_stage_z(-py)
                rad_y = math.radians(rz) if abs(rz) > 0.01 and abs(rz - 1.0) > 0.01 else 0.0
                cos_y, sin_y = math.cos(rad_y), math.sin(rad_y)
                for part in ki02_parts:
                    p_pos = part["positions"]
                    new_pos = []
                    for v in range(0, len(p_pos), 3):
                        lx, ly, lz = p_pos[v] * sx_m, p_pos[v+1] * sz_m, p_pos[v+2] * sy_m
                        rx_v = lx * cos_y - lz * sin_y + wx
                        ry_v = ly + wy
                        rz_v = lx * sin_y + lz * cos_y + wz
                        new_pos.extend((round(rx_v, 2), round(ry_v, 2), round(rz_v, 2)))
                    stage_meshes.append({
                        "name": f"{dname}_{part['name']}",
                        "mat_cmap": part["mat_cmap"],
                        "texture": part["texture"],
                        "positions": new_pos,
                        "normals": list(part["normals"]),
                        "uvs": list(part["uvs"]),
                        "indices": list(part["indices"]),
                    })

            stage_out_path = os.path.join(OUT_DIR, "stage", "stage_3d.json")
            tot_sv = sum(len(m["positions"]) // 3 for m in stage_meshes)
            tot_st = sum(len(m["indices"]) // 3 for m in stage_meshes)
            with open(stage_out_path, "w", encoding="utf-8") as sf:
                json.dump({
                    "name": "Konoha Training Field (sd00a.xfbin)",
                    "apkSource": "assets/data/sim/stage1.awb -> sd00a.xfbin",
                    "verts": tot_sv,
                    "tris": tot_st,
                    "meshes": stage_meshes,
                }, sf, separators=(",", ":"))
            print(f"Saved fixed 3D Stage Map stage_3d.json ({len(stage_meshes)} submeshes, {tot_sv} verts, {tot_st} tris)")


if __name__ == "__main__":
    fix_stage_and_all_textures()
