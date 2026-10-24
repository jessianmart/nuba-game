# -*- coding: utf-8 -*-
"""W-REAL F3: extrai os CORPOS 3D de verdade das skills do repo (NDP3 >= 40v,
textura NTP3 do mesmo xfbin) e faz merge cirurgico no skill_vfx.json.

Fontes (corpos nunca extraidos) -> grupo alvo no JSON:
  1ssveff1 (chamas com corpo), 1szneff1 (chakra 330v)  -> 1ssk
  1skneff1 (punho gigante 368v, perna 769v)            -> 1skr
  1kmmeff1 (bolt do raikiri/kirin 170v)                -> 1kks
  1nrveff1 (sonic01_air 145-304v, ring01, chakra02/03) -> 1nrt
  1gareff1 (corpos de areia snd01-15, mao hnd01_body)  -> 1gar (ja parcial; idempotente)
"""
import io, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.extract_moba_assets import parse_nucc_chunks, decode_ndp3_mesh, decode_ntp3_texture, write_png_rgba

VFX_JSON = 'public/assets/skills/skill_vfx.json'
SKILLS_DIR = 'public/assets/skills'
SPC = 'public/assets/data/spc'

SOURCES = {
    '1ssk': ['1ssveff1', '1szneff1'],
    '1skr': ['1skneff1'],
    '1kks': ['1kmmeff1'],
    '1nrt': ['1nrveff1'],
    '1jry': ['1jryeff1'],
    '1gar': ['1gareff1'],
}
MIN_V = 40
# xfbin sem chunk de textura (referencia externa) -> fallback do common
TEX_FALLBACK = {
    '1skneff_fist01': 'skills/1efc_chakra05.png',
    '1skneff_leg01': 'skills/1efc_chakra05.png',
}


def pick_tex(model_name, texs):
    """Textura com maior overlap de nome com o model (ex.: fire03 -> fire03.png)."""
    if not texs:
        return None
    stem = re.sub(r'[^a-z0-9]', '', model_name.lower())
    best, score = None, -1
    for tname in texs:
        tstem = re.sub(r'[^a-z0-9]', '', tname.lower())
        # maior substring comum simples por comprimento de intersecao de sufixo
        s = 0
        for L in range(min(len(stem), len(tstem)), 2, -1):
            if stem[-L:] == tstem[-L:]:
                s = L
                break
        if s > score:
            best, score = tname, s
    return texs[best]


def main():
    data = json.load(io.open(VFX_JSON, encoding='utf-8'))
    added = 0
    for target, xfbs in SOURCES.items():
        for xfb in xfbs:
            path = f'{SPC}/data_spc_{xfb}.xfbin'
            raw = io.open(path, 'rb').read()
            chunks, _, _, _, _ = parse_nucc_chunks(raw)
            # texturas
            texs = {}
            for tname, ch_name, cmap, pay, pbase in chunks:
                if tname == 'nuccChunkTexture' and b'NTP3' in pay:
                    pos = pay.find(b'NTP3')
                    w, h, rgba, _ = decode_ntp3_texture(pay, pos + 16, max_dim=256)
                    rel = f'skills/{xfb}_{ch_name}.png'
                    out_p = os.path.join(SKILLS_DIR, f'{xfb}_{ch_name}.png')
                    if not os.path.exists(out_p):
                        write_png_rgba(out_p, w, h, rgba)
                    texs[ch_name] = rel
            # modelos (shadow fora)
            for tname, ch_name, cmap, pay, pbase in chunks:
                if tname != 'nuccChunkModel' or b'NDP3' not in pay:
                    continue
                if 'shadow' in (ch_name or '').lower():

                    continue
                try:
                    subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
                except Exception as _e:

                    continue
                v = sum(len(s['positions']) // 3 for s in subs)
                if v < MIN_V or not subs:

                    continue

                tex = pick_tex(ch_name, texs)
                if not tex:
                    tex = TEX_FALLBACK.get(ch_name)
                if not tex:

                    continue
                for sm in subs:
                    sm['texture'] = tex
                grp = data.setdefault(target, {'source': xfb, 'textures': [], 'models': {}})
                grp.setdefault('models', {})
                if ch_name in grp['models']:

                    continue  # idempotente
                grp['models'][ch_name] = subs
                if tex not in grp.get('textures', []):
                    grp.setdefault('textures', []).append(tex)
                print(f'  {target} <- {xfb}/{ch_name}: {v}v tex={tex.split("/")[-1]}')
                added += 1
    txt = json.dumps(data, separators=(',', ':'), allow_nan=False)
    assert 'NaN' not in txt and 'Infinity' not in txt
    io.open(VFX_JSON, 'w', encoding='utf-8', newline='\n').write(txt)
    chk = json.load(io.open(VFX_JSON, encoding='utf-8'))
    print(f'\nmerge OK: +{added} corpos, grupos: {sorted(chk.keys())}')


if __name__ == '__main__':
    main()
