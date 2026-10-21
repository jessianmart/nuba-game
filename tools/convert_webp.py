"""convert_webp.py — PNG -> WebP adaptativo (PV-B.2 do pivot mobile v2).

Politica por grupo (escada adaptativa): tenta a qualidade base; se o delta visual
(media por canal RGB + delta max de alfa) passar do limite, sobe a qualidade; se ainda
passar, cai para lossless (delta zero, ganho menor). Nada e sobrescrito: os PNGs
permanecem como fonte; os .webp sao gerados ao lado.

    python tools/convert_webp.py            # plano (dry-run) + manifesto
    python tools/convert_webp.py --apply    # escreve os .webp
    python tools/convert_webp.py --apply --only arena

Saida: tools/webp_manifest.json  { png: { webp, quality, mode, bytes_png, bytes_webp, delta } }
O cliente (game.js loadTex) tenta .webp primeiro e cai para .png em caso de erro.
"""

import argparse
import glob
import io
import json
import os
import sys

from PIL import Image, ImageChops, ImageStat

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')
MANIFEST = os.path.join(ROOT, 'tools', 'webp_manifest.json')

# (glob, qualidade base, ladder, delta medio max, delta alfa max, rotulo)
GROUPS = {
    'arena': ('assets/stage/arena/**/*.png', 80, [80, 90, 95], 6.0, 12.0, 'arena/cenario'),
    'skills': ('assets/skills/*.png', 90, [90, 95], 4.0, 10.0, 'VFX skills'),
    'hero': ('assets/textures/*.png', 90, [90, 95], 4.0, 10.0, 'texturas de heroi'),
    'portrait': ('assets/portraits/*.png', 90, [90, 95], 4.0, 10.0, 'retratos'),
    'lobby': ('assets/ui/lobby/*.png', 85, [85, 92], 5.0, 10.0, 'fundo do lobby'),
    'logo': ('assets/logo/*.png', 90, [90, 95], 3.0, 8.0, 'logo'),
}
ORDER = ['arena', 'skills', 'hero', 'portrait', 'lobby', 'logo']


def measure(orig, data):
    """Delta visual: RGB comparado apenas onde alpha > 0 (RGB em pixels totalmente
    transparentes e' invisivel e o WebP lossless zera esse canal -> falso positivo)."""
    dec = Image.open(io.BytesIO(data))
    dec.load()
    o = orig.convert('RGBA')
    d = dec.convert('RGBA')
    if o.mode == 'RGBA':
        mask = o.getchannel('A').point(lambda a: 255 if a > 0 else 0)
        diff = ImageChops.difference(o.convert('RGB'), d.convert('RGB'))
        masked = Image.composite(diff, Image.new('RGB', diff.size, (0, 0, 0)), mask)
        stat = ImageStat.Stat(masked)
        dmean = sum(stat.mean) / 3.0
        a_o = o.getchannel('A')
        a_d = d.getchannel('A')
        dalpha = ImageChops.difference(a_o, a_d).getextrema()[1]
    else:
        stat = ImageStat.Stat(ImageChops.difference(o.convert('RGB'), d.convert('RGB')))
        dmean = sum(stat.mean) / 3.0
        dalpha = 0
    return dmean, dalpha


def encode(img, quality, lossless=False):
    buf = io.BytesIO()
    if lossless:
        img.save(buf, 'WEBP', lossless=True, method=4)
    else:
        img.save(buf, 'WEBP', quality=quality, method=4)
    return buf.getvalue()


def convert_one(path, group):
    base_q, ladder, dlim, alim = GROUPS[group][1:5]
    src = os.path.getsize(path)
    with Image.open(path) as im:
        im.load()
        if im.mode not in ('RGB', 'RGBA'):
            im = im.convert('RGBA')
        best = None
        for q in ladder:
            data = encode(im, q)
            dmean, dalpha = measure(im, data)
            cand = {'data': data, 'quality': q, 'mode': 'lossy', 'delta': round(dmean, 2), 'alpha': dalpha,
                    'bytes': len(data)}
            if dmean <= dlim and dalpha <= alim:
                best = cand
                break
            best = cand  # guarda a ultima tentativa
        if best is None or best['delta'] > dlim or best['alpha'] > alim:
            data = encode(im, 0, lossless=True)
            dmean, dalpha = measure(im, data)
            best = {'data': data, 'quality': 100, 'mode': 'lossless', 'delta': round(dmean, 2),
                    'alpha': dalpha, 'bytes': len(data)}
    if best['bytes'] >= src:
        return None  # nao compensa
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--apply', action='store_true', help='escreve os arquivos .webp')
    ap.add_argument('--only', default=None, help='processa so um grupo')
    ap.add_argument('--manifest', default=MANIFEST)
    args = ap.parse_args()

    manifest = {}
    if os.path.exists(args.manifest):
        try:
            manifest = json.load(open(args.manifest, encoding='utf-8'))
        except Exception:
            manifest = {}

    groups = [args.only] if args.only else ORDER
    tot_png = tot_webp = 0
    rows = []
    for g in groups:
        pattern, base_q, ladder, dlim, alim, label = GROUPS[g]
        files = sorted(glob.glob(os.path.join(PUB, pattern), recursive=True))
        g_png = g_webp = 0
        n_lossless = n_lossy = 0
        worst = 0.0
        for f in files:
            rel = os.path.relpath(f, PUB).replace('\\', '/')
            out = f[:-4] + '.webp'
            res = convert_one(f, g)
            if not res:
                continue
            g_png += os.path.getsize(f)
            g_webp += res['bytes']
            worst = max(worst, res['delta'])
            if res['mode'] == 'lossless':
                n_lossless += 1
            else:
                n_lossy += 1
            manifest[rel] = {
                'webp': rel[:-4] + '.webp',
                'quality': res['quality'],
                'mode': res['mode'],
                'delta': res['delta'],
                'alphaDelta': res['alpha'],
                'bytes_png': os.path.getsize(f),
                'bytes_webp': res['bytes'],
            }
            if args.apply:
                with open(out, 'wb') as fh:
                    fh.write(res['data'])
        tot_png += g_png
        tot_webp += g_webp
        rows.append((label, len(files), g_png / 1048576, g_webp / 1048576, worst, n_lossy, n_lossless))

    print('%-22s %5s %9s %9s %7s %6s %9s' % ('grupo', 'n', 'PNG MB', 'WebP MB', 'delta', 'lossy', 'lossless'))
    for label, n, a, b, dm, nl, nll in rows:
        print('%-22s %5d %9.2f %9.2f %7.2f %6d %9d' % (label, n, a, b, dm, nl, nll))
    print('-' * 74)
    print('%-22s %5s %9.2f %9.2f   (-%.0f%%)' % ('TOTAL', '', tot_png / 1048576, tot_webp / 1048576,
                                                 100 * (1 - tot_webp / max(1, tot_png))))
    with open(args.manifest, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=1, ensure_ascii=False, sort_keys=True)
    print('manifesto:', args.manifest, '(%d entradas)' % len(manifest))
    if args.apply:
        print('arquivos .webp escritos')


if __name__ == '__main__':
    main()
