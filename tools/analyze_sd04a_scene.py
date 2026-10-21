import zipfile
import struct
import math
import tools.apk_inspect as ai
from tools.extract_moba_assets import parse_nucc_chunks, decode_ndp3_mesh

z = zipfile.ZipFile(ai.APK_PATH)
with z.open("assets/data/sim/stage1.awb") as f_stg:
    cpk = ai.parse_utf(f_stg.read(65536), 16)[0]
    f_stg.seek(cpk["TocOffset"])
    toc = ai.parse_utf(f_stg.read(cpk["TocSize"]), 16)
    toc_map = {r["FileName"].lower(): r for r in toc}
    r = toc_map["sd04a.xfbin"]
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
        for u in u32s:
            if (pbase + u) < len(sci):
                gi = sci[pbase + u]
                if gi < len(smaps):
                    ti, pi, ni = smaps[gi]
                    if stypes[ti] == "nuccChunkTexture":
                        cand = snames[ni]
                        if cand in tex_chunks:
                            # skip shadow/normal if possible
                            if "shadow" not in cand.lower() and "normal" not in cand.lower():
                                resolved_tex = tex_chunks[cand]
                                break
                            elif not resolved_tex:
                                resolved_tex = tex_chunks[cand]
        mat_to_tex[(pbase, cmap_idx)] = resolved_tex

coord_map = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkCoord" and len(payload) >= 36:
        coord_map[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

models = []
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkModel" and b"NDP3" in payload:
        trf = coord_map.get((pbase, ch_name))
        subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=trf)
        for sm in subs:
            tex = mat_to_tex.get((pbase, sm["mat_cmap"]))
            pos = sm["positions"]
            xs, ys, zs = pos[0::3], pos[1::3], pos[2::3]
            models.append({
                "model_name": ch_name,
                "sub_name": sm["name"],
                "tex": tex,
                "nv": len(xs),
                "nt": len(sm["indices"]) // 3,
                "x_min": min(xs) if xs else 0, "x_max": max(xs) if xs else 0,
                "y_min": min(ys) if ys else 0, "y_max": max(ys) if ys else 0,
                "z_min": min(zs) if zs else 0, "z_max": max(zs) if zs else 0,
            })

models.sort(key=lambda m: m["nv"], reverse=True)
print(f"Total Submeshes: {len(models)}")
print(f"Total Vertices: {sum(m['nv'] for m in models)}")
print(f"Total Triangles: {sum(m['nt'] for m in models)}")
print("\n=== ARENA ZONE MESHES (|x| < 6000 and |z| < 6000) ===")
arena_zone = [m for m in models if abs(m["x_min"]) < 6000 and abs(m["x_max"]) < 6000 and abs(m["z_min"]) < 6000 and abs(m["z_max"]) < 6000]
arena_zone.sort(key=lambda m: m["nv"], reverse=True)
for i, m in enumerate(arena_zone[:50]):
    print(f"[{i:2d}] {m['sub_name']:28s} tex={str(m['tex']):28s} v={m['nv']:5d} t={m['nt']:5d} "
          f"x=[{m['x_min']:7.1f},{m['x_max']:7.1f}] y=[{m['y_min']:7.1f},{m['y_max']:7.1f}] z=[{m['z_min']:7.1f},{m['z_max']:7.1f}]")


