"""W6: decodifica as trilhas de musica (modeslct=menu, stage00=batalha) do
bgm.awb -> public/assets/audio/music/*.ogg (stereo q2, 1 passada, loop no browser)."""
import os
import subprocess

VGM = 'tools/audiobanks/vgmstream-cli.exe'
AWB = 'tools/audiobanks/bgm.awb'
OUT = 'public/assets/audio/music'
os.makedirs(OUT, exist_ok=True)

TRACKS = {20: 'menu_modeslct', 27: 'battle_stage00'}
for sub, name in TRACKS.items():
    wav = f'{OUT}/{name}.wav'
    ogg = f'{OUT}/{name}.ogg'
    r = subprocess.run([VGM, '-s', str(sub), '-l', '0', '-o', wav, AWB],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'FAIL vgmstream {name}: {r.stderr[:150]}')
        continue
    r2 = subprocess.run(['ffmpeg', '-y', '-i', wav, '-qscale:a', '2', ogg],
                        capture_output=True, text=True)
    if r2.returncode != 0:
        print(f'FAIL ffmpeg {name}: {r2.stderr[:150]}')
        continue
    os.remove(wav)
    sz = os.path.getsize(ogg)
    print(f'{name}.ogg: {sz:,} bytes')
print('BGM DECODE DONE')
