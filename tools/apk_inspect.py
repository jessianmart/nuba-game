import zipfile
import struct
import sys
import os
import re

APK_PATH = r"C:\Users\jessi\Downloads\naruto-ultimate-ninja-storm-mod_129_working_1791703630.apk"

def parse_utf(data: bytes, offset: int = 0):
    magic = data[offset:offset+4]
    if magic != b'@UTF':
        raise ValueError(f"Not @UTF at {offset}: {magic}")
    table_size, = struct.unpack('>I', data[offset+4:offset+8])
    t = data[offset+8:offset+8+table_size]
    rows_offset, strings_offset, data_offset, table_name_off, num_cols, row_len, num_rows = struct.unpack('>IIIIHHI', t[:24])

    def get_str(off: int) -> str:
        s_start = strings_offset + off
        s_end = t.index(b'\x00', s_start)
        return t[s_start:s_end].decode('utf-8', errors='replace')

    pos = 24
    cols = []
    for _ in range(num_cols):
        flags = t[pos]
        pos += 1
        if flags == 0:
            flags = t[pos]
            pos += 1
        col_type = flags & 0x0F
        storage = flags & 0xF0
        name_off, = struct.unpack('>I', t[pos:pos+4])
        pos += 4
        col_name = get_str(name_off)
        const_val = None
        if storage == 0x30:
            if col_type in (0, 1):
                const_val = t[pos]; pos += 1
            elif col_type in (2, 3):
                const_val, = struct.unpack('>H', t[pos:pos+2]); pos += 2
            elif col_type in (4, 5):
                const_val, = struct.unpack('>I', t[pos:pos+4]); pos += 4
            elif col_type in (6, 7):
                const_val, = struct.unpack('>Q', t[pos:pos+8]); pos += 8
            elif col_type == 8:
                const_val, = struct.unpack('>f', t[pos:pos+4]); pos += 4
            elif col_type == 10:
                soff, = struct.unpack('>I', t[pos:pos+4]); pos += 4
                const_val = get_str(soff)
            elif col_type == 11:
                boff, bsize = struct.unpack('>II', t[pos:pos+8]); pos += 8
                const_val = (data_offset + boff, bsize)
        cols.append((col_name, col_type, storage, const_val))

    rows = []
    for r in range(num_rows):
        rpos = rows_offset + r * row_len
        row = {}
        for col_name, col_type, storage, const_val in cols:
            if storage in (0x10, 0x00, 0x70):
                row[col_name] = None
            elif storage == 0x30:
                row[col_name] = const_val
            elif storage == 0x50:
                if col_type in (0, 1):
                    val = t[rpos]; rpos += 1
                elif col_type in (2, 3):
                    val, = struct.unpack('>H', t[rpos:rpos+2]); rpos += 2
                elif col_type in (4, 5):
                    val, = struct.unpack('>I', t[rpos:rpos+4]); rpos += 4
                elif col_type in (6, 7):
                    val, = struct.unpack('>Q', t[rpos:rpos+8]); rpos += 8
                elif col_type == 8:
                    val, = struct.unpack('>f', t[rpos:rpos+4]); rpos += 4
                elif col_type == 10:
                    soff, = struct.unpack('>I', t[rpos:rpos+4]); rpos += 4
                    val = get_str(soff)
                elif col_type == 11:
                    boff, bsize = struct.unpack('>II', t[rpos:rpos+8]); rpos += 8
                    val = (data_offset + boff, bsize)
                row[col_name] = val
        rows.append(row)
    return rows


import ctypes

_crilayla_dll = None
_dll_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crilayla_fast.dll")
if os.path.exists(_dll_path):
    try:
        _crilayla_dll = ctypes.CDLL(_dll_path)
        _crilayla_dll.decompress_crilayla_c.argtypes = [
            ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_int
        ]
        _crilayla_dll.decompress_crilayla_c.restype = ctypes.c_int
    except Exception:
        _crilayla_dll = None


def decompress_crilayla(src: bytes) -> bytes:
    if src[:8] != b'CRILAYLA':
        return src
    uncomp_size, comp_size = struct.unpack('<II', src[8:16])
    total_out = uncomp_size + 0x100

    if _crilayla_dll:
        out_buf = ctypes.create_string_buffer(total_out)
        res = _crilayla_dll.decompress_crilayla_c(src, len(src), out_buf, total_out)
        if res == total_out:
            return out_buf.raw

    header_prefix = src[16 + comp_size : 16 + comp_size + 0x100]
    out = bytearray(total_out)
    out[:0x100] = header_prefix

    in_pos = 16 + comp_size - 1
    bit_buf = 0
    bits_left = 0

    def get_bits(n: int) -> int:
        nonlocal in_pos, bit_buf, bits_left
        while bits_left < n:
            if in_pos >= 16:
                bit_buf = (bit_buf << 8) | src[in_pos]
                in_pos -= 1
            else:
                bit_buf = (bit_buf << 8)
            bits_left += 8
        bits_left -= n
        val = (bit_buf >> bits_left) & ((1 << n) - 1)
        bit_buf &= (1 << bits_left) - 1
        return val

    out_pos = 0x100 + uncomp_size - 1
    vle_lens = (2, 3, 5, 8)
    while out_pos >= 0x100:
        if get_bits(1):
            offset = out_pos + get_bits(13) + 3
            length = 3
            for vle in vle_lens:
                this_level = get_bits(vle)
                length += this_level
                if this_level != ((1 << vle) - 1):
                    break
            else:
                while True:
                    this_level = get_bits(8)
                    length += this_level
                    if this_level != 255:
                        break
            for _ in range(length):
                out[out_pos] = out[offset]
                out_pos -= 1
                offset -= 1
                if out_pos < 0x100:
                    break
        else:
            out[out_pos] = get_bits(8)
            out_pos -= 1

    return bytes(out)


