"""Build a web-ready arena (mesh JSON + ETC2 textures) from any Storm stage file.

Usage:
    python tools/build_arena.py sd00a
    python tools/build_arena.py sd03b --name AREA_COLOSSEUM --label "Colosseu"
    python tools/build_arena.py sd03b --catalog-only

Reads the raw .xfbin produced by tools/extract_fase3.py, so no APK access is needed
after the first extraction pass.
"""

import argparse
import json
import math
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.extract_moba_assets import decode_ndp3_mesh, parse_nucc_chunks, write_png_rgba  # noqa: E402
from tools.fix_stage_and_textures import decode_ntp3_etc2_clean  # noqa: E402

STAGE_RAW = os.path.join(ROOT, "public/assets/stage/raw")
STAGE_OUT = os.path.join(ROOT, "public/assets/stage")
ARENA_OUT = os.path.join(ROOT, "public/assets/stage/arena")
ARENAS_JSON = os.path.join(ROOT, "public/assets/data/arenas.json")

# NUCC stage coordinates are centimetres; Three.js wants metres.
STAGE_SCALE = 0.022

# Submeshes that never contribute to the playable arena: collision proxies,
# shadow blobs, camera/dummy rigs, transition triggers and LOD duplicates.
DROP_SUBMESH = (
    "hit", "wallroot", "dummylodcoord", "bug", "dummy", "dummylod", "lodcoord", "lod1", "lod2",
    "hashadow", "mikishadow", "cam_", "transanm", "shadow", "sun", "sd03b02", "sd03b04",
    "sd03balfa07", "trans_obj08_sub1"
)

# Textures that are lighting data rather than colour maps.
DROP_TEXTURE = ("shadow", "normal", "height", "_spec", "specular")


def load_stage(stage_id):
    path = os.path.join(STAGE_RAW, f"data_stage_{stage_id}.xfbin")
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    from tools.cpk_extract import read_by_name
    return read_by_name(f"{stage_id}.xfbin")


def should_drop_mesh(name):
    low = name.lower()
    return any(k in low for k in DROP_SUBMESH)


def should_drop_texture(name):
    low = name.lower()
    return any(k in low for k in DROP_TEXTURE)


def collect_materials(chunks, smaps, sci, stypes, snames, tex_chunks, stage_id=""):
    """Resolve each material chunk to the colour texture it actually samples."""
    mat_to_tex = {}
    for tname, ch_name, cmap_idx, payload, pbase in chunks:
        if tname != "nuccChunkMaterial":
            continue
        n = len(payload) // 4
        if not n:
            continue
        u32s = struct.unpack(f">{n}I", payload[: n * 4])
        resolved = None
        cand_list = []
        for u in u32s:
            gi = pbase + u
            if 0 <= gi < len(sci):
                si = sci[gi]
                if si < len(smaps):
                    ti, pi, ni = smaps[si]
                    if ti < len(stypes) and stypes[ti] == "nuccChunkTexture":
                        cand = snames[ni]
                        if cand in tex_chunks:
                            cand_list.append(cand)
        # For sd01b, skip sd01bobj012 (ambient lightmap) during material diffuse resolution
        # so authentic diffuse textures (sd01bobj001 scrolls, sd01bobj002 wood walls, sd01bobj004 railings,
        # sd01bobj005 floor, sd01bobj006 ceiling, sd01bobj020 statue) are assigned.
        for cand in cand_list:
            if should_drop_texture(cand):
                continue
            if stage_id == "sd01b" and cand == "sd01bobj012":
                continue
            resolved = tex_chunks[cand]
            break
        if resolved is None:
            for cand in cand_list:
                if not should_drop_texture(cand):
                    resolved = tex_chunks[cand]
                    break
        if resolved is None and cand_list:
            resolved = tex_chunks[cand_list[0]]
        mat_to_tex[(pbase, cmap_idx)] = resolved
    return mat_to_tex


