"""W6: (a) TOC COMPLETO do sound.awb salvo em tools/audiobanks/sound_files.txt,
(b) extrai bgm.awb (84MB) do adx2.awb e checa o magic (AFS2/CPK)."""
import sys
import zipfile

sys.path.insert(0, 'tools')
sys.path.insert(0, 'C:/Users/jessi/Documents/antigravity/fearless-davinci')
from apk_inspect import APK_PATH  # noqa: E402
from acb_utf import UTF  # noqa: E402

z = zipfile.ZipFile(APK_PATH, 'r')


def toc_of(member):
    f = z.open(member)
    head = f.read(65536)
    f.seek(0)
    tbl = UTF(head, 16)
    toc_row = tbl.rows()[0]
    f.seek(toc_row['TocOffset'] + 16)
    toc = UTF(f.read(toc_row['TocSize'] - 16), 0)
    return f, toc_row['TocOffset'], toc.rows()


# (a) sound.awb completo
f, base, rows = toc_of('assets/data/sim/sound.awb')
with open('tools/audiobanks/sound_files.txt', 'w') as fh:
    for r in rows:
        fn = r.get('FileName') or ''
        fh.write(f"{r.get('FileSize', 0)}\t{fn}\n")
print(f'sound.awb: {len(rows)} entradas salvas em sound_files.txt')
print('--- nomes com bgm/adx/music/strm ---')
for r in rows:
    fn = (r.get('FileName') or '').lower()
    if any(k in fn for k in ('bgm', 'adx', 'music', 'strm', 'title')):
        print(f"  {r.get('FileSize', 0):>12,}  {r.get('FileName')}")

# (b) extrai bgm.awb
f2, base2, rows2 = toc_of('assets/data/disc/adx2.awb')
for r in rows2:
    if r.get('FileName') == 'bgm.awb':
        f2.seek(base2 + r['FileOffset'])
        raw = f2.read(r['FileSize'])
        open('tools/audiobanks/bgm.awb', 'wb').write(raw)
        print(f"\nbgm.awb extraido: {len(raw):,} bytes, magic={raw[:8]!r}")
        break
