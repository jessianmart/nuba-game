"""W5-Fase2: TOC completo do sound.awb + extrai v_battleST/ED/evbattleST/v_etc
e dumpa os CueNameTables — procura o mapa char->cue de batalha."""
import sys
import zipfile

sys.path.insert(0, 'tools')
sys.path.insert(0, 'C:/Users/jessi/Documents/antigravity/fearless-davinci')
from apk_inspect import APK_PATH, decompress_crilayla  # noqa: E402
from acb_utf import UTF  # noqa: E402

z = zipfile.ZipFile(APK_PATH, 'r')


def cpk_toc(f):
    head = f.read(65536)
    f.seek(0)
    tbl = UTF(head, 16)
    row = tbl.rows()[0]
    f.seek(row['TocOffset'] + 16)
    toc = UTF(f.read(row['TocSize'] - 16), 0)
    return row['TocOffset'], toc.rows()


f = z.open('assets/data/sim/sound.awb')
base, rows = cpk_toc(f)
print(f'sound.awb: {len(rows)} entradas (base={base})')
for r in rows:
    fn = r.get('FileName') or ''
    if fn:
        print(f'  {r.get("FileSize", 0):>12,}  {fn}')

# extrai os ACBs de batalha
WANT = ('v_battleST.acb', 'v_battleED.acb', 'v_evbattleST.acb', 'v_etc.acb')
out_dir = 'tools/audiobanks/'
for r in rows:
    fn = r.get('FileName') or ''
    if fn in WANT:
        f.seek(base + r['FileOffset'])
        raw = f.read(r['FileSize'])
        data = raw if raw[:8] != b'CRILayla' else decompress_crilayla(raw)
        open(out_dir + fn, 'wb').write(data)
        print(f'extraido {fn} ({len(data)} bytes)')

# dump cue names de cada ACB extraido
for fn in WANT:
    try:
        raw = open(out_dir + fn, 'rb').read()
    except FileNotFoundError:
        continue
    # ACB pode ter 4-byte size antes do @UTF ou direto
    b = 4 if raw[4:8] == b'@UTF' else 0
    root = UTF(raw, b)
    row = root.rows()[0]
    off, size = row['CueNameTable']
    if not size:
        print(f'{fn}: sem CueNameTable')
        continue
    sub = UTF(raw, off, alloc=size)
    names = [r2['CueName'] for r2 in sub.rows()]
    print(f'{fn}: {len(names)} cues')
    for n in names[:50]:
        print('   ', n)
print('BATTLE VOICE DUMP DONE')
