import zipfile
import struct
import zlib
import json
import os
import re
import math
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "public", "assets")


def write_png_rgba(path: str, width: int, height: int, rgba_bytes: bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    raw_rows = bytearray()
    stride = width * 4
    for y in range(height):
        raw_rows.append(0)
        raw_rows.extend(rgba_bytes[y * stride : (y + 1) * stride])

    def make_chunk(ctype: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(ctype + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + ctype + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw_rows), level=6)
    png = b"\x89PNG\r\n\x1a\n" + make_chunk(b"IHDR", ihdr) + make_chunk(b"IDAT", idat) + make_chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def downsample_rgba(rgba: bytes, w: int, h: int, target_w: int, target_h: int) -> bytes:
    if w == target_w and h == target_h:
        return rgba
    out = bytearray(target_w * target_h * 4)
    x_ratio = w / target_w
    y_ratio = h / target_h
    for ty in range(target_h):
        sy = int(ty * y_ratio)
        for tx in range(target_w):
            sx = int(tx * x_ratio)
            src_i = (sy * w + sx) * 4
            dst_i = (ty * target_w + tx) * 4
            out[dst_i:dst_i+4] = rgba[src_i:src_i+4]
    return bytes(out)


ETC1_MODS = (
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183),
)


def clamp8(v: int) -> int:
    return 0 if v < 0 else (255 if v > 255 else v)


def decode_etc1_block(blk: bytes, out_rgba: bytearray, bx: int, by: int, width: int, height: int, alpha_block: bytes = None):
    b0, b1, b2, b3 = blk[0], blk[1], blk[2], blk[3]
    diff = (b3 >> 1) & 1
    flip = b3 & 1
    t1 = (b3 >> 5) & 7
    t2 = (b3 >> 2) & 7
    if diff:
        r1 = (b0 >> 3) & 31
        dr = b0 & 7
        if dr >= 4: dr -= 8
        g1 = (b1 >> 3) & 31
        dg = b1 & 7
        if dg >= 4: dg -= 8
        b_1 = (b2 >> 3) & 31
        db = b2 & 7
        if db >= 4: db -= 8
        r2 = clamp8(r1 + dr)
        g2 = clamp8(g1 + dg)
        b_2 = clamp8(b_1 + db)
        c1 = ((r1 << 3) | (r1 >> 2), (g1 << 3) | (g1 >> 2), (b_1 << 3) | (b_1 >> 2))
        c2 = ((r2 << 3) | (r2 >> 2), (g2 << 3) | (g2 >> 2), (b_2 << 3) | (b_2 >> 2))
    else:
        r1, r2 = (b0 >> 4) & 15, b0 & 15
        g1, g2 = (b1 >> 4) & 15, b1 & 15
        b_1, b_2 = (b2 >> 4) & 15, b2 & 15
        c1 = ((r1 << 4) | r1, (g1 << 4) | g1, (b_1 << 4) | b_1)
        c2 = ((r2 << 4) | r2, (g2 << 4) | g2, (b_2 << 4) | b_2)

    pix_indices, = struct.unpack(">I", blk[4:8])

    alphas = None
    if alpha_block is not None:
        base_a = alpha_block[0]
        mul_a = (alpha_block[1] >> 4) & 15
        tbl_a = alpha_block[1] & 15
        eac_mods = (
            (-3, -6, -9, -15, 2, 5, 8, 14),
            (-3, -7, -10, -13, 2, 6, 9, 12),
            (-2, -5, -8, -13, 1, 4, 7, 12),
            (-2, -4, -6, -13, 1, 3, 5, 12),
            (-3, -6, -8, -12, 2, 5, 7, 11),
            (-3, -7, -9, -11, 2, 6, 8, 10),
            (-4, -7, -8, -11, 3, 6, 7, 10),
            (-3, -5, -8, -11, 2, 4, 7, 10),
            (-2, -6, -8, -10, 1, 5, 7, 9),
            (-2, -5, -8, -10, 1, 4, 7, 9),
            (-2, -4, -8, -10, 1, 3, 7, 9),
            (-2, -5, -7, -10, 1, 4, 6, 9),
            (-3, -4, -7, -10, 2, 3, 6, 9),
            (-1, -2, -3, -10, 0, 1, 2, 9),
            (-4, -6, -8, -9, 3, 5, 7, 8),
            (-3, -5, -7, -9, 2, 4, 6, 8),
        )[tbl_a]
        abits = int.from_bytes(alpha_block[2:8], "big")
        alphas = [0] * 16
        for i in range(16):
            shift = 45 - i * 3
            a_idx = (abits >> shift) & 7
            alphas[i] = clamp8(base_a + eac_mods[a_idx] * (mul_a if mul_a > 0 else 1))

    for i in range(16):
        px = i // 4
        py = i % 4
        x = bx * 4 + px
        y = by * 4 + py
        if x >= width or y >= height:
            continue
        sub = (py >= 2) if flip else (px >= 2)
        base_c = c2 if sub else c1
        mod_t = ETC1_MODS[t2 if sub else t1]
        lsb = (pix_indices >> i) & 1
        msb = (pix_indices >> (i + 16)) & 1
        mod = mod_t[(msb << 1) | lsb]
        dst = (y * width + x) * 4
        out_rgba[dst] = clamp8(base_c[0] + mod)
        out_rgba[dst + 1] = clamp8(base_c[1] + mod)
        out_rgba[dst + 2] = clamp8(base_c[2] + mod)
        out_rgba[dst + 3] = alphas[i] if alphas is not None else 255


