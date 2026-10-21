"""Fase 1: combat params, SFX banks and stage metadata."""

import json
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cpk_extract import extract, free_gb_report  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "public", "assets")

LOTS = [
    ("combat_params", ["data/spc/"], os.path.join(OUT, "data", "spc"),
     ["bod1", "bod2", "bod3", "bod4", "awa.xfbin", "_mg.xfbin", "test"]),
    ("sfx_banks", ["data/sound/Se/", "data/sound/NS1.acf", "data/sound/config.nus3conf"],
     os.path.join(OUT, "audio"), []),
    ("stage_meta", ["data/stage/StageAreaInfo.bin.xfbin", "data/stage/GIMKonohaAct",
                    "data/stage/CAMKonohaAct", "data/stage/FLYKonohaAct",
                    "data/stage/SCRKonohaAct", "data/stage/MAPKonohaAct",
                    "data/stage/DMYKonohaAct", "data/stage/GIMTraining",
                    "data/stage/GIMForestAct", "data/stage/GIMKonohaActPerson"],
     os.path.join(OUT, "data", "stage_meta"), []),
]


def flatten(full):
    return full.replace("/", "_").replace("\\", "_")


def run(lot_filter=None, dry_run=False):
    report = {}
    for name, patterns, dest, exclude in LOTS:
        if lot_filter and name not in lot_filter:
            continue
        print(f"\n=== {name} -> {os.path.relpath(dest, ROOT)} ({free_gb_report()}) ===")
        n, written, skipped = extract(patterns, dest, dry_run=dry_run,
                                      name_fn=flatten, exclude=exclude)
        print(f"  -> {n} files, {written / 1024 / 1024:.2f} MB, skipped {skipped}")
        report[name] = {"files": n, "bytes": written, "skipped": skipped}
    with open(os.path.join(OUT, "data", "fase1_report.json"), "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nDone. {free_gb_report()}")


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    lots = [a for a in sys.argv[1:] if not a.startswith("--")]
    run(lots or None, dry)