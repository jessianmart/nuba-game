# -*- coding: utf-8 -*-
"""Decodifica 1nrtprm_mot / _skl (motion + skill tables do APK): procura as
anims de reacao de dano e extrai os ints/floats vizinhos — frame counts do
engine de hitstun do Storm. Roda com cwd no repo goofy-mendeleev."""
import os, re, struct, sys

sys.path.insert(0, os.getcwd())
from tools.extract_moba_assets import parse_nucc_chunks  # noqa: E402

data = open(os.path.join('public', 'assets', 'data', 'spc', 'data_spc_1nrtprm.bin.xfbin'), 'rb').read()
chunks, maps, ci, types, names = parse_nucc_chunks(data)

by_name = {c[1]: c[3] for c in chunks if c[0] == 'nuccChunkBinary'}
mot = by_name['1nrtprm_mot']
skl = by_name['1nrtprm_skl']
etc = by_name['1nrtprm_etc']
print('mot:', len(mot), 'bytes | skl:', len(skl), 'bytes | etc:', len(etc), 'bytes')

print('\n== header mot (48 bytes) ==')
print(repr(mot[:48]))
print('== header skl (48 bytes) ==')
print(repr(skl[:48]))
print('== etc (primeiros 128) ==')
print(repr(etc[:128]))

anims = [(m.start(), m.group().decode()) for m in re.finditer(rb'[\x20-\x7e]{4,24}', mot)]
print('\n== strings legiveis no mot (primeiras 45) ==')
for off, s in anims[:45]:
    nxt = mot[off + len(s): off + len(s) + 12]
    print(f'  +{off:5d} {s!r:26s} next12={nxt.hex()}')

print('\nstrings totais no mot:', len(anims))
print('\n== ocorrencias de reacao/dano no mot e skl ==')
for label, blob in (('mot', mot), ('skl', skl)):
    for pat in (b'dmg', b'hsta', b'hav', b'dow', b'rdy', b'RXN', b'stn', b'hurt', b'kime'):
        for m in re.finditer(re.escape(pat), blob):
            o = m.start()
            ctx = blob[max(0, o - 10): o + 26]
            print(f'  [{label}] {pat.decode():5s} @+{o:5d}: {ctx!r}')

# --- decoder estrutural: entradas da mot tem 88 bytes (nome anim + PL_ANM + payload)
print('\n== decoder estrutural: anims de REACAO (entrada de 88 bytes) ==')
REACTION = ('dmg', 'hsta', 'hav', 'dow', 'rxn', 'sdg', 'lan', 'get', 'kime', 'bre')
for m in re.finditer(rb'1nrt(\w{3,7})\x00', mot):
    stem = m.group(1).decode()
    if not any(stem.startswith(p) for p in REACTION):
        continue
    o = m.start()
    bloco = mot[o: o + 88]
    # PL_ANM grupo
    gm = re.search(rb'PL_ANM_([A-Z_0-9]+)', bloco)
    grupo = gm.group(1).decode() if gm else '?'
    # decodifica o payload pos-PL_ANM: ints LE de 2 bytes e floats
    tail = bloco[gm.end() + 1: o + 88] if gm else b''
    ints = []
    for i in range(0, min(len(tail) - 1, 40), 2):
        v = int.from_bytes(tail[i:i+2], 'little')
        if 0 < v < 300: ints.append(v)
    floats = []
    for i in range(0, len(tail) - 3):
        v = struct.unpack('<f', tail[i:i+4])[0]
        if 0.05 < abs(v) < 200: floats.append(round(v, 2))
    # PTRR sub-entries (transitions com frame counts)
    ptrrs = [int.from_bytes(b, 'little') for b in re.findall(rb'PTRR0123456789\x01(....)', bloco)]
    print(f'  {m.group().decode():12s} PL_ANM_{grupo:14s} ints16={ints[:12]} floats~{floats[:8]}')
