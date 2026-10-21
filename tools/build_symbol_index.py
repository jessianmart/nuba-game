"""Demangle every recovered symbol and build a class -> methods architecture index."""

import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.demangle import demangle  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "public/assets/data/so_symbols.json")
OUT_JSON = os.path.join(ROOT, "public/assets/data/so_class_index.json")
OUT_MD = os.path.join(ROOT, "public/assets/data/so_class_index.md")

SUBSYSTEMS = {
    "player": r"ccPlayer|PlayerLeader|CpuPlayer|PlayerPad|PlayerRpg",
    "chakra": r"Chakra|Cakra",
    "skill": r"Skill|Skl|Ninjutsu|Jutsu|Ougi|Ultimate|Secret",
    "collision": r"Collision|Hit|Attack|Damage|Dmg|Guard|Dodge",
    "effect": r"Effect|Vfx|Particle|Billboard|Spark",
    "ai": r"BaseAI|CpuAI|NpcAI|AI_",
    "status": r"Status|Poison|Confus|Stun|Slow|Seal|Trap",
    "item": r"Item|Equip|Weapon|Costume|Consum",
    "stage": r"Stage|Arena|Spawn|Checkpoint",
    "team": r"Team|Counter|Score|Kill|Respawn|Revive|LifeGauge",
    "ui": r"Hud|Interface|Menu|Gauge|Icon|Pad",
    "motion": r"Motion|Anim|Cmab|Clump|GimData",
    "sound": r"Sound|Audio|Nus3|Wav|Adx|Bgm|Voice",
    "net": r"Lobby|Online|Network|Packet|Multiplayer|Photon",
}


def classify(cls):
    for name, pat in SUBSYSTEMS.items():
        if re.search(pat, cls, re.I):
            return name
    return "other"


def main():
    data = json.load(open(SRC, encoding="utf-8"))
    funcs = data["functions"]

    classes = defaultdict(lambda: {"methods": [], "statics": [], "unresolved": 0})
    unresolved = 0
    for f in funcs:
        d = demangle(f)
        if d == f:
            unresolved += 1
            continue
        m = re.match(r"^(.*?)([A-Za-z_~][^:()]*)\((.*)\)$", d)
        if not m:
            classes["<free functions>"]["methods"].append(d)
            continue
        prefix, method, args = m.groups()
        if not prefix:
            classes["<free functions>"]["methods"].append(d)
            continue
        owner = prefix.rsplit("::", 1)[0] if "::" in prefix else prefix
        member = prefix.rsplit("::", 1)[-1] if "::" in prefix else ""
        key = f"{owner}::{member}" if member and member[0].islower() else owner
        entry = f"{method}({args})" if not method[0].islower() else f"{member}::{method}({args})"
        classes[key]["methods"].append(entry)

    index = {}
    for cls, v in classes.items():
        sub = classify(cls)
        index[cls] = {
            "subsystem": sub,
            "method_count": len(v["methods"]),
            "methods": sorted(set(v["methods"])),
        }

    by_sub = defaultdict(list)
    for cls, v in index.items():
        by_sub[v["subsystem"]].append((v["method_count"], cls))

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump({"library": data["library"], "class_count": len(index),
                   "classes": index}, f, indent=1)

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("# Class index recovered from `libultimateninjastorm.so`\n\n")
        f.write(f"- Classes recovered: **{len(index)}**\n")
        f.write(f"- Unresolved symbols: {unresolved}\n\n")
        f.write("## Subsystems\n\n| Subsystem | Classes | Methods |\n|---|---:|---:|\n")
        for sub, items in sorted(by_sub.items(), key=lambda kv: -len(kv[1])):
            f.write(f"| {sub} | {len(items)} | {sum(c for c, _ in items)} |\n")
        for sub, items in sorted(by_sub.items(), key=lambda kv: -len(kv[1])):
            if sub == "other":
                continue
            f.write(f"\n## {sub} ({len(items)} classes)\n\n")
            f.write("| Class | Methods |\n|---|---:|\n")
            for count, cls in sorted(items, key=lambda x: -x[0])[:120]:
                f.write(f"| `{cls}` | {count} |\n")

    print(f"classes: {len(index)}, unresolved: {unresolved}")
    for sub, items in sorted(by_sub.items(), key=lambda kv: -len(kv[1])):
        print(f"  {sub:9s} {len(items):4d} classes, {sum(c for c,_ in items):6d} methods")
    print(f"-> {OUT_MD}")


if __name__ == "__main__":
    main()