"""Fase 1 do reskin: decodifica os containers de UI Battle do APK que faltavam.

Cobre `battle.xfbin`, `bigbat.xfbin` e `xbattle_startmenu.xfbin` (variantes
ANDROID = layout retrato, o mesmo do HUD MOBA), que nao estavam cobertos por
`tools/extract_all_ui_from_apk.py`.

Le via `tools.cpk_extract.read` (streaming, sem escrever .xfbin em disco) e
salva apenas os PNGs decodificados. Roda em memoria: ~22 MB de entrada.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.cpk_extract import read_by_name  # noqa: E402
from tools.extract_moba_assets import (  # noqa: E402
    decode_ntp3_texture,
    parse_nucc_chunks,
    write_png_rgba,
)

OUT_DIR = os.path.join("public", "assets", "ui", "battle")

TARGETS = {
    "battle": "data/interface/battle/eng/ANDROID/battle.xfbin",
    "bigbat": "data/interface/battle/eng/ANDROID/bigbat.xfbin",
    "startmenu": "data/interface/battle/eng/ANDROID/xbattle_startmenu.xfbin",
}

MAX_DIM = 1024


def extract():
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = {}

    for group, path in TARGETS.items():
        raw = read_by_name(path)
        chunks, _, _, _, _ = parse_nucc_chunks(raw)
        written = []

        for tname, chunk_name, _cmap, payload, _pb in chunks:
            if tname != "nuccChunkTexture":
                continue
            pos = payload.find(b"NTP3")
            if pos == -1:
                continue
            decoded = decode_ntp3_texture(payload, pos + 16, max_dim=MAX_DIM)
            if not decoded:
                continue
            w, h, rgba, _tot = decoded
            safe = chunk_name.replace("/", "_").replace("\\", "_")
            out = os.path.join(OUT_DIR, f"{group}_{safe}.png")
            write_png_rgba(out, w, h, rgba)
            written.append(f"{group}_{safe}.png")
            print(f"  [UI] {group}/{chunk_name} -> {w}x{h} ({safe}.png)")

        manifest[group] = {"source": path, "textures": sorted(written)}
        print(f"[{group}] {len(written)} texturas de {path}\n")

    with open(os.path.join(OUT_DIR, "battle_sources.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    total = sum(len(v["textures"]) for v in manifest.values())
    print(f"Total: {total} PNGs em {OUT_DIR}")


if __name__ == "__main__":
    extract()
