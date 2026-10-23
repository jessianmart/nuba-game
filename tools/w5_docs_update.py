"""W5-docs: registra W5 (SFX autênticos posicionados) + PV4.2 (pendente) nos
docs contrato do repo — TEST_READY.md (secoes de validacao), PROJECT.md
(feature rows 49/50), docs/PIVOT_MOBILE.md (§8.5), LIFELINE.md (decisao).

Só de passar com anchor existente + assert de presenca do marcador novo.
Run: python tools/w5_docs_update.py   (cwd = repo root)
"""
import shutil

BKP = '.bak_w5docs'
MARK = 'W5'

FILES = ['docs/PIVOT_MOBILE.md', 'TEST_READY.md', 'PROJECT.md', 'LIFELINE.md']
for f in FILES:
    shutil.copy2(f, f + BKP)

TR_SECAO = """### W5 — SFX AUTÊNTICOS DO APK POSICIONADOS (vozes no momento da batalha + volume por distância) — validado 2026-10-22
- Pedido do usuário: "puxar do apk as vozes originais e aplicar estrategicamente
  no momento da batalha de cada um obedecendo a distancia... nos sons CORRETOS
  de batalha, nada de som generico".
- Extração (`tools/extract_battle_sfx.py`): bancos CRI já no repo
  (`public/assets/audio/data_sound_Se_*.xfbin`) -> unwrap NUCC
  (`parse_nucc_chunks` de extract_moba_assets) -> blob `@UTF` (= ACB) ->
  `vgmstream-cli -s N` (subsong por CueName) -> wav -> ffmpeg -> ogg mono em
  `public/assets/audio/decoded/`. 6 ACBs em `tools/audiobanks/` (10,5 MB):
  battle 141 cues, common 177, hugebtl/pupSe/missionSe/minigame.
- 47 -> 70 oggs autênticos: +22 cues (kunai_hit, kunai_hit2, kunai_hit_wall,
  kunai_miss, shuriken, kick_swing, kick_hit2, punch_hit2, ground_hit,
  ground_hit2, water_hit, body_atk, sousai, stand_up1, stand_up2, awake_off,
  box_open, chakura_get, item_get, jump1, jump2, chak_hit). Nomenclatura
  preservada do CueName (S_maxGauge -> max_gauge.ogg).
- `AUTH_SFX.playAt(name, x, z, opts)`: falloff `pow(1 - min(d/60,1), 1.2) * 1.4`
  a partir de `window.__camera`; abaixo de 0.06 vira silêncio (luta distante
  desaparece; sons do jogador ~0.95 em d~15). `AUTH_SFX.pick(a, b)` alterna
  hit1/hit2 (variação sem repetição). `lastPlays` (cap 60) grava {n, v, d}.
- **ZERO chamadas genéricas em batalha** (sfx.hit/kick/ko/shuriken/ultimate/
  kawarimi/jutsu/resurrect removidas): impacto dealDamage -> hit_s (+ground_hit/
  ground_hit2 em dmg >= 180); melee -> punch_hit/kick_hit com variação no alvo;
  arremesso -> kunai_swing (golpe 1, 1 kunai) / shuriken (2-3); impacto de
  projétil -> kunai_hit/kunai_hit2 (**era sfx.clink = menu_slct, som de menu no
  impacto!**); kunai errada -> kunai_hit_wall; KO -> down+ko; ressurreição ->
  stand_up1/2; fim do awakening -> awake_off; ult pronto -> max_gauge
  (edge-trigger `_ultReadyAnnounced`, player); baú do BR -> box_open+chakura_get;
  vozes de cast do herói (SKILL_SFX_MAP, 12 heróis) + dash/awake_open/level_up
  agora posicionados (bots distantes nos volumes certos); UI do lobby e cheat
  lines autênticos (menu_slct/menu_fix/chakura_use).
- Throttles dedicados no THROTTLE map: kunai_swing 90, shuriken 110, kunai_hit
  60, ground_hit 240, box_open 1200, awake_off 1500.
- `tools/probe_w_sfx.py` 13/13: C1 22 cues HEAD 200; C2 falloff
  d0=1 -> d25=0.73 -> d50=0.16 + skip > 60u; C3/C3b hit_s + ground_hit
  posicionados; C4 melee punch/kick; C5 voz do herói posicionada; C6
  down/ko/level_up; C7 stand_up (respawn dm_3v3 = 6s, poof aos 4s); C8
  awake_off; C9 max_gauge; C10 kunai_swing + kunai_hit; 0 console errors.
- Pitfalls: (1) throttle é por NOME e o combate 12-unidades come o budget —
  probes precisam resetar `AUTH_SFX._last = {}`; (2) `lastPlays` cap estoura com
  o combate ambiente (bots enchem em < 1s) — ler early+late; (3) `clampArena`
  puxa teleporte longo de volta pela borda — usar deslocamento curto válido;
  (4) respawn: contagem 6s, poof aos 4s, rebirth no santuário.
- Novos `.bak`: public/game.js.bak_w5sfx; novos artefatos:
  tools/extract_battle_sfx.py, tools/w_sfx_patcher.py, tools/probe_w_sfx.py,
  tools/audiobanks/ (ACBs + vgmstream r2117).

### PV4.2 — Banners leves + zoom afastado (pendente de doc, validado 2026-10-22)
- Peso dos textos de ult/sequencia cai por fonte/caixa/moldura (a regra PV4
  `transform: scale(0.55)` NUNCA teve efeito — keyframes/GSAP sobrescrevem
  transform ao animar): ult 26px->15px, padding 60->24, borda 14->8, top
  36%->24%; streak kanji 30->19, texto 22->13, contador 42->26, caixa 340->220.
  Gates `body.touch` — desktop intacto.
- Zoom thirdperson: `camDist` 13.5 -> 16 (pitch 0.32 mantido; distância real
  medida 17.3 no probe PV4.2 v2).
- Probe probe_pv4_2_v2: 11/11 — câmera 17.3, banners leves e dentro da tela,
  0 console errors (navigator.vibrate bloqueado no headless = PV3.3 correto).
"""