def decode_dxt_block(blk_color: bytes, out_rgba: bytearray, bx: int, by: int, width: int, height: int, blk_alpha: bytes = None):
    c0, c1, code = struct.unpack("<HHI", blk_color)
    def rgb565(v):
        return (((v >> 11) & 31) * 255 // 31, ((v >> 5) & 63) * 255 // 63, (v & 31) * 255 // 31)
    r0, g0, b0 = rgb565(c0)
    r1, g1, b1 = rgb565(c1)
    if c0 > c1 or blk_alpha is not None:
        pal = (
            (r0, g0, b0, 255),
            (r1, g1, b1, 255),
            ((2 * r0 + r1) // 3, (2 * g0 + g1) // 3, (2 * b0 + b1) // 3, 255),
            ((r0 + 2 * r1) // 3, (g0 + 2 * g1) // 3, (b0 + 2 * b1) // 3, 255),
        )
    else:
        pal = (
            (r0, g0, b0, 255),
            (r1, g1, b1, 255),
            ((r0 + r1) // 2, (g0 + g1) // 2, (b0 + b1) // 2, 255),
            (0, 0, 0, 0),
        )
    alphas = None
    if blk_alpha is not None:
        a0, a1 = blk_alpha[0], blk_alpha[1]
        abits = int.from_bytes(blk_alpha[2:8], "little")
        apal = [a0, a1]
        if a0 > a1:
            for j in range(1, 7): apal.append(((7 - j) * a0 + j * a1) // 7)
        else:
            for j in range(1, 5): apal.append(((5 - j) * a0 + j * a1) // 5)
            apal.extend([0, 255])
        alphas = [apal[(abits >> (3 * i)) & 7] for i in range(16)]

    for py in range(4):
        for px in range(4):
            x = bx * 4 + px
            y = by * 4 + py
            if x >= width or y >= height:
                continue
            idx = py * 4 + px
            c = pal[(code >> (2 * idx)) & 3]
            dst = (y * width + x) * 4
            out_rgba[dst] = c[0]
            out_rgba[dst + 1] = c[1]
            out_rgba[dst + 2] = c[2]
            out_rgba[dst + 3] = alphas[idx] if alphas is not None else c[3]


def decode_ntp3_texture(data: bytes, t_pos: int, max_dim: int = 256):
    tot_sz, unk, dat_sz, hdr_sz, unk2, mips, pfmt, w, h = struct.unpack(">IIIHHHHHH", data[t_pos:t_pos+24])
    pix = data[t_pos + hdr_sz : t_pos + hdr_sz + dat_sz]
    rgba = bytearray(w * h * 4)

    if pfmt == 0x0E:  # ARGB8888
        for i in range(0, w * h * 4, 4):
            rgba[i] = pix[i + 1]
            rgba[i + 1] = pix[i + 2]
            rgba[i + 2] = pix[i + 3]
            rgba[i + 3] = pix[i]
    elif pfmt == 0x08:  # Big-Endian RGB565
        words = struct.unpack(f">{w*h}H", pix[:w*h*2])
        for i, v in enumerate(words):
            dst = i * 4
            rgba[dst] = ((v >> 11) & 31) * 255 // 31
            rgba[dst + 1] = ((v >> 5) & 63) * 255 // 63
            rgba[dst + 2] = (v & 31) * 255 // 31
            rgba[dst + 3] = 255
    elif pfmt == 0x07:  # Big-Endian ARGB4444
        words = struct.unpack(f">{w*h}H", pix[:w*h*2])
        for i, v in enumerate(words):
            dst = i * 4
            a = ((v >> 12) & 15) * 17
            r = ((v >> 8) & 15) * 17
            g = ((v >> 4) & 15) * 17
            b = (v & 15) * 17
            rgba[dst], rgba[dst+1], rgba[dst+2], rgba[dst+3] = r, g, b, a
    elif pfmt == 0x17:  # ETC1
        bw, bh = (w + 3) // 4, (h + 3) // 4
        p = 0
        for by in range(bh):
            for bx in range(bw):
                decode_etc1_block(pix[p:p+8], rgba, bx, by, w, h)
                p += 8
    elif pfmt == 0x15:  # ETC2 RGBA8
        bw, bh = (w + 3) // 4, (h + 3) // 4
        p = 0
        for by in range(bh):
            for bx in range(bw):
                decode_etc1_block(pix[p+8:p+16], rgba, bx, by, w, h, alpha_block=pix[p:p+8])
                p += 16
    elif pfmt == 0x00:  # DXT1
        bw, bh = (w + 3) // 4, (h + 3) // 4
        p = 0
        for by in range(bh):
            for bx in range(bw):
                decode_dxt_block(pix[p:p+8], rgba, bx, by, w, h)
                p += 8
    elif pfmt == 0x02:  # DXT5
        bw, bh = (w + 3) // 4, (h + 3) // 4
        p = 0
        for by in range(bh):
            for bx in range(bw):
                decode_dxt_block(pix[p+8:p+16], rgba, bx, by, w, h, blk_alpha=pix[p:p+8])
                p += 16

    out_w, out_h = w, h
    if max_dim and (w > max_dim or h > max_dim):
        scale = max_dim / max(w, h)
        out_w = max(4, int(round(w * scale)))
        out_h = max(4, int(round(h * scale)))
        rgba = downsample_rgba(bytes(rgba), w, h, out_w, out_h)
    return out_w, out_h, bytes(rgba), tot_sz


def parse_nucc_chunks(data: bytes):
    ntypes, sz_types, npaths, sz_paths, nnames, sz_names, nmaps, sz_maps, nrefs, n_extra8 = struct.unpack(">10I", data[0x1C:0x44])

    def read_cstrs(buf, count):
        res, p = [], 0
        for _ in range(count):
            end = buf.index(b"\x00", p)
            res.append(buf[p:end].decode("utf-8", errors="replace"))
            p = end + 1
        return res

    pos = 0x44
    types = read_cstrs(data[pos:pos+sz_types], ntypes); pos += sz_types
    paths = read_cstrs(data[pos:pos+sz_paths], npaths); pos += sz_paths
    names = read_cstrs(data[pos:pos+sz_names], nnames); pos += sz_names
    pos = (pos + 3) & ~3
    maps = [struct.unpack(">3I", data[pos+i*12:pos+(i+1)*12]) for i in range(nmaps)]
    pos += sz_maps
    pos += n_extra8 * 8
    chunk_indices = struct.unpack(f">{nrefs}I", data[pos:pos+nrefs*4])
    pos += nrefs * 4

    chunk_pos = pos
    page_base = 0
    chunks = []
    while chunk_pos < len(data):
        csz, cmap_idx, cver, cunk = struct.unpack(">IIHH", data[chunk_pos:chunk_pos+12])
        payload = data[chunk_pos+12 : chunk_pos+12+csz]
        g_idx = chunk_indices[page_base + cmap_idx]
        t_idx, p_idx, n_idx = maps[g_idx]
        tname, cname = types[t_idx], names[n_idx]
        chunks.append((tname, cname, cmap_idx, payload, page_base))
        if tname == "nuccChunkPage" and csz >= 8:
            p_len, _ = struct.unpack(">II", payload[:8])
            page_base += p_len
        chunk_pos += 12 + csz
    return chunks, maps, chunk_indices, types, names


# 20 Canonical Humanoid Skeleton Bones for GPU SkinnedMesh
CANONICAL_BONES = [
    ("root",       -1, [0.0,   0.0,  0.0]),   # 0
    ("pelvis",      0, [0.0,  74.0,  0.0]),   # 1
    ("spine",       1, [0.0,  87.0,  0.0]),   # 2
    ("spine1",      2, [0.0, 108.0,  0.0]),   # 3
    ("neck",        3, [0.0, 118.0,  0.0]),   # 4
    ("head",        4, [0.0, 126.0,  0.0]),   # 5
    ("l_clavicle",  3, [8.0, 111.0, -1.0]),   # 6
    ("l_upperarm",  6, [16.5,108.0, -1.5]),   # 7
    ("l_forearm",   7, [29.0, 93.5, -2.0]),   # 8
    ("l_hand",      8, [43.0, 78.5, -2.0]),   # 9
    ("r_clavicle",  3, [-8.0,111.0, -1.0]),   # 10
    ("r_upperarm", 10, [-16.5,108.0,-1.5]),   # 11
    ("r_forearm",  11, [-29.0, 93.5,-2.0]),   # 12
    ("r_hand",     12, [-43.0, 78.5,-2.0]),   # 13
    ("l_thigh",     1, [10.0, 68.0,  0.0]),   # 14
    ("l_calf",     14, [15.0, 37.0, -1.0]),   # 15
    ("l_foot",     15, [20.0,  7.0,  0.0]),   # 16
    ("r_thigh",     1, [-10.0,68.0,  0.0]),   # 17
    ("r_calf",     17, [-15.0,37.0, -1.0]),   # 18
    ("r_foot",     18, [-20.0, 7.0,  0.0]),   # 19
]


def match_canonical_bone(raw_name: str):
    low = raw_name.lower()
    parts = low.split(" ", 1)
    b = parts[1].strip() if len(parts) > 1 else low
    if b == "pelvis": return 1
    if b == "spine": return 2
    if b in ("spine1", "spine2"): return 3
    if b == "neck": return 4
    if b in ("head", "head1", "face02", "face01"): return 5
    if b == "l clavicle": return 6
    if b == "l upperarm": return 7
    if b == "l forearm": return 8
    if b == "l hand": return 9
    if b == "r clavicle": return 10
    if b == "r upperarm": return 11
    if b == "r forearm": return 12
    if b == "r hand": return 13
    if b == "l thigh": return 14
    if b == "l calf": return 15
    if b == "l foot": return 16
    if b == "r thigh": return 17
    if b == "r calf": return 18
    if b == "r foot": return 19
    return None


def map_bone_to_canonical(b_idx: int, coords, parents) -> int:
    curr = b_idx
    visited = set()
    while 0 <= curr < len(coords) and curr not in visited:
        visited.add(curr)
        m = match_canonical_bone(coords[curr])
        if m is not None:
            return m
        if curr < len(parents):
            curr = parents[curr]
        else:
            break
    return 1


def decode_ndp3_mesh(payload: bytes, mesh_name: str, is_character: bool = True, bone_lut=None, coord_transform=None):
    ndp_off = payload.find(b"NDP3")
    if ndp_off == -1:
        return []
    p = payload[ndp_off:]
    sec1_sz, sec2_sz, sec3_sz, sec4_sz = struct.unpack(">IIII", p[16:32])
    num_sub, = struct.unpack(">H", p[0x5A:0x5C])

    ndp_total, = struct.unpack(">I", p[4:8])
    post = payload[ndp_off + ndp_total:]
    mat_cmaps = []
    if len(post) >= 2:
        mcnt, = struct.unpack(">H", post[:2])
        for m in range(min(mcnt, (len(post) - 2) // 4)):
            mat_cmaps.append(struct.unpack(">I", post[2 + m*4 : 6 + m*4])[0])

    idx_base = 0x30 + sec1_sz
    sec3_base = idx_base + sec2_sz
    sec4_base = sec3_base + sec3_sz

    sub_descs = []
    for s in range(num_sub):
        sb = 0x60 + s * 0x30
        idx_off, s3_off, s4_off, nv, flg = struct.unpack(">IIIHH", p[sb:sb+16])
        n_idx, = struct.unpack(">H", p[sb+0x20:sb+0x22])
        sub_descs.append((idx_off, s3_off, s4_off, nv, flg, n_idx))

    # Optional world transform for stage props (px, py, pz, rx, ry, rz, sx, sy, sz in NUCC Z-up space)
    tx_off, ty_off, tz_off = 0.0, 0.0, 0.0
    cos_z, sin_z = 1.0, 0.0
    sx_m, sy_m, sz_m = 1.0, 1.0, 1.0
    if coord_transform is not None:
        px, py, pz, rx, ry, rz, sx_m, sy_m, sz_m = coord_transform
        tx_off, ty_off, tz_off = px, py, pz
        rad_z = math.radians(rz) if abs(rz) > 0.01 and abs(rz - 1.0) > 0.01 else 0.0
        cos_z, sin_z = math.cos(rad_z), math.sin(rad_z)

    submeshes = []
    for s, (idx_off, s3_off, s4_off, nv, flg, n_idx) in enumerate(sub_descs):
        if nv == 0 or n_idx < 3:
            continue
        next_s3 = sub_descs[s + 1][1] if s + 1 < num_sub else sec3_sz
        next_s4 = sub_descs[s + 1][2] if s + 1 < num_sub else sec4_sz
        stride3 = (next_s3 - s3_off) // nv if nv else 0
        stride4 = (next_s4 - s4_off) // nv if nv and sec4_sz > 0 else 0

        ibuf = p[idx_base + idx_off : idx_base + idx_off + n_idx * 2]
        raw_indices = struct.unpack(f">{n_idx}H", ibuf)
        tris = []
        strip = []
        for idx_val in raw_indices:
            if idx_val == 0xFFFF or idx_val >= nv:
                strip.clear()
            else:
                strip.append(idx_val)
                if len(strip) >= 3:
                    i0, i1, i2 = strip[-3], strip[-2], strip[-1]
                    if i0 != i1 and i1 != i2 and i0 != i2:
                        if (len(strip) % 2) == 1:
                            tris.extend((i0, i1, i2))
                        else:
                            tris.extend((i0, i2, i1))
        if not tris:
            continue

        positions = []
        normals = []
        uvs = []
        skin_indices = []
        skin_weights = []

        if sec4_sz > 0 and stride4 >= 64 and stride3 >= 8:
            for v in range(nv):
                uv_b = p[sec3_base + s3_off + v * stride3 : sec3_base + s3_off + (v + 1) * stride3]
                v4_b = p[sec4_base + s4_off + v * stride4 : sec4_base + s4_off + (v + 1) * stride4]
                vx, vy, vz = struct.unpack(">3f", v4_b[:12])
                nx, ny, nz = struct.unpack(">3f", v4_b[16:28])
                u, v_coord = struct.unpack(">2e", uv_b[4:8])
                # Convert NUCC Z-up (vx, vy, vz) -> Three.js Y-up (vx, vz, -vy)
                positions.extend((round(vx, 2), round(vz, 2), round(-vy, 2)))
                normals.extend((round(nx, 2), round(nz, 2), round(-ny, 2)))
                uvs.extend((round(float(u), 4), round(float(v_coord), 4)))
                if is_character:
                    b0, b1, b2, b3 = struct.unpack(">4I", v4_b[32:48])
                    w0, w1, w2, w3 = struct.unpack(">4f", v4_b[48:64])
                    if bone_lut is not None:
                        cb0 = bone_lut[b0] if b0 < len(bone_lut) else 1
                        cb1 = bone_lut[b1] if b1 < len(bone_lut) else 1
                        cb2 = bone_lut[b2] if b2 < len(bone_lut) else 1
                        cb3 = bone_lut[b3] if b3 < len(bone_lut) else 1
                    else:
                        cb0, cb1, cb2, cb3 = 1, 1, 1, 1
                    wsum = w0 + w1 + w2 + w3
                    if wsum <= 0.0001:
                        w0, w1, w2, w3 = 1.0, 0.0, 0.0, 0.0
                    else:
                        w0, w1, w2, w3 = w0 / wsum, w1 / wsum, w2 / wsum, w3 / wsum
                    skin_indices.extend((cb0, cb1, cb2, cb3))
                    skin_weights.extend((round(w0, 4), round(w1, 4), round(w2, 4), round(w3, 4)))
        elif stride3 >= 28:
            uv_off = 24 if stride3 in (28, 32) else (stride3 - 8 if (flg & 0xF0) == 0x20 else stride3 - 4)
            for v in range(nv):
                vb = p[sec3_base + s3_off + v * stride3 : sec3_base + s3_off + (v + 1) * stride3]
                vx, vy, vz = struct.unpack(">3f", vb[:12])
                nx, ny, nz = struct.unpack(">3e", vb[12:18])
                u, v_coord = struct.unpack(">2e", vb[uv_off:uv_off+4])
                if coord_transform is not None:
                    svx, svy, svz = vx * sx_m, vy * sy_m, vz * sz_m
                    rvx = svx * cos_z - svy * sin_z + tx_off
                    rvy = svx * sin_z + svy * cos_z + ty_off
                    rvz = svz + tz_off
                    vx, vy, vz = rvx, rvy, rvz
                positions.extend((round(vx, 2), round(vz, 2), round(-vy, 2)))
                normals.extend((round(float(nx), 2), round(float(nz), 2), round(float(-ny), 2)))
                uvs.extend((round(float(u), 4), round(float(v_coord), 4)))
                if is_character:
                    # Non-skinned character submeshes (like eye_l, eye_r) belong 100% to Head bone (5)
                    skin_indices.extend((5, 0, 0, 0))
                    skin_weights.extend((1.0, 0.0, 0.0, 0.0))
        else:
            continue

        mat_cmap = mat_cmaps[s] if s < len(mat_cmaps) else (mat_cmaps[0] if mat_cmaps else -1)
        sm_dict = {
            "name": f"{mesh_name}_sub{s}",
            "mat_cmap": mat_cmap,
            "positions": positions,
            "normals": normals,
            "uvs": uvs,
            "indices": tris,
        }
        if is_character:
            sm_dict["skinIndices"] = skin_indices
            sm_dict["skinWeights"] = skin_weights
        submeshes.append(sm_dict)
    return submeshes


ROSTER = [
    ("1nrt", "Naruto Uzumaki", "Uzumaki Clan • Jinchuriki", "Fighter / Burst", "#ff7b00"),
    ("1ssk", "Sasuke Uchiha", "Uchiha Clan • Sharingan", "Assassin / Ranged", "#4a6cf7"),
    ("1skr", "Sakura Haruno", "Konoha Medical & Taijutsu", "Support / Brawler", "#ff5c8a"),
    ("1kks", "Kakashi Hatake", "Copy Ninja • Jonin Leader", "Mage / Assassin", "#60a5fa"),
    ("1roc", "Rock Lee", "Handsome Devil of the Leaf", "Hyper Melee / Speed", "#22c55e"),
    ("1itc", "Itachi Uchiha", "Akatsuki • Mangekyo", "Burst Mage / Control", "#ef4444"),
    ("1gar", "Gaara", "Kazekage Clan • Sand Defense", "Tank / Zone Control", "#d97706"),
    ("1hnt", "Hinata Hyuga", "Hyuga Clan • Byakugan", "Melee / Gentle Fist", "#a78bfa"),
    ("1nej", "Neji Hyuga", "Hyuga Genius • Kaiten", "Bruiser / Counter", "#818cf8"),
    ("1jry", "Jiraiya", "Toad Sage • Legendary Sannin", "Heavy Tank / AoE", "#f43f5e"),
]


def extract_all():
    os.makedirs(OUT_DIR, exist_ok=True)
    with zipfile.ZipFile(APK_PATH, "r") as z:
        # 1. Extract celshade texture from system
        cel_raw = z.read("assets/data/system/celshade.tex.xfbin")
        ntp_off = cel_raw.find(b"NTP3")
        if ntp_off != -1:
            cw, ch, crgba, _ = decode_ntp3_texture(cel_raw, ntp_off + 16, max_dim=128)
            write_png_rgba(os.path.join(OUT_DIR, "ui", "celshade.png"), cw, ch, crgba)

        # 2. Extract Character Select Portraits from dataRegion.awb
        with z.open("assets/data/disc/dataRegion.awb") as f_reg:
            cpk = parse_utf(f_reg.read(64 * 1024), 16)[0]
            f_reg.seek(cpk["TocOffset"])
            toc = parse_utf(f_reg.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            for cid, cname, _, _, _ in ROSTER:
                fname = f"msel1_{cid}.tex.xfbin"
                if fname in toc_map:
                    r = toc_map[fname]
                    f_reg.seek(cpk["TocOffset"] + r["FileOffset"])
                    raw = f_reg.read(r["FileSize"])
                    if raw[:8] == b"CRILAYLA":
                        raw = decompress_crilayla(raw)
                    p_off = raw.find(b"NTP3")
                    if p_off != -1:
                        pw, ph, prgba, _ = decode_ntp3_texture(raw, p_off + 16, max_dim=256)
                        write_png_rgba(os.path.join(OUT_DIR, "portraits", f"{cid}.png"), pw, ph, prgba)

        # 3. Extract 10 Playable 3D Characters with Full 20-Bone Rig & Skinning Weights
        roster_meta = []
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(64 * 1024), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}

            for cid, cname, ctitle, crole, ccolor in ROSTER:
                bod_name = f"{cid}bod1.xfbin"
                prm_name = f"{cid}prm.bin.xfbin"
                if bod_name not in toc_map:
                    continue

                r = toc_map[bod_name]
                f_dat.seek(cpk["TocOffset"] + r["FileOffset"])
                raw = f_dat.read(r["FileSize"])
                if raw[:8] == b"CRILAYLA":
                    raw = decompress_crilayla(raw)

                chunks, maps, ci, types, names = parse_nucc_chunks(raw)

                # Extract textures for this character
                tex_files = {}
                for tname, ch_name, cmap_idx, payload, pbase in chunks:
                    if tname == "nuccChunkTexture" and b"NTP3" in payload:
                        low_t = ch_name.lower()
                        if "lod" in low_t or "blur" in low_t or "gmc" in low_t or "wnc" in low_t or "byakugan" in low_t or "icpr" in low_t:
                            continue
                        ntp_pos = payload.find(b"NTP3")
                        _, num_tex = struct.unpack(">HH", payload[ntp_pos+4:ntp_pos+8])
                        tp = ntp_pos + 16
                        for sub_t in range(num_tex):
                            w, h, rgba, tot_sz = decode_ntp3_texture(payload, tp, max_dim=512)
                            key = f"{ch_name}_{sub_t}" if num_tex > 1 else ch_name
                            rel_path = f"textures/{cid}_{key}.png"
                            write_png_rgba(os.path.join(OUT_DIR, "textures", f"{cid}_{key}.png"), w, h, rgba)
                            tex_files[key] = rel_path
                            tp += tot_sz

                # Find the main character Clump and Coords matching cid (e.g. "1jrybod1", not "1gmc")
                char_clump_pay = None
                char_pbase = None
                for tname, ch_name, cmap_idx, payload, pbase in chunks:
                    if tname == "nuccChunkClump" and ch_name.lower().startswith(cid):
                        char_clump_pay = payload
                        char_pbase = pbase
                        break
                if char_clump_pay is None:
                    for tname, ch_name, cmap_idx, payload, pbase in chunks:
                        if tname == "nuccChunkClump":
                            char_clump_pay = payload
                            char_pbase = pbase
                            break

                coords_in_page = [c[1] for c in chunks if c[0] == "nuccChunkCoord" and c[4] == char_pbase]
                _, nbones, _ = struct.unpack(">IHH", char_clump_pay[:8])
                parents = struct.unpack(f">{nbones}h", char_clump_pay[8 : 8 + nbones * 2])
                bone_lut = [map_bone_to_canonical(i, coords_in_page, parents) for i in range(len(coords_in_page))]

                # Extract material UV transforms & names in char_pbase
                mat_info = {}
                for tname, ch_name, cmap_idx, payload, pbase in chunks:
                    if tname == "nuccChunkMaterial" and pbase == char_pbase:
                        uv_off_u, uv_off_v, uv_scl_u, uv_scl_v = 0.0, 0.0, 1.0, 1.0
                        if len(payload) >= 28:
                            u0, v0, su, sv = struct.unpack(">4f", payload[12:28])
                            if 0.0 < su <= 2.0 and 0.0 < sv <= 2.0:
                                uv_off_u, uv_off_v, uv_scl_u, uv_scl_v = u0, v0, su, sv
                        mat_info[cmap_idx] = (ch_name.lower(), (uv_off_u, uv_off_v, uv_scl_u, uv_scl_v))

                # Primary textures for character
                body_tex = tex_files.get(f"{cid}body_0") or next((v for k, v in tex_files.items() if "body_0" in k.lower() or "body" in k.lower()), None)
                mant_tex = tex_files.get(f"{cid}mant_0")
                eye_l_tex = tex_files.get(f"{cid}eyeL") or tex_files.get(f"{cid}eye_0") or tex_files.get(f"{cid}eye") or next((v for k, v in tex_files.items() if "eye" in k.lower()), body_tex)
                eye_r_tex = tex_files.get(f"{cid}eyeR") or tex_files.get(f"{cid}eye_0") or tex_files.get(f"{cid}eye") or eye_l_tex

                selected_meshes = []
                for tname, ch_name, cmap_idx, payload, pbase in chunks:
                    if tname != "nuccChunkModel" or pbase != char_pbase or b"NDP3" not in payload:
                        continue
                    low = ch_name.lower()
                    # Only include main character 00t0 visible meshes
                    if not low.startswith(f"{cid}00t0"):
                        continue
                    if any(skip in low for skip in ("blur", "shadow", "_lod1", "_lod2", "tongue", "teeth", "byakugan", "icp", "hatigane02", "weapon")):
                        continue

                    subs = decode_ndp3_mesh(payload, ch_name, is_character=True, bone_lut=bone_lut)
                    for sm in subs:
                        mcmap = sm["mat_cmap"]
                        mname, (u0, v0, su, sv) = mat_info.get(mcmap, ("", (0.0, 0.0, 1.0, 1.0)))
                        if "eye" in low or "eye" in mname:
                            sm["texture"] = eye_l_tex if ("_l" in low or " l" in low or "_l" in mname) else eye_r_tex
                            # Apply eye UV transform if non-identity
                            if su != 1.0 or sv != 1.0 or u0 != 0.0 or v0 != 0.0:
                                new_uvs = []
                                for i in range(0, len(sm["uvs"]), 2):
                                    new_uvs.append(round(sm["uvs"][i] * su + u0, 4))
                                    new_uvs.append(round(sm["uvs"][i + 1] * sv + v0, 4))
                                sm["uvs"] = new_uvs
                        elif mant_tex and mname == "1itcbody4":
                            sm["texture"] = mant_tex
                        else:
                            sm["texture"] = body_tex
                        selected_meshes.append(sm)

                # Compute per-character canonical bone joint positions from weighted vertices
                sums = {i: [0.0, 0.0, 0.0, 0.0] for i in range(len(CANONICAL_BONES))}
                for sm in selected_meshes:
                    pos_arr = sm["positions"]
                    si_arr = sm["skinIndices"]
                    sw_arr = sm["skinWeights"]
                    nv = len(pos_arr) // 3
                    for v in range(nv):
                        vx, vy, vz = pos_arr[v*3], pos_arr[v*3+1], pos_arr[v*3+2]
                        for k in range(4):
                            bi = si_arr[v*4 + k]
                            wi = sw_arr[v*4 + k]
                            if wi > 0.1:
                                sums[bi][0] += vx * wi
                                sums[bi][1] += vy * wi
                                sums[bi][2] += vz * wi
                                sums[bi][3] += wi

                bones_out = []
                for bi, (bname, bparent, default_pos) in enumerate(CANONICAL_BONES):
                    sx_v, sy_v, sz_v, sw_v = sums[bi]
                    if bi in (0, 1, 2, 3, 4, 5):
                        # Keep central spine/head strictly on X=0 midline for symmetrical rotations
                        jy = (sy_v / sw_v) if sw_v > 5.0 else default_pos[1]
                        if bi == 0: jy = 0.0
                        if bi == 5: jy = max(116.0, min(126.0, jy - 6.0))  # Pivot head at base of skull
                        jpos = [0.0, round(jy, 2), 0.0]
                    elif sw_v > 5.0:
                        jpos = [round(sx_v / sw_v, 2), round(sy_v / sw_v, 2), round(sz_v / sw_v, 2)]
                    else:
                        jpos = list(default_pos)
                    bones_out.append({"name": bname, "parent": bparent, "pos": jpos})

                model_out_path = os.path.join(OUT_DIR, "models", f"{cid}.json")
                os.makedirs(os.path.dirname(model_out_path), exist_ok=True)
                tot_v = sum(len(m["positions"]) // 3 for m in selected_meshes)
                tot_t = sum(len(m["indices"]) // 3 for m in selected_meshes)
                with open(model_out_path, "w", encoding="utf-8") as mf:
                    json.dump({
                        "id": cid,
                        "name": cname,
                        "bones": bones_out,
                        "meshes": selected_meshes,
                    }, mf, separators=(",", ":"))
                print(f"Saved rigged 3D model {cid}.json ({len(selected_meshes)} submeshes, {tot_v} verts, {tot_t} tris, 20 bones)")

                anm_ids = []
                if prm_name in toc_map:
                    pr = toc_map[prm_name]
                    f_dat.seek(cpk["TocOffset"] + pr["FileOffset"])
                    praw = f_dat.read(pr["FileSize"])
                    if praw[:8] == b"CRILAYLA":
                        praw = decompress_crilayla(praw)
                    anm_ids = sorted(list(set(m.group(0).decode("ascii") for m in re.finditer(b"PL_ANM_[A-Z0-9_]+", praw))))[:24]

                roster_meta.append({
                    "id": cid,
                    "name": cname,
                    "title": ctitle,
                    "role": crole,
                    "color": ccolor,
                    "portrait": f"assets/portraits/{cid}.png",
                    "model": f"assets/models/{cid}.json",
                    "textures": list(tex_files.values()),
                    "verts": tot_v,
                    "tris": tot_t,
                    "apkSource": f"assets/data/sim/data.awb -> {bod_name}",
                    "animations": anm_ids,
                })

        # 4. Extract Complete 3D Stage Map (sd00a.xfbin) from stage1.awb
        stage_textures = {}
        stage_meshes = []
        with z.open("assets/data/sim/stage1.awb") as f_stg:
            cpk = parse_utf(f_stg.read(64 * 1024), 16)[0]
            f_stg.seek(cpk["TocOffset"])
            toc = parse_utf(f_stg.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}
            if "sd00a.xfbin" in toc_map:
                r = toc_map["sd00a.xfbin"]
                f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
                sraw = f_stg.read(r["FileSize"])
                if sraw[:8] == b"CRILAYLA":
                    sraw = decompress_crilayla(sraw)
                schunks, smaps, sci, stypes, snames = parse_nucc_chunks(sraw)

                # Extract all non-shadow diffuse stage textures
                for tname, ch_name, cmap_idx, payload, pbase in schunks:
                    if tname == "nuccChunkTexture" and b"NTP3" in payload:
                        if "shadow" in ch_name.lower() or "normal" in ch_name.lower() or "height" in ch_name.lower():
                            continue
                        ntp_pos = payload.find(b"NTP3")
                        max_d = 512 if ("flo" in ch_name or "bac" in ch_name or "river" in ch_name) else 256
                        w, h, rgba, _ = decode_ntp3_texture(payload, ntp_pos + 16, max_dim=max_d)
                        write_png_rgba(os.path.join(OUT_DIR, "stage", f"{ch_name}.png"), w, h, rgba)
                        stage_textures[ch_name] = f"stage/{ch_name}.png"
                print(f"Saved {len(stage_textures)} stage textures from sd00a.xfbin")

                # Map (pbase, cmap_idx) of nuccChunkMaterial -> resolved texture name
                mat_to_tex = {}
                for tname, ch_name, cmap_idx, payload, pbase in schunks:
                    if tname == "nuccChunkMaterial":
                        u32s = struct.unpack(f">{len(payload)//4}I", payload[:(len(payload)//4)*4])
                        resolved_tex = None
                        for u in u32s[-8:]:
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
                            # Fallback by material name prefix
                            for tk, tv in stage_textures.items():
                                if tk in ch_name:
                                    resolved_tex = tv
                                    break
                        mat_to_tex[(pbase, cmap_idx)] = resolved_tex

                # Map (pbase, coord_name) -> (px, py, pz, rx, ry, rz, sx, sy, sz)
                coord_map = {}
                for tname, ch_name, cmap_idx, payload, pbase in schunks:
                    if tname == "nuccChunkCoord" and len(payload) >= 36:
                        coord_map[(pbase, ch_name)] = struct.unpack(">9f", payload[:36])

                # Tree placements from dummy_ki02..08
                tree_placements = []
                for (pbase, kname), trf in coord_map.items():
                    if kname.startswith("dummy_ki"):
                        tree_placements.append((kname, trf))

                # Extract 3D Stage Models (Ground, Cliffs, River, Fences, Training Posts, Backdrop, Sky Dome, Trees)
                tree_trunks = {}
                for tname, ch_name, cmap_idx, payload, pbase in schunks:
                    if tname != "nuccChunkModel" or b"NDP3" not in payload:
                        continue
                    low = ch_name.lower()
                    if any(skip in low for skip in ("hashadow", "mikishadow", "kage", "_lod1", "trans", "bug", "hit", "mdl0", "sun", "cam_")):
                        continue

                    if low in ("ki02_miki", "ki03_miki", "ki07_miki", "ki08_miki"):
                        if low not in tree_trunks:
                            tree_trunks[low] = (payload, pbase)
                        continue
                    if low.startswith("eda"):
                        continue

                    trf = coord_map.get((pbase, ch_name))
                    subs = decode_ndp3_mesh(payload, ch_name, is_character=False, coord_transform=trf)
                    for sm in subs:
                        tex = mat_to_tex.get((pbase, sm["mat_cmap"]))
                        if not tex:
                            if "river" in low:
                                tex = stage_textures.get("sd00a_river01_floor")
                            elif "dome" in low:
                                tex = stage_textures.get("sd00abac004") or stage_textures.get("sd00abac003")
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
                        stage_meshes.append(sm)

                # Instantiate the extracted 3D trees at their dummy_ki world coordinates
                trunk_list = list(tree_trunks.items())
                for idx_t, (dname, trf) in enumerate(tree_placements):
                    if not trunk_list:
                        break
                    t_name, (t_pay, t_pbase) = trunk_list[idx_t % len(trunk_list)]
                    subs = decode_ndp3_mesh(t_pay, f"{t_name}_{dname}", is_character=False, coord_transform=trf)
                    for sm in subs:
                        sm["texture"] = mat_to_tex.get((t_pbase, sm["mat_cmap"])) or stage_textures.get("sd00aobj008")
                        stage_meshes.append(sm)

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
                print(f"Saved 3D Stage Map stage_3d.json ({len(stage_meshes)} submeshes, {tot_sv} verts, {tot_st} tris)")

        os.makedirs(os.path.join(OUT_DIR, "data"), exist_ok=True)
        with open(os.path.join(OUT_DIR, "data", "roster_meta.json"), "w", encoding="utf-8") as rf:
            json.dump({
                "roster": roster_meta,
                "stageMap": "assets/stage/stage_3d.json",
                "stageTextures": {k: f"assets/{v}" for k, v in stage_textures.items()},
            }, rf, indent=2)
        print("Extraction complete!")


if __name__ == "__main__":
    extract_all()
