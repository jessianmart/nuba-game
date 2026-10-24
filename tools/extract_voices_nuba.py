"""W5-Fase2b: decodifica as vozes de batalha por heroi dos ACBs PL_1XXX.
22 cues essenciais x 12 herois -> public/assets/audio/decoded/voice/<hero>/<cue>.ogg
Cada PL ACB tem 56 subsongs (waveforms); o CueNameTable tem 78 cues
(multiplas cues compartilham waves). Map name->subsong via vgmstream -I.
"""
import json
import re
import subprocess

VGM = 'tools/audiobanks/vgmstream-cli.exe'
OUT = 'public/assets/audio/decoded/voice'

TARGET = [
    'S_PL_DmgS1', 'S_PL_DmgS2', 'S_PL_DmgS3',
    'S_PL_DmgM1', 'S_PL_DmgM2',
    'S_PL_DmgL1', 'S_PL_DmgL2',
    'S_PL_Down',
    'S_PL_AtkS1', 'S_PL_AtkS2', 'S_PL_AtkS3',
    'S_PL_AtkM1', 'S_PL_AtkM2',
    'S_PL_AtkL1', 'S_PL_AtkL2',
    'S_PL_Combo1', 'S_PL_Combo2', 'S_PL_Combo3',
    'S_PL_Awake', 'S_PL_Catch',
    'S_PL_GrdBrk1', 'S_PL_GrdBrk2',
]

HEROES = ['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt',
          '1nej', '1jry', '1tnd', '1orc']

manifest = {}
total_ok = 0
for h in HEROES:
    acb = f'tools/audiobanks/PL_{h}.acb'
    r = subprocess.run([VGM, '-m', '-I', '-s', '1', acb], capture_output=True, text=True)
    m = json.loads(r.stdout)
    total = m['streamInfo']['total']
    name2sub = {}
    for s in range(1, total + 1):
        rr = subprocess.run([VGM, '-m', '-I', '-s', str(s), acb], capture_output=True, text=True)
        mm = json.loads(rr.stdout)
        name2sub[mm['streamInfo']['name']] = s
    manifest[h] = {}
    import os
    os.makedirs(f'{OUT}/{h}', exist_ok=True)
    for cue in TARGET:
        s = name2sub.get(cue)
        if not s:
            print(f'{h}: {cue} SEM SUBSONG')
            continue
        wav = f'{OUT}/{h}/{cue}.wav'
        rv = subprocess.run([VGM, '-s', str(s), '-o', wav, acb], capture_output=True, text=True)
        if rv.returncode != 0:
            print(f'{h}: {cue} FAIL vgmstream')
            continue
        ogg = wav[:-4] + '.ogg'
        rf = subprocess.run(['ffmpeg', '-y', '-i', wav, '-ac', '1', '-qscale:a', '2', ogg],
                             capture_output=True, text=True)
        if rf.returncode != 0:
            print(f'{h}: {cue} FAIL ffmpeg')
            continue
        subprocess.run(['rm', wav], capture_output=True)
        manifest[h][cue] = f'assets/audio/decoded/voice/{h}/{cue}.ogg'
        total_ok += 1
    print(f'{h}: {len(manifest[h])}/{len(TARGET)} oggs', flush=True)

json.dump(manifest, open('tools/audiobanks/voice_manifest.json', 'w'), indent=1)
print(f'VOICE DECODE DONE: {total_ok} oggs de {len(TARGET)*12} esperados')
