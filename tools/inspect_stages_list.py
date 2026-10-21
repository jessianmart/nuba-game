import zipfile
import tools.apk_inspect as ai

z = zipfile.ZipFile(ai.APK_PATH)
for awb in ['stage1.awb', 'stage2.awb']:
    with z.open(f'assets/data/sim/{awb}') as f:
        cpk = ai.parse_utf(f.read(65536), 16)[0]
        f.seek(cpk['TocOffset'])
        toc = ai.parse_utf(f.read(cpk['TocSize']), 16)
        print(f'=== {awb} ===')
        for r in toc:
            print(f"  {r['FileName']} ({r['FileSize']} bytes)")
