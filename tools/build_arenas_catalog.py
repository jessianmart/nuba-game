"""Build public/assets/data/arenas.json from the Storm StageAreaInfo table.

StageAreaInfo.bin (extracted to public/assets/data/stage_meta) is the game's own
map index: every AREA_* entry is followed by its stage id. That gives us the
authoritative arena -> stage mapping instead of guessing filenames.

Playable radius is curated, not derived: the stage geometry mixes the fight
footprint with distant scenery, and the Konoha field's 88 m value is the one the
E2E suite already validates.
"""

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from tools.cpk_extract import read_by_name  # noqa: E402

OUT = os.path.join(ROOT, "public/assets/data/arenas.json")

# area name -> (display label, playable half-extent in metres)
# Only arenas that map to a stage we actually ship. The rest of the 65 AREA_*
# entries are demos, test maps and minigames.
ARENAS = [
    ("AREA_TRAINING", "Campo de Treinamento (Konoha)", "sd00a", 88),
    ("AREA_COLOSSEUM", "Coliseu (Exame Chūnin)", "sd03b", 78),
    ("AREA_PLAIN", "Planície", "sd05a", 92),
    ("AREA_TOWER", "Torre", "sd01b", 62),
    ("AREA_DEATH", "Vale da Morte", "sd01a", 84),
    ("AREA_FOREST", "Floresta", "sd03a", 80),
    ("AREA_WILD", "Selvagem", "sd04a", 86),
    ("AREA_YAGURA", "Yagura (telhados)", "sd03c", 58),
]

PT = {
    "AREA_TRAINING": "Konoha", "AREA_COLOSSEUM": "Coliseu", "AREA_PLAIN": "Planície",
    "AREA_TOWER": "Torre", "AREA_DEATH": "Vale da Morte", "AREA_FOREST": "Floresta",
    "AREA_WILD": "Selvagem", "AREA_YAGURA": "Yagura",
}


def parse_area_index(raw):
    """AREA_* -> stage id, read straight out of the game data."""
    strings = [s.decode() for s in re.findall(rb"[ -~]{4,}", raw)]
    out = {}
    for i, s in enumerate(strings[:-1]):
        if s.startswith("AREA_") and strings[i + 1].startswith("sd"):
            out.setdefault(s, strings[i + 1])
    return out, strings


def main():
    raw = read_by_name("data/stage/StageAreaInfo.bin.xfbin")
    index, strings = parse_area_index(raw)
    print(f"StageAreaInfo: {len(index)} areas mapped from {len(strings)} strings")
    for a in ARENAS:
        found = index.get(a[0])
        flag = "OK " if found == a[2] else ("?  " if found else "MISS")
        print(f"  {flag} {a[0]:18s} apk={found or '-':8s} shipped={a[2]}")

    catalog = []
    for key, label, stage_id, radius in ARENAS:
        arena_json = os.path.join(ROOT, f"public/assets/stage/arena/{stage_id}.json")
        built = os.path.exists(arena_json)
        entry = {
            "id": stage_id,
            "area": key,
            "label": label,
            "short": PT.get(key, stage_id),
            "radius": radius,
            "built": built,
            "map": f"stage/arena/{stage_id}.json" if built else None,
        }
        if built:
            with open(arena_json, encoding="utf-8") as f:
                d = json.load(f)
            entry["verts"] = d["verts"]
            entry["tris"] = d["tris"]
            entry["meshes"] = len(d["meshes"])
        catalog.append(entry)

    out = {
        "source": "assets/data/sim/stage1.awb -> StageAreaInfo.bin.xfbin",
        "areasInGame": len(index),
        "default": catalog[0]["id"],
        "arenas": catalog,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(f"\n-> {os.path.relpath(OUT, ROOT)} ({len(catalog)} arenas, "
          f"{sum(1 for c in catalog if c['built'])} built)")


if __name__ == "__main__":
    main()