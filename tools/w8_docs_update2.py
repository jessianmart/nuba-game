"""W8 docs v2 — append com ancoras reais (nenhum marker existia)."""
import os

G = '../goofy-mendeleev/'

PIVOT = '''### 8.8 W8 — Mix equalizado (voz / skills / musica)
Medicao real RMS (ffmpeg astats): musica -14.0dB | skills -16.6dB (picos -9.2dB) |
voz -15.8dB. Causa raiz do desequilibrio: boost `1.4x` no falloff do playAt saturava
voz/tombo/cast NO MESMO CLAMP (play faz `master 0.85 x min(falloff*boost*cue, 1)`).
Mix novo (audio eff = master 0.85 x cue):
| canal | cue | eff | papel |
|---|---|---|---|
| voz (unitVoice) | 0.92 | 0.78 | referencia do mix (gated 1.7s) |
| tombo (ground_hit) | 0.90 | 0.765 | impacto dramatico empatado a voz |
| cast skill | 0.80 | 0.68 | 1.8dB abaixo |
| melee soco/chute | 0.80 | 0.68 | 1.8dB abaixo (antes 0.62) |
| hit_s | 0.70 | 0.595 | 2.9dB abaixo |
| kunai | 0.70 | 0.595 | agudo, percebido como alto |
| sword | 0.65 | 0.5525 | 3.2dB abaixo (antes 0.45/0.6) |
| musica menu | baseVol 0.70 | 0.385 x musicVol | ~12dB abaixo da voz |
| musica battle | baseVol 0.55 | 0.3025 x musicVol | ~8dB abaixo (audivel, "de leve") |
Falloff do playAt: boost `1.4 -> 1.0` (headroom real pra degraus diferenciaveis).
Nota de runtime: playAt usa `cam.position` (camera THREE) desde W-REAL do pipeline paralelo.

'''

TEST_READY = '''
## W8 — Mix Equalizado
- Probe `tools/probe_w8_mix.py`: C1 musica battle vol=0.3025 | C2 voz unitVoice v=0.92 (sem
  clamp) | C3 skill perto v=0.9 (<0.99 headroom) | C4 menu vol=0.385 | C5 zero console -> 5/5.
- Bateria: suite 51/51. Verify vermelho APENAS por 404 de `combo_digit_5..9.png` (HUD MOBA do
  pipeline paralelo so embarcou 0-4) — nao e do mix W8.
- Pitfall: probe mocka `window.__camera = {position:{x,z}}` (playAt le cam.position).

'''

PROJECT = '''
39. **W8 Mix equalizado (RMS medido)** — voz 0.92 / skills 0.65-0.9 com headroom real
    (boost do falloff 1.4->1.0 elimina o clamp que empatava voz/tombo/cast no topo);
    musica battle 0.38->0.55 baseVol (eff 0.3025, ~8dB abaixo da voz). Medicao:
    musica -14dB, skills -16.6dB picos -9.2dB, voz -15.8dB. Probe 5/5, suite 51/51.

'''

LIFELINE = '''- **W8 (equalizacao de mix)**: medicao RMS astats — musica -14.0dB, skills -16.6dB (picos
  -9.2dB), voz -15.8dB. Causa raiz do desequilibrio: boost 1.4x no falloff do playAt saturava
  voz/tombo/cast NO MESMO CLAMP (`master 0.85 x min(falloff*boost*cue,1)`), sem degrau
  perceptivel. Solucao: boost 1.4->1.0 + cue vols escalonados (voz 0.92 referencia, tombo 0.9,
  cast/melee 0.8, hit/kunai 0.7, sword 0.65) + musica battle 0.38->0.55 (menu mantem 0.70).
  Falloff por cam.position (THREE camera) desde W-REAL do pipeline paralelo — probe mocka
  `{position:{x,z}}`. Probe 5/5 (voz 0.92 e skill 0.9 sem clamp), suite 51/51. Verify vermelho
  so por 404 combo_digit_5..9.png do HUD MOBA do paralelo (nao e do mix).
**Body**:
Medicao guia equalizacao (nao chute): ffmpeg astats RMS dB por canal antes de calibrar ganhos;
master 0.85 multiplica tudo (slider do perfil escala proporcional, mix relativo preservado).

'''

def append_file(path, text):
    full = G + path
    if not os.path.exists(full):
        return f'FALTA {full}'
    s = open(full, encoding='utf-8', newline='').read()
    if s.count('W8') >= 2:
        return f'JA TEM W8 {path}'
    if '<!-- lifeline:end -->' in s:
        s = s.replace('<!-- lifeline:end -->', text + '<!-- lifeline:end -->', 1)
    else:
        s = s + ('\r\n' if '\r\n' in s else '\n') + text
    open(full, 'w', encoding='utf-8', newline='').write(s)
    return f'OK {path}'


print(append_file('docs/PIVOT_MOBILE.md', PIVOT))
print(append_file('TEST_READY.md', TEST_READY))
print(append_file('PROJECT.md', PROJECT))
print(append_file('LIFELINE.md', LIFELINE))
