"""Selective reader/extractor for CPK (.awb) archives inside the Storm APK.

Streams from the APK zip; never unpacks the whole archive.
"""

import os
import posixpath
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.apk_inspect import APK_PATH, decompress_crilayla, parse_utf  # noqa: E402

MIN_FREE_GB = 3.0


class DiskFull(Exception):
    pass


def free_gb(path=None):
    path = path or os.path.splitdrive(APK_PATH)[0] + "\\"
    import shutil
    return shutil.disk_usage(path).free / 1024 ** 3


def check_space(need_bytes, reserve_gb=MIN_FREE_GB):
    if free_gb() - need_bytes / 1024 ** 3 < reserve_gb:
        raise DiskFull(
            f"need {need_bytes / 1024 ** 3:.2f}GB, free {free_gb():.2f}GB, "
            f"reserve {reserve_gb}GB"
        )


_toc_cache = {}


def cpk_path(needle):
    """Resolve an APK-internal path to an .awb holding an entry matching `needle`."""
    with zipfile.ZipFile(APK_PATH) as z:
        for name in z.namelist():
            if name.endswith(".awb") and needle in name:
                return name
    return None


def toc_of(z, awb):
    if awb not in _toc_cache:
        with z.open(awb) as f:
            cpk = parse_utf(f.read(64 * 1024), 16)[0]
            f.seek(cpk["TocOffset"])
            _toc_cache[awb] = (cpk, parse_utf(f.read(cpk["TocSize"]), 16))
    return _toc_cache[awb]


def entry_name(r):
    dn, fn = r.get("DirName", ""), r.get("FileName", "")
    return posixpath.join(dn, fn) if dn else fn


def find(patterns, exclude=()):
    """Yield (awb, row, fullname) for every entry matching a pattern and no exclusion."""
    if isinstance(patterns, str):
        patterns = [patterns]
    pats = [p.lower() for p in patterns]
    exs = [e.lower() for e in exclude]
    with zipfile.ZipFile(APK_PATH) as z:
        for awb in sorted(n for n in z.namelist() if n.endswith(".awb")):
            _, toc = toc_of(z, awb)
            for r in toc:
                full = entry_name(r)
                low = full.lower()
                if any(p in low for p in pats) and not any(e in low for e in exs):
                    yield awb, r, full


def read(awb, row):
    with zipfile.ZipFile(APK_PATH) as z:
        with z.open(awb) as f:
            cpk, _ = toc_of(z, awb)
            f.seek(cpk["TocOffset"] + row["FileOffset"])
            raw = f.read(row["FileSize"])
    if raw[:8] == b"CRILAYLA":
        return decompress_crilayla(raw)
    return raw


def read_by_name(fullname, prefer_largest=True):
    """Fetch one entry by its exact internal path."""
    matches = [
        (a, r, f) for a, r, f in find(fullname)
        if f.lower() == fullname.lower()
    ]
    if not matches:
        matches = [(a, r, f) for a, r, f in find(fullname)]
    if not matches:
        raise FileNotFoundError(fullname)
    awb, row, _ = max(matches, key=lambda m: m[1]["FileSize"]) if prefer_largest else matches[0]
    return read(awb, row)


def extract(patterns, out_dir, limit_bytes=None, dry_run=False, reserve_gb=MIN_FREE_GB,
            transform=None, name_fn=None, verbose=True, exclude=()):
    """Extract matching entries to out_dir, honouring a byte budget.

    transform(bytes, fullname) -> bytes | None lets callers convert (e.g. PNG decode)
    before anything hits disk.
    """
    os.makedirs(out_dir, exist_ok=True)
    written = 0
    count = 0
    skipped = 0
    for awb, row, full in find(patterns, exclude):
        if limit_bytes is not None and written >= limit_bytes:
            skipped += 1
            continue
        est = row.get("ExtractSize") or row.get("FileSize") or 0
        if limit_bytes is not None and written + est > limit_bytes:
            skipped += 1
            continue
        data = transform(read(awb, row), full) if transform else None
        if transform and data is None:
            skipped += 1
            continue
        if data is None:
            data = read(awb, row)
        if not dry_run:
            check_space(len(data), reserve_gb)
            name = name_fn(full) if name_fn else os.path.basename(full)
            with open(os.path.join(out_dir, name), "wb") as f:
                f.write(data)
        written += len(data)
        count += 1
        if verbose:
            print(f"  {full} -> {len(data)} bytes")
    return count, written, skipped


def free_gb_report():
    return f"free={free_gb():.2f}GB"


if __name__ == "__main__":
    for a, r, full in find(sys.argv[1:] or ["xfbin"]):
        print(f"{a}\t{r['FileSize']}\t{r.get('ExtractSize', 0)}\t{full}")