def sanitize(sm):
    """Clean corrupt or non-finite floats and out-of-bounds indices."""
    pos, nrm, uv = sm["positions"], sm["normals"], sm["uvs"]
    for i in range(len(pos)):
        if not (math.isfinite(pos[i]) and abs(pos[i]) < 1e6):
            pos[i] = 0.0
    for i in range(len(nrm)):
        if not math.isfinite(nrm[i]):
            nrm[i] = 1.0 if (i % 3 == 1) else 0.0
    for i in range(len(uv)):
        if not math.isfinite(uv[i]):
            uv[i] = 0.0
    sm["positions"], sm["normals"], sm["uvs"] = pos, nrm, uv

    num_verts = len(pos) // 3
    idxs = sm.get("indices", [])
    valid_idxs = []
    for i in range(0, len(idxs) - 2, 3):
        i1, i2, i3 = idxs[i], idxs[i + 1], idxs[i + 2]
        if 0 <= i1 < num_verts and 0 <= i2 < num_verts and 0 <= i3 < num_verts:
            valid_idxs.extend([i1, i2, i3])
    sm["indices"] = valid_idxs
    return sm


def playable_radius(meshes, pct=0.90, lo=40.0, hi=140.0):
    """Radius that contains `pct` of floor vertices around the origin.

    Stage files mix the playable floor with distant scenery, so a plain bbox is
    useless; density around the origin is what actually bounds the fight.
    """
    radii = []
    for m in meshes:
        if "flo" not in m["name"].lower():
            continue
        p = m["positions"]
        for i in range(0, len(p), 3):
            x, z = p[i] * STAGE_SCALE, p[i + 2] * STAGE_SCALE
            radii.append(math.hypot(x, z))
    if not radii:
        radii = []
        for m in meshes:
            p = m["positions"]
            for i in range(0, len(p), 3):
                radii.append(math.hypot(p[i] * STAGE_SCALE, p[i + 2] * STAGE_SCALE))
    if not radii:
        return lo
    radii.sort()
    r = radii[min(len(radii) - 1, int(len(radii) * pct))]
    return round(max(lo, min(hi, r)), 2)


