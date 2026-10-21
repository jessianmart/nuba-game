"""Gera contact sheets de revisao visual a partir de public/assets/ui/slices."""

import json
import os
import sys

from PIL import Image, ImageDraw

SLICE_DIR = os.path.join("public", "assets", "ui", "slices")
SHEET_DIR = os.path.join("public", "assets", "ui", "_sheets")

GROUPS = {
    "rev_deck": ["big", "btg", "actb", "site", "action00", "brndg", "gauge"],
    "rev_fx": ["ougi", "combo", "sousai", "free_fd", "playere", "cmn_button", "spo"],
    "rev_chrome": [
        "sicon", "pad", "namebase", "window", "count", "signal", "win",
        "choicebar", "button_bar", "base", "hwindow", "item01", "mob",
        "uzu", "midashi", "ninka",
    ],
}


def main():
    os.makedirs(SHEET_DIR, exist_ok=True)
    manifest = json.load(open(os.path.join(SLICE_DIR, "manifest.json"), encoding="utf-8"))
    entries = [e for v in manifest.values() for e in v]

    for name, keys in GROUPS.items():
        items = [e for e in entries if any(k in e["atlas"] for k in keys)]
        cols, cell = 10, 104
        rows = (len(items) + cols - 1) // cols
        im = Image.new("RGBA", (cols * cell, rows * (cell + 13)), (20, 22, 30, 255))
        d = ImageDraw.Draw(im)
        for i, e in enumerate(items):
            p = Image.open(os.path.join(SLICE_DIR, e["file"])).convert("RGBA")
            cx, cy = (i % cols) * cell, (i // cols) * (cell + 13)
            p.thumbnail((cell - 8, cell - 8), Image.LANCZOS)
            im.alpha_composite(p, (cx + 4, cy + 4))
            label = f"{e['atlas'].replace('battle_', '').replace('bigbat_', '')[-18:]} {e['w']}x{e['h']}"
            d.text((cx + 3, cy + cell), label, fill=(200, 210, 230, 255))
        out = os.path.join(SHEET_DIR, f"{name}.png")
        im.save(out)
        print(f"{out}: {len(items)} itens")


if __name__ == "__main__":
    sys.exit(main())
