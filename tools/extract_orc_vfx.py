# -*- coding: utf-8 -*-
"""W-ORC: extrai os VFX autenticos de Orochimaru (1orceff1) direto do SPC ja
extraido no repo (public/assets/data/spc/) — nao abre o APK.
- decodifica textura NTP3 -> public/assets/skills/1orc_1orceff1_01.png
- decodifica modelos NDP3  -> skill_vfx.json['1orc'] (MERGE cirurgico:
  preserva os demais herois byte a byte; dump com allow_nan=False)
- sanity: reload do JSON, scan NaN, verts > 0

Mapa de consumo (SKILL_VFX_MAP no game.js):
  1orc.q -> '1orceff1_01' (Sen'nejashu — cobras)
Apos rodar, patchear o MAP ('1orc_1orceff1_01' -> '1orceff1_01') — nome de
chunk limpo, sem prefixo de textura.
Idempotente: re-run so re-extrai (deterministico).
"""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.extract_moba_assets import (
    parse_nucc_chunks,
    decode_ndp3_mesh,
    decode_ntp3_texture,
    write_png_rgba,
)

SPC = os.path.join('public', 'assets', 'data', 'spc', 'data_spc_1orceff1.xfbin')
SKILLS_DIR = os.path.join('public', 'assets', 'skills')
VFX_JSON = os.path.join(SKILLS_DIR, 'skill_vfx.json')
CID = '1orc'


def main():
    raw = io.open(SPC, 'rb').read()
    chunks, _, _, _, _ = parse_nucc_chunks(raw)
    print(f'{CID}eff1: {len(raw)} bytes, {len(chunks)} chunks')

    # pass 1: texturas (primeiro — models linkam depois)
    texs = {}
    for tname, ch_name, cmap, pay, pbase in chunks:
        if tname == 'nuccChunkTexture' and b'NTP3' in pay:
            pos = pay.find(b'NTP3')
            w, h, rgba, _ = decode_ntp3_texture(pay, pos + 16, max_dim=256)
            rel = f'skills/{CID}_{ch_name}.png'
            out_p = os.path.join(SKILLS_DIR, f'{CID}_{ch_name}.png')
            write_png_rgba(out_p, w, h, rgba)
            texs[ch_name] = rel
            print(f'  tex {ch_name}: {w}x{h} -> {rel}')

    # pass 2: modelos (shadow fora, como o pipeline canônico)
    models = {}
    meshes = []
    for tname, ch_name, cmap, pay, pbase in chunks:
        if tname == 'nuccChunkModel' and b'NDP3' in pay and 'shadow' not in ch_name.lower():
            subs = decode_ndp3_mesh(pay, ch_name, is_character=False)
            v = sum(len(s['positions']) // 3 for s in subs)
            if v > 0:
                for sm in subs:
                    sm['texture'] = next(iter(texs.values()), None)
                models[ch_name] = subs
                meshes.extend(subs)
                print(f'  model {ch_name}: {v} verts, {len(subs)} submeshes')
    if not models:
        print('ERRO: nenhum modelo decodificado'); sys.exit(1)

    # merge cirurgico
    data = json.load(io.open(VFX_JSON, encoding='utf-8'))
    antes = sorted(data.keys())
    data[CID] = {
        'source': f'{CID}eff1.xfbin',
        'textures': list(texs.values()),
        'meshes': meshes[:6],
        'models': models,
    }
    txt = json.dumps(data, separators=(',', ':'), allow_nan=False)
    assert 'NaN' not in txt and 'Infinity' not in txt, 'NaN/Inf no dump!'
    io.open(VFX_JSON, 'w', encoding='utf-8', newline='').write(txt)

    # sanity: reload
    chk = json.load(io.open(VFX_JSON, encoding='utf-8'))
    depois = sorted(chk.keys())
    verts = {k: sum(len(s['positions']) // 3 for m in v.get('models', {}).values() for s in m)
             for k, v in chk.items() if k == CID}
    novos = set(depois) - set(antes)
    print(f'skill_vfx.json: {len(antes)} -> {len(depois)} chaves | novos: {sorted(novos)}')
    print(f'{CID} verts totais: {verts[CID]}')
    for hid in antes:
        assert hid in chk, f'REGRESSAO: {hid} sumiu!'
    print('MERGE OK — sem regressao de herois, sem NaN')


if __name__ == '__main__':
    main()
