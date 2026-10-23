"""W5-SFX: decodifica as cues de batalha que faltam dos bancos CRI locais.

Fonte: public/assets/audio/data_sound_Se_*.xfbin -> [blob @UTF ACB] ->
vgmstream-cli (-s N por subsong, nomes das cues via CueName) -> wav ->
ffmpeg -> ogg mono q2 em public/assets/audio/decoded/.

Convencao de nome do jogo: strip 'S_', camelCase -> snake_case
(S_maxGauge -> max_gauge.ogg). Rodar: python tools/extract_battle_sfx.py
"""
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BANKS = os.path.join(ROOT, 'tools', 'audiobanks')
OUT = os.path.join(ROOT, 'public', 'assets', 'audio', 'decoded')
VGM = os.path.join(BANKS, 'vgmstream-cli.exe')

# (banco, S_cue) -> nome do arquivo ogg alvo
WANTED = [
    ('Se_common', 'S_kunai_hit', 'kunai_hit'),
    ('Se_common', 'S_kunai_hit2', 'kunai_hit2'),
    ('Se_common', 'S_kunai_hitWall', 'kunai_hit_wall'),
    ('Se_common', 'S_kunai_miss', 'kunai_miss'),
    ('Se_common', 'S_shuriken', 'shuriken'),
    ('Se_common', 'S_kick_swing', 'kick_swing'),
    ('Se_common', 'S_kick_hit2', 'kick_hit2'),
    ('Se_common', 'S_punch_hit2', 'punch_hit2'),
    ('Se_common', 'S_groundHit', 'ground_hit'),
    ('Se_common', 'S_waterHit', 'water_hit'),
    ('Se_common', 'S_bodyAtk', 'body_atk'),
    ('Se_common', 'S_sousai', 'sousai'),
    ('Se_common', 'S_standUp1', 'stand_up1'),
    ('Se_common', 'S_standUp2', 'stand_up2'),
    ('Se_common', 'S_awake_off', 'awake_off'),
    ('Se_common', 'S_box_open', 'box_open'),
    ('Se_common', 'S_chakura_get', 'chakura_get'),
    ('Se_common', 'S_item_get', 'item_get'),
    ('Se_common', 'S_jump1', 'jump1'),
    ('Se_common', 'S_jump2', 'jump2'),
    ('Se_battle', 'S_groundHit2', 'ground_hit2'),
    ('Se_battle', 'S_chakHit', 'chak_hit'),
]


def load_cues(bank):
    """battle_cues.txt/common_cues.txt: linhas 'N \"name\":\"S_xxx\"'."""
    idx = {}
    fn = bank.replace('Se_', '') + '_cues.txt'
    path = os.path.join(BANKS, fn)
    for line in open(path, encoding='utf-8'):
        m = re.search(r'^(\d+)\s+"name":"([^"]+)"', line)
        if m:
            idx[m.group(2)] = int(m.group(1))
    return idx


def main():
    os.makedirs(OUT, exist_ok=True)
    ok, skip, fail = [], [], []
    for bank, cue, ogg_name in WANTED:
        target = os.path.join(OUT, ogg_name + '.ogg')
        if os.path.exists(target) and os.path.getsize(target) > 2000:
            skip.append(ogg_name)
            continue
        cues = load_cues(bank)
        sub = cues.get(cue)
        if not sub:
            fail.append(f'{cue} NAO ESTA EM {bank}')
            continue
        wav = os.path.join(BANKS, ogg_name + '.wav')
        r1 = subprocess.run([VGM, '-s', str(sub), '-o', wav, os.path.join(BANKS, bank + '.acb')],
                            capture_output=True, text=True)
        if not os.path.exists(wav) or os.path.getsize(wav) < 4000:
            fail.append(f'{cue}: vgmstream falhou ({r1.stdout[-80:]}{r1.stderr[-80:]})')
            continue
        r2 = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', wav,
                             '-ac', '1', '-qscale:a', '2', target],
                            capture_output=True, text=True)
        if os.path.exists(wav):
            os.remove(wav)
        if os.path.exists(target) and os.path.getsize(target) > 2000:
            ok.append(ogg_name)
        else:
            fail.append(f'{cue}: ffmpeg falhou ({r2.stderr[-80:]})')
    print(f'OK ({len(ok)}): {" ".join(ok)}')
    if skip:
        print(f'JA EXISTIAM ({len(skip)}): {" ".join(skip)}')
    if fail:
        print(f'FALHAS ({len(fail)}):')
        for f in fail:
            print('  -', f)
        sys.exit(1)
    print(f'TOTAL decoded/: {len(os.listdir(OUT))} oggs')


if __name__ == '__main__':
    main()
