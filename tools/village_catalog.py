"""Cataloga os chunks candidatos a vila Konoha (modo aventura) — nomes de submesh/triagem.
Run: python tools/village_catalog.py   (cwd = repo root)
"""
import os
import sys
from collections import Counter

sys.path.insert(0, os.getcwd())
from tools.extract_moba_assets import parse_nucc_chunks  # noqa: E402

RAW = 'public/assets/stage/raw'
CANDIDATES = ['sm00a', 'sp00', 'sa00z', 'sk00a']

for sid in CANDIDATES:
    path = os.path.join(RAW, sid + '.xfbin')
    with open(path, 'rb') as f:
        raw = f.read()
    try:
        chunks, maps, ci, types, names = parse_nucc_chunks(raw)
    except Exception as e:
        print('=' * 20, sid, f'{len(raw)/1e6:.0f}MB  PARSE ERR: {e!r}')
        continue
    real = [(t, n, p) for (t, n, c, p, pb) in chunks
            if t not in ('nuccChunkPage', 'nuccChunkNull') and n]
    print('=' * 20, sid, f'{len(raw)/1e6:.0f}MB  chunks={len(chunks)}  com-nome={len(real)}')
    # prefixo do nome (2 segmentos) para triagem de familia
    fams = Counter()
    for t, n, p in real:
        parts = n.replace('-', '_').split('_')
        fams[' '.join(parts[:2])[:34]] += 1
    print('  familias top:', fams.most_common(12))
    for t, n, p in real[:24]:
        print(f'  {t.replace("nuccChunk", ""):16} {n[:52]:52} {len(p)/1024:8.0f}KB')
    tex = sum(1 for t, n, p in real if t == 'nuccChunkTexture')
    mdl = sum(1 for t, n, p in real if 'Model' in t or 'NDP3' in t)
    print(f'  [resumo] models={mdl} textures={tex}')
print('\nCATALOG DONE')
