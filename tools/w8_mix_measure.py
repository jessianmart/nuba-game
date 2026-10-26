"""W8: medição de loudness (RMS dB) dos 3 canais de áudio do NUBA."""
import glob
import random
import re
import subprocess

random.seed(42)


def rms_db(path):
    try:
        r = subprocess.run(
            ['ffmpeg', '-hide_banner', '-i', path,
             '-af', 'astats=measure_overall=RMS_level:measure_perchannel=none',
             '-f', 'null', '-'],
            capture_output=True, text=True, timeout=20)
        m = re.search(r'RMS level dB:\s*(-?[\d.]+|-inf)', r.stderr)
        if not m:
            return None
        v = m.group(1)
        return float(v) if v != '-inf' else -120.0
    except Exception:
        return None

groups = {
    'musica': sorted(glob.glob('public/assets/audio/music/*.ogg')),
    'skills': random.sample(sorted(glob.glob('public/assets/audio/decoded/*.ogg')), 5),
    'voz': random.sample(sorted(glob.glob('public/assets/audio/decoded/voice/*/*.ogg')), 5),
}
for g, files in groups.items():
    vals = [v for v in (rms_db(f) for f in files) if v is not None and v > -110]
    if vals:
        print(f'{g:8s}: n={len(vals):2d}  media RMS={sum(vals)/len(vals):+.2f} dB  '
              f'min={min(vals):+.1f}  max={max(vals):+.1f}')
    else:
        print(f'{g:8s}: sem leituras ({len(files)} arquivos)')
