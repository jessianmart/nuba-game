# -*- coding: utf-8 -*-
"""W-REAL F1: forense dos CORPOS NDP3 (>=80 verts) em todos os xfbin do repo
+ localizacao dos .awb no disco (installTimeDisc com os spl_*)."""
import io, os, sys, glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.extract_moba_assets import parse_nucc_chunks, decode_ndp3_mesh

print('=== CORPOS NDP3 (>=80 verts) em TODOS os xfbin spc do repo ===')
for path in sorted(glob.glob('public/assets/data/spc/*.xfbin')):
    try:
        raw = io.open(path, 'rb').read()
        chunks, _, _, _, _ = parse_nucc_chunks(raw)
    except Exception:
        continue
    for t, cn, cm, pay, pb in chunks:
        if t == 'nuccChunkModel' and b'NDP3' in pay:
            try:
                subs = decode_ndp3_mesh(pay, cn or '?', is_character=False)
                v = sum(len(s['positions']) // 3 for s in subs)
                if v >= 80:
                    print(f'  {os.path.basename(path)}/{cn}: {v}v')
            except Exception:
                pass

print()
print('=== .awb no disco (repo + Downloads) ===')
seen = set()
for base in ('tools', 'public/assets', r'C:\Users\jessi\Downloads'):
    for root, dirs, files in os.walk(base):
        for f in files:
            if f.lower().endswith('.awb') or 'install' in f.lower() and f.lower().endswith(('.awb', '.bin')):
                fp = os.path.normpath(os.path.join(root, f))
                if fp not in seen:
                    seen.add(fp)
                    print(f'  {fp} ({os.path.getsize(fp) // 1048576}MB)')
