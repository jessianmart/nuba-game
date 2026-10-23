"""W5-lifeline: append da entrada W5 no fim do LIFELINE.md (a ancora
<!-- lifeline:end --> repete 26x — inserir entry no FIM do arquivo).
Parent = hash da ultima entrada (W-TRAIL, d4051c95...).
"""
import shutil

P = 'LIFELINE.md'
shutil.copy2(P, P + '.bak_w5docs')

ENTRY = """
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W5 — SFX/vozes autenticas do APK posicionadas (volume por distancia)
- **parents**: d4051c954322bc7a627eeb8f7309464cac3b431af716eeaef2287c44c7bae8ec

**Body**:
W5 entrega o pedido de audio do usuario: vozes originais do APK do Storm no
momento de batalha de cada ninja, volume obedecendo a distancia e sons corretos
de combate — zero som generico. Extracao reaproveita os bancos CRI ja no repo
(Se_*.xfbin -> ACB por unwrap NUCC com parse_nucc_chunks) com vgmstream
(subsong por CueName), sem tocar no APK de 3,4 GB; +22 cues (47->70 oggs).
playAt com falloff pow(1-min(d/60,1),1.2)*1.4 da camera: luta distante some
(<0.06), jogador claro (~0.95). Genericos removidos de todos os caminhos de
batalha — o mais grave era o impacto de kunai tocando menu_slct (sfx.clink
wrappeado pela UI). Variacao hit1/hit2 por pick() para nao repetir; throttles
dedicados para o combate 12-unidades nao virar sopa de som; edge-trigger no
ult pronto (max_gauge 1x) e awake_off no fim do awakening. Probe 13/13 +
bateria 47/47 + verify 0 erros. Bins e cues versionados no repo
(determinismo: servidor :8080 serve tudo do proprio repo). PV4.2 (banners
leves + zoom) finalmente documentado no mesmo ciclo — ficou de fora do docs
quando foi entregue.

<!-- lifeline:end -->
"""

s = open(P, encoding='utf-8', newline='').read()
tail = s.rstrip('\n').rstrip('\r').rstrip()[-60:]
assert 'lifeline:end' in tail, 'fim do arquivo nao e uma entry lifeline'
open(P, 'w', encoding='utf-8', newline='').write(s.rstrip('\n') + ('\n' if '\n' in s else '\r\n') + ENTRY)
print('LIFELINE: entrada W5 appended no fim (backup .bak_w5docs)')
