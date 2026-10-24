# -*- coding: utf-8 -*-
"""W-VFX-SEQ F1: extrai os LIFETIMES reais dos Anms de VFX (frames, loop) de
cada eff1 e mergeia no skill_vfx.json como vfx_anims. A duracao autentica de
cada efeito (31f = 0.52s de vida etc)."""
import io, json, os, struct, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.extract_moba_assets import parse_nucc_chunks

VFX_JSON = 'public/assets/skills/skill_vfx.json'
SPC = 'public/assets/data/spc'
ROSTER = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']


def main():
    data = json.load(io.open(VFX_JSON, encoding='utf-8'))
    total = 0
    EFF1 = {
        '1nrt': ['1nrteff1', '1nrveff1'],
        '1ssk': ['1sskeff1', '1ssveff1', '1szneff1'],
        '1skr': ['1skreff1', '1skneff1'],
        '1kks': ['1kkseff1', '1kmmeff1'],
        '1roc': ['1roceff1'],
        '1itc': ['1itceff1'],
        '1gar': ['1gareff1'],
        '1hnt': ['1hnteff1'],
        '1nej': ['1nejeff1'],
        '1jry': ['1jryeff1'],
        '1tnd': ['1tndeff1'],
        '1orc': ['1orceff1'],
    }
    for hid in ROSTER:
        anms = {}
        for xfb in EFF1[hid]:
            path = f'{SPC}/data_spc_{xfb}.xfbin'
            if not os.path.exists(path):
                continue
            raw = io.open(path, 'rb').read()
            chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
            for tname, cn, cm, pay, pb in chunks:
                if tname != 'nuccChunkAnm' or not cn:
                    continue
                if len(pay) < 20:
                    continue
                dur, fs, unk1, loop, n_e, n_oe, n_c = struct.unpack('>IIHHHHI', pay[:20])
                nf = max(1, dur // max(1, fs) + 1)
                anms[cn] = {'frames': nf, 'loop': bool(loop), 'fps': 60}
        if anms:
            grp = data.setdefault(hid, {})
            grp['vfx_anims'] = anms
            total += len(anms)
            print(f'  {hid}: {len(anms)} lifetimes')
    txt = json.dumps(data, separators=(',', ':'), allow_nan=False)
    assert 'NaN' not in txt
    io.open(VFX_JSON, 'w', encoding='utf-8', newline='\n').write(txt)
    print(f'merge OK: {total} lifetimes')


if __name__ == '__main__':
    main()
