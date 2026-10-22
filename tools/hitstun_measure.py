# -*- coding: utf-8 -*-
"""Mede o HITSTUN REAL do APK do Storm: abre o APK, carrega os xfbin de
anims (bod1c/bod1l/bod1s/bod1r/skl1/skl2) de N herois via o pipeline do repo
(parse_nucc_chunks + parse_full_anm) e reporta numFrames das anims de REACAO
DE DANO (dmg/rxn/hsta/hav/dow/lan/get/kime/sdg). Fps do Storm = 60.
Roda com cwd no repo goofy-mendeleev."""
import struct, sys, zipfile

sys.path.insert(0, '.')
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks
from tools.test_fk_anm_pose import parse_full_anm

HEROES = ['1nrt', '1ssk', '1kks', '1tnd', '1orc', '1gar', '1hnt']
SUFFIXES = ('bod1c', 'bod1l', 'bod1s', 'bod1r', 'skl1', 'skl2')
REACT = ('dmg', 'rxn', 'hsta', 'hav', 'dow', 'lan', 'get', 'kime', 'sdg', 'bre')

FPS = 60.0

with zipfile.ZipFile(APK_PATH, 'r') as z:
    with z.open('assets/data/sim/data.awb') as f_dat:
        cpk = parse_utf(f_dat.read(65536), 16)[0]
        f_dat.seek(cpk['TocOffset'])
        toc = parse_utf(f_dat.read(cpk['TocSize']), 16)
        toc_map = {r['FileName'].lower(): r for r in toc}
        print(f'toc: {len(toc_map)} arquivos | alvo: {len(HEROES)} herois')

        for cid in HEROES:
            anm = {}
            for suffix in SUFFIXES:
                fn = f'{cid}{suffix}.xfbin'
                if fn not in toc_map:
                    continue
                r = toc_map[fn]
                f_dat.seek(cpk['TocOffset'] + r['FileOffset'])
                raw = decompress_crilayla(f_dat.read(r['FileSize']))
                chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
                for tname, ch_name, cmap, pay, pbase in chunks:
                    if tname != 'nuccChunkAnm':
                        continue
                    try:
                        nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci, smaps, stypes, snames)
                    except Exception:
                        continue
                    if len(r_trks) >= 12 or 'spk0' in ch_name.lower():
                        anm[ch_name.lower()] = nf
            react = {k: v for k, v in sorted(anm.items()) if any(k.replace(cid, '', 1).startswith(p) for p in REACT)}
            if react:
                print(f'\n== {cid} — anims de reacao (frames @60fps) ==')
                for k, nf in react.items():
                    stem = k.replace(cid, '', 1)
                    if nf and nf < 300:
                        print(f'  {k:16s} {nf:4d}f = {nf / FPS:.3f}s')
                    else:
                        print(f'  {k:16s} {nf}f (?)')
            else:
                print(f'\n== {cid}: sem anims de reacao no banco ({len(anm)} anims totais)')
