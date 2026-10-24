"""W5-Fase2: extrai os ACBs PL_1XXX dos 12 herois do NUBA do sound.awb e
salva como tools/audiobanks/PL_1XXX.acb (blob @UTF -> 8+tsize)."""
import sys
import zipfile

sys.path.insert(0, 'tools')
sys.path.insert(0, 'C:/Users/jessi/Documents/antigravity/fearless-davinci')
from apk_inspect import APK_PATH, decompress_crilayla  # noqa: E402
from acb_utf import UTF  # noqa: E402

HEROES = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt',
          '1nej', '1jry', '1tnd', '1orc']

z = zipfile.ZipFile(APK_PATH, 'r')
f = z.open('assets/data/sim/sound.awb')
head = f.read(65536)
f.seek(0)
tbl = UTF(head, 16)
toc_row = tbl.rows()[0]
f.seek(toc_row['TocOffset'] + 16)
toc = UTF(f.read(toc_row['TocSize'] - 16), 0)
base = toc_row['TocOffset']
rows = toc.rows()

by_name = {r.get('FileName'): r for r in rows if r.get('FileName')}
ok = 0
for h in HEROES:
    fn = f'PL_{h}.xfbin'
    r = by_name.get(fn)
    if not r:
        print(f'{fn}: NAO ESTA NO TOC!')
        continue
    f.seek(base + r['FileOffset'])
    raw = f.read(r['FileSize'])
    data = raw if raw[:8] != b'CRILayla' else decompress_crilayla(raw)
    i = data.find(b'@UTF')
    root = UTF(data, i)
    acb = data[i:i + 8 + root.tsize]
    out = f'tools/audiobanks/PL_{h}.acb'
    open(out, 'wb').write(acb)
    names_tbl_off, names_tbl_size = root.rows()[0]['CueNameTable']
    sub = UTF(data, names_tbl_off, alloc=names_tbl_size)
    n = len(sub.rows())
    print(f'{out}: {len(acb):,} bytes, {n} cues')
    ok += 1
print(f'EXTRACT DONE: {ok}/12')