TR_ANCHOR = '### Tier 5 E2E — PV1.6/PV2.6 formal (validado 2026-10-22)'

PROJ_49 = '| 49 | W5 — SFX autênticos do APK posicionados (vozes + som correto de batalha) | Extração CRI local: 6 ACBs dos xfbin Se_* (10,5MB) -> vgmstream-cli (r2117) -> +22 oggs autênticos (47->70 em public/assets/audio/decoded/); `AUTH_SFX.playAt(nome,x,z)` com falloff pow(1-min(d/60,1),1.2)*1.4 da camera (<0.06 = silêncio — luta longe some) + `pick(a,b)` de variação hit1/hit2; ZERO genéricos em batalha: hit_s/ground_hit (pesado), punch_hit/kick_hit no melee, kunai_swing/shuriken no arremesso, kunai_hit/kunai_hit2 no impacto (era menu_slct via sfx.clink!), kunai_hit_wall na errada, down/ko, stand_up1/2 no respawn, awake_off no fim do awakening, max_gauge no ult pronto (edge-trigger), box_open+chakura_get nos baús do BR; vozes do herói (SKILL_SFX_MAP 12) + dash/awake/level_up posicionados; probe_w_sfx 13/13 + 0 erros | W5 (áudio) | TEST_READY.md §W5 |\n'
PROJ_50 = '| 50 | PV4.2 — banners leves + zoom afastado (touch) | Peso real dos banners cai em fonte/caixa/moldura (transform:scale sobrescrito por keyframes/GSAP): ult 26->15px padding 60->24 borda 14->8; streak 30/22/42 -> 19/13/26px, caixa 340->220, gates body.touch (desktop intacto); camDist 13.5->16 (zoom >, pitch mantido, real medido 17.3); probe_pv4_2_v2 11/11 | PV4.2 (UI touch) | TEST_READY.md §PV4.2 |\n'

PVM_SECAO = """### 8.5 W5 — Áudio autêntico do APK na batalha (pedido direto do usuário 2026-10-22)

Fora do escopo original das fases 8.2 (o escopo dizia "áudio permanece como
está") — o usuário pediu explicitamente as **vozes originais do APK** no momento
da batalha de cada ninja, **com volume obedecendo à distância** e os **sons
corretos de combate, sem nada genérico**. Entregue em W5:

- 70 cues autênticas de Naruto Ultimate Ninja Storm em
  `public/assets/audio/decoded/` (+22 novas, pipeline em
  `tools/extract_battle_sfx.py` + vgmstream em `tools/audiobanks/`).
- `AUTH_SFX.playAt` posiciona cada som pela distância câmera→fonte
  (falloff suave, silêncio além de ~60u): a luta dos bots atravessando a vila
  toca nos volumes certos, o que acontece perto do jogador é claro.
- Cada momento de batalha tem o som correto do jogo original: impacto, queda
  pesada, soco/chute (com variação), kunai/shuriken, impacto metálico
  (substituindo o som de menu que tocava no impacto de arma), KO, ressurreição,
  fim de awakening, ult pronto, baús do BR; vozes de jutsu por herói no cast.
- ZERO áudio sintetizado em batalha (os bleeps de `SoundFX` saíram de todos os
  caminhos de combate; sobram apenas na UI, onde cues autênticas os cobrem).
- Validação: `tools/probe_w_sfx.py` 13/13 + bateria 47/47 + verify 0 erros.
"""

