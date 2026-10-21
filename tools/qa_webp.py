"""qa_webp.py — QA de fidelidade WebP vs PNG (PV-B.2 do pivot mobile v2).

Para cada textura candidata:
  * converte PNG -> WebP na qualidade pedida
  * mede o delta visual (max/mean por canal) e o tamanho

Regra de aceitacao por grupo:
  * arena/cenario : q80 (difusas com alpha)  -> delta medio <= 6/255
  * UI / skin     : q90 (bordas duras)       -> delta medio <= 3/255
  * VFX / skills  : q90                     -> delta medio <= 4/255
  * herois/retratos: q90                   -> delta medio <= 4/255

Nao escreve nada: apenas mede e imprime o plano de conversao.
"""

import os
import sys
from PIL import Image, ImageChops, ImageStat

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PUB = os.path.join(ROOT, 'public')

GROUPS = [
    # (glob relativo a public/, qualidade, delta medio maximo, rotulo)
    ('assets/stage/arena/**/*.png', 80, 6.0, 'arena/cenario'),
    ('assets/stage/*.png', 80, 6.0, 'arena/cenario (raiz)'),
    ('assets/ui/skin/*.png', 90, 3.0, 'skin/HUD'),
    ('assets/ui/battle/*.png', 90, 3.0, 'UI battle'),
    ('assets/ui/*.png', 90, 3.0, 'UI raiz'),
    ('assets/skills/*.png', 90, 4.0, 'VFX skills'),
    ('assets/textures/*.png', 90, 4.0, 'texturas de heroi'),
    ('assets/portraits/*.png', 90, 4.0, 'retratos'),
    ('assets/ui/lobby/*.png', 85, 5.0, 'fundo do lobby'),
    ('assets/logo/*.png', 90, 3.0, 'logo'),
]


def delta(a, b):
    d = ImageChops.difference(a.convert('RGB'), b.convert('RGB'))
    stat = ImageStat.Stat(d)
    mean = sum(stat.mean) / 3.0
    worst = max(d.convert('L').getextrema())
    return mean, worst


def main():
    import glob
    total_png = total_webp = 0
    rows = []
    rejected = []
    for pattern, q, limit, label in GROUPS:
        files = glob.glob(os.path.join(PUB, pattern), recursive=True)
        g_png = g_webp = 0
        worst_mean = 0.0
        worst_file = ''
        for f in files:
            try:
                im = Image.open(f)
                im.load()
                if im.mode not in ('RGB', 'RGBA'):
                    im = im.convert('RGBA')
                import io
                buf = io.BytesIO()
                im.save(buf, 'WEBP', quality=q, method=4)
                w = buf.tell()
                dec = Image.open(io.BytesIO(buf.getvalue()))
                dec.load()
                m, wst = delta(im, dec)
                g_png += os.path.getsize(f)
                g_webp += w
                if m > worst_mean:
                    worst_mean = m
                    worst_file = os.path.relpath(f, PUB)
                if m > limit:
                    rejected.append((os.path.relpath(f, PUB), round(m, 2), limit))
            except Exception as e:
                rejected.append((os.path.relpath(f, PUB), 'erro: %s' % e, limit))
        total_png += g_png
        total_webp += g_webp
        rows.append((label, len(files), g_png / 1048576, g_webp / 1048576, worst_mean, worst_file))

    print('%-24s %5s %10s %10s %8s  %s' % ('grupo', 'n', 'PNG MB', 'WebP MB', 'delta', 'pior arquivo'))
    for label, n, a, b, dm, wf in rows:
        print('%-24s %5d %10.2f %10.2f %8.2f  %s' % (label, n, a, b, dm, wf))
    print('-' * 78)
    print('%-24s %5s %10.2f %10.2f  (%.0f%% de reducao)' % ('TOTAL', '', total_png / 1048576,
          total_webp / 1048576, 100 * (1 - total_webp / max(1, total_png))))
    if rejected:
        print('\nREJEITADOS (delta acima do limite) — %d:' % len(rejected))
        for r in rejected[:25]:
            print('   ', r)


if __name__ == '__main__':
    main()
