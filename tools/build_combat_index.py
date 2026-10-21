"""Build a clean per-character combat index from the extracted *prm.bin NUCC data."""

import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPC = os.path.join(ROOT, "public/assets/data/spc")
OUT = os.path.join(ROOT, "public/assets/data/combat_params.json")

ANIM_RE = re.compile(rb"(PL_ANM)_([A-Z0-9]+)\x00")
ID_RE = re.compile(rb"\b(1[a-z]{3}[a-z0-9]{2,12})\x00")


def group(stem):
    for pre, name in (
        ("CMB", "combo"), ("RPG", "rpg_skill"), ("FALL", "airborne"), ("NUT", "nutada"),
        ("LAN", "landing"), ("ENTR", "entrance"), ("EXIT", "exit"), ("RUN", "run"),
        ("RXN", "reaction"), ("TRN", "turn"), ("JMP", "jump"), ("NXJ", "next_jump"),
        ("INN", "in"), ("IXN", "out"), ("PLEA", "plea"), ("ETC", "etc"), ("CATC", "catch"),
    ):
        if stem.startswith(pre):
            return name
    return "other"


def main():
    chars = defaultdict(lambda: {"anim": defaultdict(list), "subtables": [], "files": []})
    for fn in sorted(os.listdir(SPC)):
        if not fn.endswith(".xfbin"):
            continue
        data = open(os.path.join(SPC, fn), "rb").read()
        m = re.search(r"data_spc_(1[a-z]{3})", fn)
        if not m:
            continue
        c = chars[m.group(1)]
        c["files"].append(fn)
        subs = sorted({s.decode() for s in re.findall(rb"\b1[a-z]{3}prm_(\w+?)\.bin", data)})
        if subs:
            c["subtables"] = sorted(set(c["subtables"]) | set(subs))
        for mm in ANIM_RE.finditer(data):
            c["anim"][group(mm.group(2).decode())].append(mm.group(2).decode())
        ids = sorted({s.decode() for s in ID_RE.findall(data)})
        if ids:
            c.setdefault("asset_ids", sorted(set(c.get("asset_ids", [])) | set(ids)))

    out = {}
    for cid, v in sorted(chars.items()):
        out[cid] = {
            "subtables": v["subtables"],
            "files": v["files"],
            "asset_ids": v.get("asset_ids", [])[:80],
            "anim_groups": {k: sorted(set(x)) for k, x in sorted(v["anim"].items())},
            "anim_total": sum(len(set(x)) for x in v["anim"].values()),
        }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"{len(out)} characters -> {OUT}")
    sample = out.get("1nrt", {})
    print("\n1nrt groups:")
    for k, vs in sample.get("anim_groups", {}).items():
        print(f"  {k:12s} {len(vs):3d}  {' '.join(vs[:12])}")
    print("subtables:", sample.get("subtables"))


if __name__ == "__main__":
    sys.exit(main())