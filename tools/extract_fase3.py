"""Fase 3: bulk asset expansion with a hard byte ceiling per lot."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cpk_extract import extract, free_gb_report  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")
MB = 1024 * 1024

LOTS = [
    {
        "name": "puppets",
        "patterns": ["data/puppet/"],
        "exclude": ["_mg", "test"],
        "dest": os.path.join(OUT, "models", "puppets"),
        "budget": 400 * MB,
    },
    {
        "name": "ui_extra",
        "patterns": ["data/interface/sel1/", "data/interface/battle_mode/",
                     "data/interface/face/", "data/interface/sel2/"],
        "exclude": [],
        "dest": os.path.join(OUT, "ui", "raw"),
        "budget": 150 * MB,
    },
    {
        "name": "stages",
        "patterns": ["data/stage/sd", "data/stage/sa0", "data/stage/sk0",
                     "data/stage/sm0"],
        "exclude": ["sd00a", "sa00z", "sa01z", "stest", "s1ball", "s2aall"],
        "dest": os.path.join(OUT, "stage", "raw"),
        "budget": 900 * MB,
    },
]


def flatten(full):
    return full.replace("/", "_").replace("\\", "_")


def run(names=None, dry_run=False):
    report = {}
    for lot in LOTS:
        if names and lot["name"] not in names:
            continue
        print(f"\n=== {lot['name']} -> {os.path.relpath(lot['dest'], ROOT)} "
              f"(budget {lot['budget'] / MB:.0f}MB, {free_gb_report()}) ===")
        n, written, skipped = extract(lot["patterns"], lot["dest"],
                                      limit_bytes=lot["budget"],
                                      dry_run=dry_run, name_fn=flatten,
                                      exclude=lot["exclude"], verbose=False)
        print(f"  -> {n} files, {written / MB:.1f} MB, skipped {skipped} "
              f"(budget stop), {free_gb_report()}")
        report[lot["name"]] = {"files": n, "mb": round(written / MB, 1),
                               "skipped": skipped}
    path = os.path.join(OUT, "data", "fase3_report.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDone. {free_gb_report()}")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    lots = [a for a in sys.argv[1:] if not a.startswith("--")]
    run(lots or None, dry)