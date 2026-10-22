# -*- coding: utf-8 -*-
"""W-SKL: extrai as COREOGRAFIAS FK completas das skills do APK/Storm.

Por heroi: clip limpo (sem concatenacao de segs) e completo (sem truncagem):
  jutsu  <- {cid}cha10 (skl1)  [skill 1 / Q]
  jutsu2 <- {cid}cha20 (skl2)  [skill 2 / W]
  ult    <- {cid}cha14 (skl1)  [skill 3 / ult cinematografico] (se existir)

Bind pose (Clump/Coords/parents) vem do {cid}bod1.xfbin no data.awb do APK;
os Anm vem direto dos data_spc_{cid}skl{1,2}.xfbin do REPO (xfbin com sci/smaps
proprios). Clips gravados com fps=60 — o game.js usa clip.fps || 24.
Merge cirurgico em public/assets/data/animations.json (substitui jutsu/jutsu2/ult).
"""
import io as _io
import json
import struct
import sys
import zipfile

sys.path.insert(0, '.')
from tools.apk_inspect import APK_PATH, parse_utf, decompress_crilayla
from tools.extract_moba_assets import parse_nucc_chunks
from tools.test_fk_anm_pose import parse_full_anm, evaluate_fk, quat_mul, quat_inv
from tools.extract_all_storm_skills import (
    bake_fk_clip_to_threejs, nucc_vec_to_three, CANONICAL_SUFFIX, DATABOOK_HEIGHTS_CM, CM_TO_WORLD,
)

ANIM_JSON = 'public/assets/data/animations.json'
# Ult por heroi quando {cid}cha14 nao existe: Anm pesado (cinematografico) dos skl do repo
ULT_FALLBACK = {
    '1roc': ('skl2', '1roccha24'),   # 614KB — ult do Rock Lee (Ura Renge)
    '1gar': ('skl2', '1garcha24'),   # 148KB — ult do Gaara (Shukaku)
    '1hnt': ('skl2', '1hntcha21'),   # 177KB — ult da Hinata (64 Palms)
    '1tnd': ('skl2', '1tndcha24'),   # 117KB — ult da Tsunade (Creation Rebirth)
    '1orc': ('skl1', '1orccha11'),   # 403KB c/ Camera — ult do Orochimaru (Yamata)
}
ROSTER = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc']


def load_anm_from_repo(cid, suffix, chunk_name):
    """Decodifica um chunk Anm de um xfbin skl do repo. Retorna (nf, r_trks, p_trks) ou None."""
    path = f'public/assets/data/spc/data_spc_{cid}{suffix}.xfbin'
    try:
        raw = _io.open(path, 'rb').read()
    except FileNotFoundError:
        return None
    chunks, smaps, sci, stypes, snames = parse_nucc_chunks(raw)
    for tname, ch_name, cmap, pay, pbase in chunks:
        if tname == 'nuccChunkAnm' and ch_name == chunk_name:
            nf, lp, r_trks, p_trks = parse_full_anm(pay, pbase, sci, smaps, stypes, snames)
            return nf, lp, r_trks, p_trks
    return None