LIFE_BODY = """**Body**:
W5 entrega o pedido de áudio do usuário: vozes originais do APK do Storm no
momento de batalha de cada ninja, volume obedecendo à distância e sons corretos
de combate — zero som genérico. Extração reaproveita os bancos CRI já no repo
(Se_*.xfbin -> ACB por unwrap NUCC) com vgmstream (subsong por CueName), sem
tocar no APK de 3,4 GB; +22 cues (47->70 oggs). playAt com falloff
pow(1-min(d/60,1),1.2)*1.4 da camera: luta distante some (<0.06), jogador
claro (~0.95). Genéricos removidos de todos os caminhos de batalha — o mais
grave era o impacto de kunai tocando menu_slct (sfx.clink estava wrappeado
pela UI). Variação hit1/hit2 por pick() para não repetir; throttles dedicados
para o combate 12-unidades não virar sopa de som; edge-trigger no ult pronto
(max_gauge 1x) e awake_off no fim do awakening. Probe 13/13 + bateria 47/47 +
verify 0 erros. Bins e cues versionados no repo (determinismo: servidor :8080
serve tudo do próprio repo).
"""


def read(p):
    return open(p, encoding='utf-8', newline='').read()


def write(p, s):
    open(p, 'w', encoding='utf-8', newline='').write(s)


def rep(s, old, new, label, path):
    for sep in ('\r\n', '\n'):
        o, n = old.replace('\n', sep), new.replace('\n', sep)
        if s.count(o) == 1:
            print(f'[ok] {path} — {label}')
            return s.replace(o, n, 1)
    c = sum(s.count(old.replace('\n', sep)) for sep in ('\r\n', '\n'))
    raise SystemExit(f'[{path}:{label}] âncora não encontrada ou duplicada ({c})')


# TEST_READY: seções W5 + PV4.2 antes do Tier 5
t = read('TEST_READY.md')
t = rep(t, TR_ANCHOR, TR_SECAO + '\n' + TR_ANCHOR, 'seções W5+PV4.2', 'TEST_READY')
write('TEST_READY.md', t)

# PROJECT.md: rows 49 (W5) + 50 (PV4.2) coladas antes da row 43 (ordem decrescente do arquivo)
p = read('PROJECT.md')
p = rep(p, '| 43 | Otimizacao Blender da vila', PROJ_49 + PROJ_50 + '| 43 | Otimizacao Blender da vila', 'rows 49+50', 'PROJECT')
write('PROJECT.md', p)

# docs/PIVOT_MOBILE.md: §8.5 no fim da §8
d = read('docs/PIVOT_MOBILE.md')
d = rep(d, '### 8.4 Regras de execução', PVM_SECAO + '\n### 8.4 Regras de execução', '§8.5 W5', 'PIVOT_MOBILE')
write('docs/PIVOT_MOBILE.md', d)

# LIFELINE.md: entrada W5 logo após o último <!-- lifeline:end -->
l = read('LIFELINE.md')
l = rep(l, '<!-- lifeline:end -->', '<!-- lifeline:end -->\n\n- **agent**: Max\n- **provider**: modal\n- **model**: step-5-preview\n- **kind**: decision\n- **summary**: W5 — SFX/vozes autênticas do APK posicionadas (volume por distância)\n- **parents**: d4051c954322bc7a627eeb8f7309464cac3b431af716eeaef2287c44c7bae8ec\n\n' + LIFE_BODY + '\n<!-- lifeline:end -->', 'entrada W5', 'LIFELINE')
write('LIFELINE.md', l)

# autoverificação
for f in FILES:
    assert MARK in read(f), f'{f} sem marcador {MARK}'
assert 'playAt' in read('TEST_READY.md') and '| 49 |' in read('PROJECT.md')
print('W5 DOCS UPDATE DONE (4 arquivos + backup .bak_w5docs)')
