"""W6: lista as 45 faixas de bgm.awb (nome por wave embutido no HCA) com
loop e duracao — e salva bgm_tracks.txt."""
import json
import subprocess

VGM = 'tools/audiobanks/vgmstream-cli.exe'
AWB = 'tools/audiobanks/bgm.awb'
tracks = []
for s in range(1, 46):
    r = subprocess.run([VGM, '-m', '-I', '-s', str(s), AWB], capture_output=True, text=True)
    try:
        m = json.loads(r.stdout)
        li = m.get('loopingInfo') or {}
        tracks.append({
            'i': s,
            'name': m['streamInfo']['name'],
            'dur': round(m['numberOfSamples'] / 48000, 1),
            'loop': bool(li),
            'ls': round((li.get('start') or 0) / 48000, 1),
            'le': round((li.get('end') or 0) / 48000, 1),
            'ch': m['channels'],
        })
    except Exception as e:
        tracks.append({'i': s, 'name': f'ERR:{e}', 'dur': 0, 'loop': False})

with open('tools/audiobanks/bgm_tracks.txt', 'w') as fh:
    for t in tracks:
        line = f"{t['i']:>3}  {t['name']:<24} {t['dur']:>7}s  loop={t['loop']} ({t['ls']}-{t['le']}s) ch={t['ch']}"
        fh.write(line + '\n')
        print(line)
