# -*- coding: utf-8 -*-
"""PV-B.7: bump do cache-buster dos fetch de DADOS (auto-bump nao cobre fetch).
roster_meta.json e animations.json MUDARAM (10->12 herois) mantendo ?v=8, e o
skill_vfx.json sofreu cache do arquivo corrompido (NaN) — browsers serviam versao
velha. Bump v=8 -> v=9 nos tres. Rollback: public/game.js.bak_pvb7
"""
import io, shutil, sys

P = 'public/game.js'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

pairs = [
    ("fetch('assets/data/roster_meta.json?v=8')", "fetch('assets/data/roster_meta.json?v=9')"),
    ("fetch('assets/data/animations.json?v=8')", "fetch('assets/data/animations.json?v=9')"),
    ("fetch('assets/skills/skill_vfx.json?v=8')", "fetch('assets/skills/skill_vfx.json?v=9')"),
]

todo = [(a, b) for a, b in pairs if a in src]
if not todo:
    print('ja aplicado'); sys.exit(0)
n = 0
for a, b in todo:
    c = src.count(a)
    if c != 1:
        print('ABORTADO: ancora "%s" count=%d' % (a, c)); sys.exit(1)
    src = src.replace(a, b); n += 1

shutil.copyfile(P, P + '.bak_pvb7')
io.open(P, 'wb').write(src.replace('\n', eol).encode('utf-8') if eol == '\r\n' else src.encode('utf-8'))
print('PV-B.7: %d cache-busters bumpados v8->v9' % n)