def build(stage_id, name=None, label=None, textures=True, max_dim=1024,
          catalog_only=False, radius=None):
    raw = load_stage(stage_id)
    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)

    tex_chunks = {}
    for tname, ch_name, cmap_idx, payload, pbase in chunks:
        if tname == "nuccChunkTexture" and b"NTP3" in payload:
            if not should_drop_texture(ch_name):
                tex_chunks[ch_name] = f"arena/{stage_id}/{ch_name}.png"

    coord_map = {}
    for tname, ch_name, cmap_idx, payload, pbase in chunks:
        if tname == "nuccChunkCoord" and len(payload) >= 36:
            coord_map[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

    if textures:
        outdir = os.path.join(ARENA_OUT, stage_id)
        os.makedirs(outdir, exist_ok=True)
        saved = 0
        for tname, ch_name, cmap_idx, payload, pbase in chunks:
            if tname != "nuccChunkTexture" or b"NTP3" not in payload:
                continue
            if should_drop_texture(ch_name):
                continue
            pos = payload.find(b"NTP3")
            low = ch_name.lower()
            is_1024 = any(k in low for k in (
                "flo", "bac", "bac2", "wall", "obj010",
                "sd01bobj001", "sd01bobj002", "sd01bobj003", "sd01bobj004", "sd01bobj005", "sd01bobj006", "sd01bobj020",
                "sd01bobj013", "sd01bobj015"
            ))
            dim = 1024 if is_1024 else 512
            try:
                w, h, rgba, _ = decode_ntp3_etc2_clean(payload, pos + 16, max_dim=dim)
            except Exception:
                continue
            if w and h:
                write_png_rgba(os.path.join(outdir, f"{ch_name}.png"), w, h, rgba)
                saved += 1
        print(f"  textures: {saved} PNG -> public/assets/stage/arena/{stage_id}/")

    mat_to_tex = collect_materials(chunks, smaps, sci, stypes, snames, tex_chunks, stage_id=stage_id)

    meshes = []
    minx = miny = minz = float("inf")
    maxx = maxy = maxz = float("-inf")
    for tname, ch_name, cmap_idx, payload, pbase in chunks:
        if tname != "nuccChunkModel" or b"NDP3" not in payload:
            continue
        if should_drop_mesh(ch_name):
            continue
        trf = coord_map.get((pbase, ch_name))
        try:
            subs = decode_ndp3_mesh(payload, ch_name, is_character=False,
                                    coord_transform=trf)
        except Exception:
            continue
        for sm in subs:
            sm = sanitize(sm)
            if len(sm["positions"]) // 3 <= 3:
                continue
            if should_drop_mesh(sm["name"]):
                continue
            # Drop any submesh with out-of-world vertex coordinates (> 50,000 cm / 1,100 m)
            if any(abs(c) > 50000 for c in sm["positions"]):
                continue
            tex = mat_to_tex.get((pbase, sm["mat_cmap"]))
            if not tex:
                low = ch_name.lower()
                for cand_k, cand_v in tex_chunks.items():
                    if stage_id == "sd01b" and cand_k == "sd01bobj012":
                        continue
                    cl = cand_k.lower()
                    if cl in low or low in cl:
                        tex = cand_v
                        break
            sm["texture"] = tex
            pos = sm["positions"]
            for i in range(0, len(pos), 3):
                x, y, z = pos[i], pos[i + 1], pos[i + 2]
                minx, maxx = min(minx, x), max(maxx, x)
                miny, maxy = min(miny, y), max(maxy, y)
                minz, maxz = min(minz, z), max(maxz, z)
            meshes.append(sm)

    verts = sum(len(m["positions"]) // 3 for m in meshes)
    tris = sum(len(m["indices"]) // 3 for m in meshes)

    # Playable footprint in Three.js units (metres).
    def s(v):
        return round(v * STAGE_SCALE, 3)

    bounds = {
        "min": [s(minx), s(miny), s(minz)],
        "max": [s(maxx), s(maxy), s(maxz)],
    }
    half = max(abs(bounds["min"][0]), abs(bounds["max"][0]),
               abs(bounds["min"][2]), abs(bounds["max"][2]))
    bounds["halfExtent"] = round(max(abs(bounds["min"][0]), abs(bounds["max"][0]),
                                     abs(bounds["min"][2]), abs(bounds["max"][2])), 2)
    hint = playable_radius(meshes)
    # Geometry alone cannot separate the fight footprint from distant scenery,
    # so an explicit radius always wins; the computed value is only a hint.
    radius = radius if radius is not None else hint

    data = {
        "id": stage_id,
        "name": name or stage_id,
        "label": label or stage_id,
        "apkSource": f"assets/data/sim/stage1.awb -> {stage_id}.xfbin",
        "scale": STAGE_SCALE,
        "verts": verts,
        "tris": tris,
        "bounds": bounds,
        "radius": radius,
        "meshes": meshes,
    }
    if catalog_only:
        return data

    os.makedirs(ARENA_OUT, exist_ok=True)
    out = os.path.join(ARENA_OUT, f"{stage_id}.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, separators=(",", ":"), allow_nan=False)
    size = os.path.getsize(out) / 1024 / 1024
    print(f"  meshes {len(meshes)}  verts {verts}  tris {tris}")
    print(f"  bounds x[{bounds['min'][0]},{bounds['max'][0]}] "
          f"y[{bounds['min'][1]},{bounds['max'][1]}] "
          f"z[{bounds['min'][2]},{bounds['max'][2]}]")
    print(f"  playable radius: {radius} m (geometry hint {hint} m)")
    print(f"  -> {os.path.relpath(out, ROOT)} ({size:.2f} MB)")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("stage_id")
    ap.add_argument("--name")
    ap.add_argument("--label")
    ap.add_argument("--no-textures", action="store_true")
    ap.add_argument("--catalog-only", action="store_true")
    ap.add_argument("--radius", type=float,
                    help="playable half-extent in metres (overrides geometry hint)")
    args = ap.parse_args()
    print(f"=== arena {args.stage_id} ===")
    build(args.stage_id, args.name, args.label, textures=not args.no_textures,
          catalog_only=args.catalog_only, radius=args.radius)


if __name__ == "__main__":
    main()