def main():
    anims = json.load(_io.open(ANIM_JSON, encoding='utf-8'))

    with zipfile.ZipFile(APK_PATH, 'r') as z:
        with z.open('assets/data/sim/data.awb') as f_dat:
            cpk = parse_utf(f_dat.read(65536), 16)[0]
            f_dat.seek(cpk['TocOffset'])
            toc = parse_utf(f_dat.read(cpk['TocSize']), 16)
            toc_map = {r['FileName'].lower(): r for r in toc}

            for cid in ROSTER:
                # ---- bind pose do bod1 (APK) ----
                rb = toc_map.get(f'{cid}bod1.xfbin')
                if not rb:
                    print(f'{cid}: bod1 ausente no APK — SKIP')
                    continue
                f_dat.seek(cpk['TocOffset'] + rb['FileOffset'])
                raw_b = decompress_crilayla(f_dat.read(rb['FileSize']))
                chunks_b, _, _, _, _ = parse_nucc_chunks(raw_b)
                char_pbase = next(
                    (c[4] for c in chunks_b if c[0] == 'nuccChunkClump' and c[1].lower().startswith(cid)),
                    next(c[4] for c in chunks_b if c[0] == 'nuccChunkClump'),
                )
                coords = [(c[1], struct.unpack('>9f', c[3][:36])) for c in chunks_b if c[0] == 'nuccChunkCoord' and c[4] == char_pbase]
                clump_pay = next(c[3] for c in chunks_b if c[0] == 'nuccChunkClump' and c[4] == char_pbase)
                _, nbones, _ = struct.unpack('>IHH', clump_pay[:8])
                parents = struct.unpack(f'>{nbones}h', clump_pay[8:8 + nbones * 2])

                cb_to_coord_idx = {}
                for i, (bname, _) in enumerate(coords):
                    parts = bname.lower().split(' ', 1)
                    suf = parts[1].strip() if len(parts) > 1 else bname.lower()
                    for cb, target_suf in CANONICAL_SUFFIX.items():
                        if suf == target_suf and cb not in cb_to_coord_idx:
                            cb_to_coord_idx[cb] = i
                if len(cb_to_coord_idx) < 19:
                    print(f'{cid}: bind pose incompleta ({len(cb_to_coord_idx)}/20) — SKIP')
                    continue
                bind_pos, bind_rot = evaluate_fk(coords, parents)
                foot_y_cm = min(nucc_vec_to_three(bind_pos[cb_to_coord_idx[16]])[1], nucc_vec_to_three(bind_pos[cb_to_coord_idx[19]])[1]) - 8.15
                head_y_cm = nucc_vec_to_three(bind_pos[cb_to_coord_idx[5]])[1] + 24.5
                raw_h_cm = max(120.0, head_y_cm - foot_y_cm)
                world_scale = round(DATABOOK_HEIGHTS_CM.get(cid, 155.0) * CM_TO_WORLD, 3) / raw_h_cm

                # ---- clips limpos dos skl do REPO ----
                ult_src = ULT_FALLBACK.get(cid, ('skl1', f'{cid}cha14'))
                PLAN = [('jutsu', 'skl1', f'{cid}cha10'), ('jutsu2', 'skl2', f'{cid}cha20'), ('ult', ult_src[0], ult_src[1])]
                hero = anims.setdefault(cid, {})
                for clip_key, suffix, chunk_name in PLAN:
                    r = load_anm_from_repo(cid, suffix, chunk_name)
                    if not r:
                        print(f'{cid}.{clip_key}: {chunk_name} ausente — mantem clip atual')
                        continue
                    nf, lp, r_trks, p_trks = r
                    if nf < 4 or len(r_trks) < 12:
                        print(f'{cid}.{clip_key}: {chunk_name} muito curto ({nf}f) — mantem')
                        continue
                    seg = (nf, r_trks, p_trks)
                    baked = bake_fk_clip_to_threejs(
                        coords, parents, bind_pos, bind_rot, cb_to_coord_idx,
                        [seg], world_scale, foot_y_cm, loop=False, max_frames=max(nf, 120),
                    )
                    if baked['numFrames'] < 4:
                        continue
                    baked['fps'] = 60
                    baked['name'] = f'{chunk_name}_full'
                    baked['source'] = f'data_spc_{cid}{suffix}.xfbin'
                    hero[clip_key] = baked
                    print(f'{cid}.{clip_key} <- {chunk_name}: {baked["numFrames"]} frames @60fps = {baked["numFrames"]/60:.2f}s')

    with _io.open(ANIM_JSON, 'w', encoding='utf-8') as f:
        json.dump(anims, f, separators=(',', ':'), allow_nan=False)
    n = sum(len(v) for v in anims.values())
    print(f'\nmerge OK: {len(anims)} herois, {n} clips -> {ANIM_JSON}')


if __name__ == '__main__':
    main()
