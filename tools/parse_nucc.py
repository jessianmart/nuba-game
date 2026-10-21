"""Parse NUCC (.xfbin) containers into JSON: string tables + numeric payloads."""

import json
import os
import re
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

STRING_RE = re.compile(rb"[ -~]{4,}")


def strings(data, min_len=4):
    return [s.decode() for s in STRING_RE.findall(data)]


def floats(data):
    out = []
    for i in range(0, len(data) - 3, 4):
        v, = struct.unpack_from("<f", data, i)
        if v == v and abs(v) < 1e7 and (v == 0.0 or 1e-4 < abs(v) < 1e6):
            out.append(v)
    return out


def chunks(data):
    """Walk the NUCC chunk table. Offsets validated against the magic names present."""
    if data[:4] != b"NUCC":
        return []
    dir_off = struct.unpack_from("<I", data, 0x10)[0]
    count = struct.unpack_from("<I", data, 0x14)[0]
    names = []
    for name in (b"nuccChunkNull", b"nuccChunkBinary", b"nuccChunkPage",
                 b"nuccChunkIndex", b"nuccChunkTexture", b"nuccChunkModel",
                 b"nuccChunkAnimation", b"nuccChunkName", b"nuccChunkMotion"):
        p = data.find(name)
        if p != -1:
            names.append((p, name.decode()))
    return {"dir_offset": dir_off, "chunk_count": count,
            "type_table": [{"offset": p, "name": n} for p, n in names]}


def parse_dir(path, out_path, min_strings=1):
    result = {}
    for fn in sorted(os.listdir(path)):
        fp = os.path.join(path, fn)
        if not os.path.isfile(fp):
            continue
        data = open(fp, "rb").read()
        ss = strings(data)
        # drop container noise
        ss = [s for s in ss if not s.startswith("nuccChunk") and len(s) >= min_strings]
        if not ss and not chunks(data):
            continue
        char = re.search(r"(1[a-z]{3})", fn)
        result[fn] = {
            "character": char.group(1) if char else None,
            "bytes": len(data),
            "header": chunks(data),
            "strings": ss,
            "float_count": len(floats(data)),
        }
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=1, ensure_ascii=False)
    total = sum(len(v["strings"]) for v in result.values())
    print(f"{len(result)} files, {total} strings -> {out_path}")
    return result


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "public/assets/data/spc")
    dst = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, "public/assets/data/combat_params.json")
    r = parse_dir(src, dst)
    chars = sorted({v["character"] for v in r.values() if v["character"]})
    print(f"characters: {len(chars)} -> {' '.join(chars)}")