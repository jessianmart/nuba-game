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

print(f"sd04a decompressed {len(sraw)} bytes")

# Extract textures list
textures = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkTexture" and b"NTP3" in payload:
        textures[ch_name] = len(payload)

print(f"Total NTP3 textures: {len(textures)}")
for k, v in sorted(textures.items()):
    print(f"  Tex: {k} ({v} bytes)")

# Materials mapping
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
                        if cand in textures:
                            resolved_tex = cand
                            break
        mat_to_tex[(pbase, cmap_idx)] = (ch_name, resolved_tex)

# Coords
coords = {}
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkCoord" and len(payload) >= 36:
        coords[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

print(f"\nTotal Coords: {len(coords)}")
dummy_coords = [k[1] for k in coords.keys() if "dummy" in k[1].lower()]
print(f"Dummy coords ({len(dummy_coords)}): {dummy_coords[:20]}")

# Models
models = []
for tname, ch_name, cmap_idx, payload, pbase in schunks:
    if tname == "nuccChunkModel" and b"NDP3" in payload:
        trf = coords.get((pbase, ch_name))
        try:
            subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=trf)
            for sm in subs:
                mat_info = mat_to_tex.get((pbase, sm["mat_cmap"]), ("none", "none"))
                pos = sm["positions"]
                xs = pos[0::3]
                ys = pos[1::3]
                zs = pos[2::3]
                models.append({
                    "name": sm["name"],
                    "mat_name": mat_info[0],
                    "tex": mat_info[1],
                    "vcount": len(xs),
                    "icount": len(sm["indices"]),
                    "x": (min(xs), max(xs)) if xs else (0,0),
                    "y": (min(ys), max(ys)) if ys else (0,0),
                    "z": (min(zs), max(zs)) if zs else (0,0),
                })
        except Exception as e:
            print(f"Failed to decode {ch_name}: {e}")

print(f"\nTotal Decoded Submeshes: {len(models)}")
for i, m in enumerate(models):
    print(f"[{i:2d}] {m['name']:30s} mat={m['mat_name']:25s} tex={str(m['tex']):25s} v={m['vcount']:5d} x=[{m['x'][0]:7.1f},{m['x'][1]:7.1f}] y=[{m['y'][0]:7.1f},{m['y'][1]:7.1f}] z=[{m['z'][0]:7.1f},{m['z'][1]:7.1f}]")
