"""Dumper dos metadados KonohaAct — identifica qual chunk de geometria e a vila do modo aventura.
Roda do repo root (cwd = goofy-mendeleev). So leitura — nada escreve.
"""
import os
import re
import sys

sys.path.insert(0, os.getcwd())
from tools.extract_moba_assets import parse_nucc_chunks  # noqa: E402

META_DIR = os.path.join('public', 'assets', 'data', 'stage_meta')
STR_RE = re.compile(rb'[\x20-\x7e]{4,}')
HINT_RE = re.compile(
    r'(?:^|[^a-z])(?:sa|sm|sp|sd|sk)\d{2}[a-z0-9]*|konoha|act|stage|world|area|map|town|village',
    re.I,
)

for fname in sorted(os.listdir(META_DIR)):
    path = os.path.join(META_DIR, fname)
    with open(path, 'rb') as f:
        data = f.read()
    print('=' * 24, fname, f'{len(data)}b')
    try:
        chunks, maps, chunk_indices, types, names = parse_nucc_chunks(data)
        print('  chunk types:', types)
        if names:
            print('  top names  :', names[:14])
        n = 0
        for (tname, cname, cmap_idx, payload, page_base) in chunks:
            if tname == 'nuccChunkPage':
                continue
            n += 1
            if n > 8:
                print('  ... (mais chunks cortados)')
                break
            print(f'  -- chunk type={tname} name={cname} payload={len(payload)}b')
            strs = [s.decode('ascii', 'replace') for s in STR_RE.findall(payload)]
            hits = [s for s in strs if HINT_RE.search(s)]
            if hits:
                print('     HINTS:', sorted(set(hits))[:20])
            if len(strs) > len(hits):
                rest = [s for s in strs if s not in hits]
                print('     strings:', rest[:16])
    except Exception as e:
        print('  parse error:', repr(e))
        strs = [s.decode('ascii', 'replace') for s in STR_RE.findall(data)]
        hits = [s for s in strs if HINT_RE.search(s)]
        print('  RAW HINTS:', hits[:25])
        print('  RAW strings:', strs[:25])
print('\nDONE')
