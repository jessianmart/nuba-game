# -*- coding: utf-8 -*-
"""W-VIS-FULL shot analyzer: por screenshot, mede pixels 'de skill' —
brilho aditivo alto (>240), ciano/azul/roxo/vermelho/laranja saturados
(cores que o cenário sd03b nao tem em massa) — e imprime ranking."""
import os
import sys
from PIL import Image

SHOTS = os.path.join(os.environ.get('LOCALAPPDATA', os.path.expanduser('~')), 'hermes', 'cache', 'scratch')


def analyze(name):
    im = Image.open(os.path.join(SHOTS, name)).convert('RGB')
    W, H = im.size
    px = im.load()
    bright = cyan = blue = purple = red = orange = green = 0
    for y in range(0, H, 2):
        for x in range(0, W, 2):
            r, g, b = px[x, y]
            if r > 240 and g > 240 and b > 240:
                bright += 1
            if b > 170 and b > r + 60 and g > 130:
                cyan += 1
            elif b > 150 and b > r + 70:
                blue += 1
            elif r > 120 and b > 130 and g < r * 0.75:
                purple += 1
            elif r > 180 and r > b + 90 and g < 140:
                red += 1
            elif r > 190 and g > 120 and b < 100:
                orange += 1
            elif g > 140 and g > r + 40 and g > b + 40:
                green += 1
    fx = bright + cyan + blue + purple + red + orange
    return {'bright': bright, 'cyan': cyan, 'blue': blue, 'purple': purple, 'red': red, 'orange': orange, 'green': green, 'fx': fx}


if __name__ == '__main__':
    shots = sorted(f for f in os.listdir(SHOTS) if f.startswith('full_') and f.endswith('.png'))
    print(f'{len(shots)} shots')
    rows = []
    for f in shots:
        a = analyze(f)
        rows.append((a['fx'], f, a))
    rows.sort(reverse=True)
    for fx, f, a in rows:
        print(f"{f:28s} fx={fx:6d} (bright={a['bright']}, cyan={a['cyan']}, blue={a['blue']}, purple={a['purple']}, red={a['red']}, orange={a['orange']})")
