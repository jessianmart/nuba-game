# -*- coding: utf-8 -*-
"""W5-F2: bump do cache-buster do game.js no index.html (v=40 -> v=41).
Padrao do pvb7_cache_bump_patch.py: backup, assert de unica ocorrencia."""
import io
import shutil

P = 'public/index.html'
raw = io.open(P, 'rb').read()
src = raw.decode('utf-8').replace('\r\n', '\n')
old = 'src="game.js?v=40"'
new = 'src="game.js?v=41"'
c = src.count(old)
if c == 0 and src.count(new):
    print('ja aplicado (v=41 presente)')
elif c != 1:
    raise SystemExit(f'ABORTADO: ancora game.js?v=40 count={c}')
else:
    shutil.copyfile(P, P + '.bak_w5f2')
    eol = '\r\n' if b'\r\n' in raw else '\n'
    io.open(P, 'wb').write(src.replace(old, new).replace('\n', eol).encode('utf-8') if eol == '\r\n' else src.replace(old, new).encode('utf-8'))
    print('W5-F2: game.js?v=40 -> v=41 bumpado')
