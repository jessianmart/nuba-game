"""Streaming inventory of the Storm APK. Extracts nothing to disk."""

import collections
import os
import struct
import sys
import zipfile

APK_PATH = r"C:\Users\jessi\Downloads\naruto-ultimate-ninja-storm-mod_129_working_1791703630.apk"


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f}{unit}" if unit != "B" else f"{n}B"
        n /= 1024


def inventory():
    with zipfile.ZipFile(APK_PATH) as z:
        infos = z.infolist()
        print(f"entries: {len(infos)}")
        print(f"total uncompressed: {human(sum(i.file_size for i in infos))}")
        print(f"total compressed:   {human(sum(i.compress_size for i in infos))}")

        by_ext = collections.defaultdict(lambda: [0, 0])
        top = collections.defaultdict(lambda: [0, 0])
        for i in infos:
            ext = os.path.splitext(i.filename)[1].lower() or "<none>"
            by_ext[ext][0] += 1
            by_ext[ext][1] += i.file_size
            top[i.filename.split("/")[0]][0] += 1
            top[i.filename.split("/")[0]][1] += i.file_size

        print("\n=== by top-level dir ===")
        for k, (c, s) in sorted(top.items(), key=lambda kv: -kv[1][1]):
            print(f"  {k:30s} {c:7d} files  {human(s):>10s}")

        print("\n=== by extension (top 45) ===")
        for k, (c, s) in sorted(by_ext.items(), key=lambda kv: -kv[1][1])[:45]:
            print(f"  {k:14s} {c:7d} files  {human(s):>10s}")

        print("\n=== native libs ===")
        for i in sorted(infos, key=lambda i: -i.file_size):
            if i.filename.startswith("lib/"):
                print(f"  {i.filename:55s} {human(i.file_size):>10s}")

        print("\n=== 40 largest entries ===")
        for i in sorted(infos, key=lambda i: -i.file_size)[:40]:
            print(f"  {i.filename:70s} {human(i.file_size):>10s}")

        print("\n=== .dex / classes ===")
        for i in infos:
            if i.filename.endswith(".dex"):
                print(f"  {i.filename:55s} {human(i.file_size):>10s}")

        print("\n=== asset archives (.awb / .obb / .pak) ===")
        for i in infos:
            if i.filename.endswith((".awb", ".obb", ".pak", ".unity3d")):
                print(f"  {i.filename:55s} {human(i.file_size):>10s}")

        return infos


def manifest_strings():
    with zipfile.ZipFile(APK_PATH) as z:
        raw = z.read("AndroidManifest.xml")
    strings, cur = [], bytearray()
    for b in raw:
        if 32 <= b < 127:
            cur.append(b)
        else:
            if len(cur) >= 4:
                strings.append(cur.decode())
            cur = bytearray()
    print(f"\n=== AndroidManifest.xml strings ({len(strings)}) ===")
    for s in strings:
        print("  " + s)


def dex_class_names():
    with zipfile.ZipFile(APK_PATH) as z:
        names = [n for n in z.namelist() if n.endswith(".dex")]
        for n in names:
            raw = z.read(n)
            count, = struct.unpack("<I", raw[0x38:0x3C])
            out = set()
            off = 0x70
            for _ in range(count):
                idx, = struct.unpack("<I", raw[off:off + 4])
                off += 8
                _, str_off = struct.unpack("<II", raw[off - 8:off])
                m = re_type(raw, str_off)
                if m:
                    out.add(m)
            print(f"\n=== {n}: {count} type refs, {len(out)} class names ===")
            for c in sorted(out)[:400]:
                print("  " + c)


def re_type(raw: bytes, off: int):
    try:
        size = raw[off]
        end = raw.index(0, off + 1)
        s = raw[off + 1:end].decode("utf-8", "replace")
        return s if size else None
    except Exception:
        return None


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "inventory"
    if cmd == "inventory":
        inventory()
    elif cmd == "manifest":
        manifest_strings()
    elif cmd == "dex":
        dex_class_names()