def read_cpk_file(apk_entry_name: str, target_filename: str) -> bytes:
    with zipfile.ZipFile(APK_PATH, 'r') as z:
        with z.open(apk_entry_name) as f:
            header = f.read(64 * 1024)
            cpk_rows = parse_utf(header, 16)
            toc_off = cpk_rows[0]['TocOffset']
            toc_size = cpk_rows[0]['TocSize']
            f.seek(toc_off)
            toc_bytes = f.read(toc_size)
            toc_rows = parse_utf(toc_bytes, 16)
            for r in toc_rows:
                fname = r.get('FileName', '')
                dname = r.get('DirName', '')
                full = f"{dname}/{fname}" if dname else fname
                if fname.lower() == target_filename.lower() or full.lower().endswith(target_filename.lower()):
                    file_off = toc_off + r['FileOffset']
                    f.seek(file_off)
                    raw = f.read(r['FileSize'])
                    if raw[:8] == b'CRILAYLA':
                        return decompress_crilayla(raw)
                    return raw
    raise FileNotFoundError(f"{target_filename} not found in {apk_entry_name}")


def search_all_cpks(keywords):
    cpks = [
        'assets/data/sim/installTime.awb',
        'assets/data/sim/data.awb',
        'assets/data/sim/data2.awb',
        'assets/data/sim/stage1.awb',
        'assets/data/sim/stage2.awb',
        'assets/data/disc/installTimeDisc.awb',
        'assets/data/disc/dataRegion.awb',
    ]
    with zipfile.ZipFile(APK_PATH, 'r') as z:
        for cpk_path in cpks:
            with z.open(cpk_path) as f:
                cpk = parse_utf(f.read(64*1024), 16)[0]
                f.seek(cpk['TocOffset'])
                toc = parse_utf(f.read(cpk['TocSize']), 16)
                print(f"=== {cpk_path} ({len(toc)} files) ===")
                for r in toc:
                    fn = f"{r.get('DirName','')}/{r.get('FileName','')}"
                    if any(k.lower() in fn.lower() for k in keywords):
                        print(f"  {fn:50s} Size={r['FileSize']:9d} Extract={r['ExtractSize']:9d}")


def inspect_ntp3_and_ndp3(data: bytes):
    # Inspect first NTP3 texture header and first NDP3 model header
    ntp_off = data.find(b'NTP3')
    if ntp_off != -1:
        print(f"\n--- First NTP3 at {ntp_off} ---")
        b = data[ntp_off:ntp_off+96]
        for i in range(0, len(b), 16):
            hx = ' '.join(f'{x:02X}' for x in b[i:i+16])
            asc = ''.join(chr(x) if 32<=x<=126 else '.' for x in b[i:i+16])
            print(f"  {i:04X}: {hx:48s} | {asc}")

    ndp_off = data.find(b'NDP3')
    if ndp_off != -1:
        print(f"\n--- First NDP3 at {ndp_off} ---")
        b = data[ndp_off:ndp_off+128]
        for i in range(0, len(b), 16):
            hx = ' '.join(f'{x:02X}' for x in b[i:i+16])
            asc = ''.join(chr(x) if 32<=x<=126 else '.' for x in b[i:i+16])
            print(f"  {i:04X}: {hx:48s} | {asc}")


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'search'
    if cmd == 'search':
        kws = sys.argv[2:] if len(sys.argv) > 2 else ['1nrt', '1ssk', 'sel', 'title', 'gauge']
        search_all_cpks(kws)
    elif cmd == 'headers':
        raw = read_cpk_file('assets/data/sim/data.awb', '1nrtbod1.xfbin')
        inspect_ntp3_and_ndp3(raw)
    elif cmd == 'fig':
        raw = read_cpk_file('assets/data/sim/data2.awb', '1nrtfig1.xfbin')
        tbl_sz, = struct.unpack('>I', raw[0x10:0x14])
        ntypes, sz_types, npaths, sz_paths, nnames, sz_names, nmaps, sz_maps, nrefs = struct.unpack('>9I', raw[0x1C:0x40])
        pos = 0x44
        def rc(buf, c):
            res, p = [], 0
            for _ in range(c):
                e = buf.index(b'\x00', p)
                res.append(buf[p:e].decode('utf-8', errors='replace'))
                p = e + 1
            return res
        types = rc(raw[pos:pos+sz_types], ntypes); pos += sz_types
        paths = rc(raw[pos:pos+sz_paths], npaths); pos += sz_paths
        names = rc(raw[pos:pos+sz_names], nnames); pos += sz_names
        print("1nrtfig1 types:", types)
        print("1nrtfig1 names sample (first 50):", names[:50])
        print("Total names in 1nrtfig1:", len(names))

