"""Contact sheets de selecao: rotula cada slice candidato com seu nome de arquivo.

  python tools/make_pick_sheets.py <filtro-atlas> <saida> [cols] [cell]
"""

import json
import os
import sys

from PIL import Image, ImageDraw

SLICE_DIR = os.path.join("public", "assets", "ui", "slices")
SHEET_DIR = os.path.join("public", "assets", "ui", "_sheets")


def main():
    atlas_key, out_name = sys.argv[1], sys.argv[2]
    cols = int(sys.argv[3]) if len(sys.argv) > 3 else 8
    cell = int(sys.argv[4]) if len(sys.argv) > 4 else 116

    os.makedirs(SHEET_DIR, exist_ok=True)
    manifest = json.load(open(os.path.join(SLICE_DIR, "manifest.json"), encoding="utf-8"))
    entries = [e for v in manifest.values() for e in v]
    items = [e for e in entries if atlas_key in e["atlas"]]

    rows = (len(items) + cols - 1) // cols
    im = Image.new("RGBA", (cols * cell, rows * (cell + 14)), (18, 20, 28, 255))
    d = ImageDraw.Draw(im)
    for i, e in enumerate(items):
        p = Image.open(os.path.join(SLICE_DIR, e["file"])).convert("RGBA")
        cx, cy = (i % cols) * cell, (i // cols) * (cell + 14)
        p.thumbnail((cell - 8, cell - 8), Image.LANCZOS)
        im.alpha_composite(p, (cx + 4, cy + 4))
        label = f"{e['file'].split('/')[-1][:-4]} {e['w']}x{e['h']}"
        d.text((cx + 3, cy + cell), label[:24], fill=(205, 215, 235, 255))

    out = os.path.join(SHEET_DIR, f"{out_name}.png")
    im.save(out)
    print(f"{out}: {len(items)} itens, filtro='{atlas_key}'")


if __name__ == "__main__":
    main()
