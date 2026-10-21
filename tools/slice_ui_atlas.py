"""Fase 2 do reskin: recorta os atlas de UI do Storm em elementos soltos.

Cada textura NTP3 decodificada e um atlas com varios elementos colados
(molduras de barra, orbes, asas, botoes). Este script segmenta por alpha,
corta cada componente e grava um manifest.json com bbox e tamanho nativo --
fonte de verdade para o CSS do reskin.

  python tools/slice_ui_atlas.py                 # recorta tudo
  python tools/slice_ui_atlas.py --contact-sheet  # gera contact sheet p/ revisao
"""

import argparse
import json
import os

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

UI_DIR = os.path.join("public", "assets", "ui")
BATTLE_DIR = os.path.join(UI_DIR, "battle")
OUT_DIR = os.path.join(UI_DIR, "slices")
SHEET_DIR = os.path.join(UI_DIR, "_sheets")

ALPHA_MIN = 8          # alpha minimo para considerar pixel opaco
MIN_AREA = 400         # px^2 -- descarta ruido
PAD = 2                # folga em torno do bbox


def segment(img):
    """Componentes conexas do canal alpha -> lista de (x0, y0, x1, y1)."""
    a = np.asarray(img.convert("RGBA"))[:, :, 3]
    mask = a > ALPHA_MIN
    if not mask.any():
        return []
    labels, n = ndimage.label(mask)
    if n == 0:
        return []
    boxes = ndimage.find_objects(labels)
    out = []
    for sl in boxes:
        if sl is None:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        # find_objects devolve um slice por label (1..n); o canto do bbox
        # pertence ao proprio componente.
        sub = labels[y0:y1, x0:x1]
        lab = sub[0, 0]
        area = int((sub == lab).sum())
        if area < MIN_AREA:
            continue
        out.append((x0, y0, x1, y1, area))
    out.sort(key=lambda b: (b[1], b[0]))
    return out


def crop_box(img, box):
    x0, y0, x1, y1, _ = box
    x0 = max(0, x0 - PAD)
    y0 = max(0, y0 - PAD)
    x1 = min(img.width, x1 + PAD)
    y1 = min(img.height, y1 + PAD)
    return img.crop((x0, y0, x1, y1))


def slice_atlas(path, root_name, manifest, sheet_acc):
    img = Image.open(path).convert("RGBA")
    boxes = segment(img)
    name = os.path.splitext(os.path.basename(path))[0]
    out_dir = os.path.join(OUT_DIR, root_name)
    os.makedirs(out_dir, exist_ok=True)

    entries = []
    for i, box in enumerate(boxes):
        piece = crop_box(img, box)
        fname = f"{name}_{i:02d}.png"
        piece.save(os.path.join(out_dir, fname))
        entries.append({
            "file": f"{root_name}/{fname}",
            "atlas": name,
            "box": [box[0], box[1], box[2], box[3]],
            "w": piece.width,
            "h": piece.height,
            "area": box[4],
        })
        sheet_acc.append((piece, f"{name}_{i:02d} {piece.width}x{piece.height}"))

    manifest.setdefault(root_name, []).extend(entries)
    return len(entries)


def contact_sheet(items, path, cols=8, cell=120):
    if not items:
        return
    rows = (len(items) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * (cell + 14)), (24, 26, 34, 255))
    d = ImageDraw.Draw(sheet)
    for i, (piece, label) in enumerate(items):
        cx = (i % cols) * cell
        cy = (i // cols) * (cell + 14)
        p = piece.copy()
        p.thumbnail((cell - 8, cell - 8), Image.LANCZOS)
        sheet.alpha_composite(p, (cx + 4, cy + 4))
        d.text((cx + 4, cy + cell), label[:26], fill=(210, 215, 230, 255))
    sheet.save(path)
    print(f"  sheet -> {path} ({len(items)} itens)")


def collect_inputs():
    inputs = []
    for fname in sorted(os.listdir(BATTLE_DIR)):
        if fname.lower().endswith(".png"):
            inputs.append((os.path.join(BATTLE_DIR, fname), "battle"))
    for fname in sorted(os.listdir(UI_DIR)):
        if fname.lower().endswith(".png"):
            inputs.append((os.path.join(UI_DIR, fname), "core"))
    return inputs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--only", default=None, help="filtra por substring do nome")
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)
    os.makedirs(SHEET_DIR, exist_ok=True)

    manifest = {}
    sheets = {}
    total = 0
    for path, group in collect_inputs():
        if args.only and args.only not in path:
            continue
        n = slice_atlas(path, group, manifest, sheets.setdefault(group, []))
        total += n
        print(f"{os.path.basename(path):38s} -> {n} elementos")

    with open(os.path.join(OUT_DIR, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=1)

    if args.contact_sheet:
        for group, items in sheets.items():
            contact_sheet(items, os.path.join(SHEET_DIR, f"{group}.png"))

    print(f"\n{total} elementos em {OUT_DIR}")


if __name__ == "__main__":
    main()
