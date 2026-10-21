import os
import json
import math
import struct
import zipfile
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks, decode_ndp3_mesh

OUT_DIR = "public/assets/stage"
os.makedirs(OUT_DIR, exist_ok=True)

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f_stg:
    cpk = ai.parse_utf(f_stg.read(65536), 16)[0]
    f_stg.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f_stg.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}
    r = toc_map["sd01b.xfbin"]
    f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
    sraw = ai.decompress_crilayla(f_stg.read(r["FileSize"]))
    schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)

# Map textures
tex_chunks = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkTexture" and b"NTP3" in payload:
        tex_chunks[ch_name] = f"stage/{ch_name}.png"

mat_to_tex = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkMaterial":
        u32s = struct.unpack(f">{len(payload)//4}I", payload[:(len(payload)//4)*4])
        resolved_tex = None
        cand_list = []
        for u in u32s:
            if (pbase + u) < len(sci):
                gi = sci[pbase + u]
                if gi < len(smaps):
                    ti, pi, ni = smaps[gi]
                    if stypes[ti] == "nuccChunkTexture":
                        cand = snames[ni]
                        if cand in tex_chunks:
                            cand_list.append(cand)
        # In sd01b, sd01bobj012 is the ambient lightmap texture.
        # Prefer the authentic diffuse texture (e.g. sd01bobj001, sd01bobj002, etc.)
        for cand in cand_list:
            if "shadow" not in cand.lower() and cand != "sd01bobj012":
                resolved_tex = tex_chunks[cand]
                break
        if not resolved_tex:
            for cand in cand_list:
                if "shadow" not in cand.lower():
                    resolved_tex = tex_chunks[cand]
                    break
        if not resolved_tex and cand_list:
            resolved_tex = tex_chunks[cand_list[0]]
        mat_to_tex[(pbase, cmap_idx)] = resolved_tex

coord_map = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkCoord" and len(payload) >= 36:
        coord_map[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

SKIP_KEYWORDS = ("hit", "bug", "dmy", "wallroot")

stage_meshes = []
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname != "nuccChunkModel" or b"NDP3" not in payload:
        continue
    low = ch_name.lower()
    if any(k in low for k in SKIP_KEYWORDS):
        continue

    trf = coord_map.get((pbase, ch_name))
    subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=trf)
    for sm in subs:
        tex = mat_to_tex.get((pbase, sm["mat_cmap"]))
        if not tex:
            for cand_k, cand_v in tex_chunks.items():
                if cand_k.lower() in low or low in cand_k.lower():
                    tex = cand_v
                    break
            if not tex:
                tex = "stage/sd01bobj001.png"
        sm["texture"] = tex
        stage_meshes.append(sm)

tot_v = sum(len(m["positions"]) // 3 for m in stage_meshes)
tot_t = sum(len(m["indices"]) // 3 for m in stage_meshes)

stage_json_data = {
    "name": "Chunin Exam Tower Arena (sd01b.xfbin)",
    "apkSource": "assets/data/sim/stage1.awb -> sd01b.xfbin (STAGE_TOWER)",
    "arena": "Chunin Exam Arena - Tower of the Confrontation",
    "scale": 0.022,
    "verts": tot_v,
    "tris": tot_t,
    "meshes": stage_meshes
}

out_file = os.path.join(OUT_DIR, "stage_3d.json")
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(stage_json_data, f, separators=(",", ":"))

file_size_mb = os.path.getsize(out_file) / (1024 * 1024)
print(f"Generated {out_file}: {len(stage_meshes)} submeshes, {tot_v} verts, {tot_t} tris, {file_size_mb:.2f} MB")
