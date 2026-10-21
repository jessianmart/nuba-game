import zipfile
import struct
from collections import Counter
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import decode_ndp3_mesh


def parse_nucc_exact(data: bytes):
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
    # The 8-byte extra table sits right BEFORE chunk_indices!
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
            p_len, p_ex = struct.unpack(">II", payload[:8])
            page_base += p_len
        chunk_pos += 12 + csz
    return chunks, maps, chunk_indices, types, names


def main():
    with zipfile.ZipFile(APK_PATH, "r") as z:
        # 1. Test on 1nrtbod1c.xfbin
        with z.open("assets/data/sim/data.awb") as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk["TocOffset"])
            toc = parse_utf(f_dat.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}
            rc = toc_map["1nrtbod1c.xfbin"]
            f_dat.seek(cpk["TocOffset"] + rc["FileOffset"])
            raw_c = decompress_crilayla(f_dat.read(rc["FileSize"]))
            chunks_c, _, _, _, _ = parse_nucc_exact(raw_c)
            print("1nrtbod1c.xfbin Chunks:", Counter(c[0] for c in chunks_c))
            for tname, cname, cmap, pay, pbase in chunks_c:
                if tname == "nuccChunkAnm" and cname in ("1nrtnut0", "1nrtdsh0l", "1nrtjmp0"):
                    print(f"\nANM {cname} (len={len(pay)}, pbase={pbase}):")
                    print("  00..40:", pay[:64].hex())
                    print("  40..80:", pay[64:128].hex())
                    print("  80..C0:", pay[128:192].hex())

        # 2. Test on sd00a.xfbin
        with z.open("assets/data/sim/stage1.awb") as f_stg:
            cpk = parse_utf(f_stg.read(65536), 16)[0]
            f_stg.seek(cpk["TocOffset"])
            toc = parse_utf(f_stg.read(cpk["TocSize"]), 16)
            toc_map = {r["FileName"].lower(): r for r in toc}
            r = toc_map["sd00a.xfbin"]
            f_stg.seek(cpk["TocOffset"] + r["FileOffset"])
            sraw = decompress_crilayla(f_stg.read(r["FileSize"]))
            schunks, _, _, _, _ = parse_nucc_exact(sraw)
            print("\nsd00a.xfbin Chunks:", Counter(c[0] for c in schunks))
            smodels = [(c[1], c[2], len(c[3]), c[3]) for c in schunks if c[0] == "nuccChunkModel" and b"NDP3" in c[3]]
            print(f"sd00a NDP3 models ({len(smodels)}):")
            for name, cmap, sz, pay in smodels:
                subs = decode_ndp3_mesh(pay, name, is_character=False)
                v_cnt = sum(len(s["positions"]) // 3 for s in subs)
                t_cnt = sum(len(s["indices"]) // 3 for s in subs)
                if subs:
                    xs = [x for s in subs for x in s["positions"][0::3]]
                    ys = [y for s in subs for y in s["positions"][1::3]]
                    zs = [zv for s in subs for zv in s["positions"][2::3]]
                    print(f"  {name:26s} subs={len(subs)} verts={v_cnt:5d} tris={t_cnt:5d} X=[{min(xs):.0f}..{max(xs):.0f}] Y=[{min(ys):.0f}..{max(ys):.0f}] Z=[{min(zs):.0f}..{max(zs):.0f}]")


if __name__ == "__main__":
    main()
