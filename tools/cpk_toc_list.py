"""List the internal TOC of every .awb (CPK) archive without extracting."""

import collections
import os
import struct
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apk_inspect import APK_PATH, parse_utf  # noqa: E402


def toc_of(z, name):
    with z.open(name) as f:
        hdr = f.read(64 * 1024)
        cpk = parse_utf(hdr, 16)[0]
        f.seek(cpk["TocOffset"])
        return parse_utf(f.read(cpk["TocSize"]), 16)


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.1f}{u}" if u != "B" else f"{n}B"
        n /= 1024


def main(keywords):
    with zipfile.ZipFile(APK_PATH) as z:
        awbs = [n for n in z.namelist() if n.endswith(".awb")]
        grand = collections.defaultdict(lambda: [0, 0])
        for awb in sorted(awbs):
            toc = toc_of(z, awb)
            print(f"\n{'=' * 78}\n{awb}  ->  {len(toc)} entries")
            for r in toc:
                fn = r.get("FileName", "")
                dn = r.get("DirName", "")
                full = f"{dn}/{fn}" if dn else fn
                fs, es = r.get("FileSize", 0), r.get("ExtractSize", 0)
                ext = os.path.splitext(fn)[1].lower() or "<none>"
                grand[ext][0] += 1
                grand[ext][1] += es
                if any(k.lower() in full.lower() for k in keywords):
                    print(f"    {full:60s} {human(fs):>9s} -> {human(es):>9s}")
        print(f"\n{'=' * 78}\n=== GRAND TOTAL across all CPKs, by extension ===")
        tot = 0
        for k, (c, s) in sorted(grand.items(), key=lambda kv: -kv[1][1]):
            tot += s
            print(f"  {k:12s} {c:8d} files  {human(s):>10s}")
        print(f"  {'TOTAL':12s} {'':8s}       {human(tot):>10s}")


if __name__ == "__main__":
    kws = sys.argv[1:] or [".xfbin", ".nsh", ".spv"]
    main(kws)