"""Dry-run size accounting for CPK extraction plans. Writes nothing."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cpk_extract import find, free_gb_report  # noqa: E402


def human(n):
    for u in ("B", "KB", "MB", "GB"):
        if n < 1024 or u == "GB":
            return f"{n:.1f}{u}" if u != "B" else f"{n}B"
        n /= 1024


def main(patterns, limit_bytes=None):
    total = 0
    n = 0
    for awb, row, full in find(patterns):
        if limit_bytes and total >= limit_bytes:
            break
        est = row.get("ExtractSize") or row.get("FileSize") or 0
        total += est
        n += 1
        print(f"  {full:62s} {human(est):>9s}  [{awb.split('/')[-1]}]")
    print(f"\n{n} files, {human(total)} decompressed. {free_gb_report()}")
    return total


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--limit=")]
    limit = next((int(a.split("=")[1]) for a in sys.argv[1:] if a.startswith("--limit=")), None)
    main(args or ["xfbin"], limit)