"""W5-F2 docs: PIVOT_MOBILE §8.5 (subseção F2), TEST_READY §W5-F2,
PROJECT row 51, LIFELINE append. Âncoras únicas, CRLF imune (line-based)."""
import re

ok = []


def patch(path, anchor, insert_after=True, text=''):
    s = open(path, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s[:2000] else '\n'
    a = anchor.replace('\n', nl)
    assert s.count(a) == 1, f'ancora != 1 em {path}: {anchor[:50]!r}'
    t = text.replace('\n', nl)
    s = s.replace(a, a + (t if insert_after else '') if insert_after else t + a, 1)
    open(path, 'w', encoding='utf-8', newline='').write(s)
    ok.append(path)


# ---- PIVOT_MOBILE: §8.5 ganha subseção F2 (após a linha de intro do 8.5)
patch('docs/PIVOT_MOBILE.md',
      '### 8.5 W5 — Áudio autêntico do APK na batalha (pedido direto do usuário 2026-10-22)',
      True, """
#### 8.5.1 W5-F2 — Vozes de batalha POR HERÓI (bancos PL_1XXX) — 2026-10-23

Descoberta-chave: o APK carrega **um voice bank por ninja** no `sound.awb`
(CPK interno): `PL_1nrt.xfbin` ... `PL_1tyo.xfbin` (30 ninjas, ~78 cues de
batalha cada — `S_PL_DmgS1-3`, `DmgM1-2`, `DmgL1-2`, `AtkS1-3`, `AtkM1-2`,
`AtkL1-2`, `Combo1-3`, `Awake`, `Catch`, `GrdBrk1-2`...). Extração: ACB
embutido no xfbin (`tools/extract_pl_banks.py` @UTF 8+tsize) ->
`tools/extract_voices_nuba.py` (vgmstream 56 subsongs + ffmpeg mono q2) ->
**252 oggs (21 cues × 12 heróis do NUBA, 2,6 MB)** em
`public/assets/audio/decoded/voice/<heroId>/S_PL_*.ogg`.

Wiring (`tools/w5f2_voice_patcher.py`, 5 edições): `HERO_VOICE_MAP` +
`window.unitVoice(u, kind, opts)` com **gate por unidade** (1 voz/1,7 s
padrão; bots 45% mais esparsos; `min:0` para KO/awake, `min:4200` para
cast), volume pelo `playAt` falloff existente. Momentos: dano leve/pesado
na vítima (`DmgS`/`DmgM`), KO (`DmgL` — gemido de queda), cast
(`AtkS` básico / `AtkM` skills / `AtkL` ult), despertar (`Awake`).
Probe `tools/probe_w5f2.py` **8/8** (oggs 200, voz da vítima posicionada,
gate, defensivo, 0 console errors).""")

# ---- TEST_READY: nova seção após a linha de header do W5
patch('TEST_READY.md',
      '### W5 — SFX AUTÊNTICOS DO APK POSICIONADOS (vozes no momento da batalha + volume por distância) — validado 2026-10-22',
      True, """
### W5-F2 — VOZES DE BATALHA POR HERÓI (PL_1XXX) — validado 2026-10-23
- `python tools/probe_w5f2.py` -> **8/8** (C1 62 paths HEAD 200; C2 dano leve
  -> `voice/<hero>/S_PL_DmgS*` na vítima posicionado; C3 pesado -> DmgM+ground_hit;
  C4 kill -> `voice/<hero>/S_PL_DmgL*`; C5 cast atk -> `S_PL_AtkS*` e ult r ->
  `S_PL_AtkL*`+`S_PL_Awake`; C6 gate 1 voz/unidade/1,7s; C7 unitVoice defensivo
  (heroId fora do roster/null -> false); C8 zero console errors).
- Gate de determinismo do probe: `Math.random = () => 0.99` durante os checks
  de dano (bots da vítima têm 45% de skip natural — sem o mock o C2/C3 é
  loteria; restaurado em `finally`).
- Arquivos: 252 oggs (21 cues × 12 heróis, 2,6 MB) em
  `public/assets/audio/decoded/voice/`; infra `HERO_VOICE_MAP`/`unitVoice`
  game.js L287-319; hooks dealDamage L3751, kill L3787, cast L3942, awake L4698.""")

# ---- PROJECT: row 51 após row 50
patch('PROJECT.md',
      '| 50 | PV4.2 — banners leves + zoom afastado (touch)',
      False,
      """| 51 | W5-F2 — Vozes de batalha POR HERÓI (bancos PL_1XXX do sound.awb) | Descoberta dos voice banks por ninja no APK (sound.awb CPK: PL_1nrt..PL_1tyo, 78 cues cada); extract_pl_banks.py (ACB @UTF embutido no xfbin) + extract_voices_nuba.py (vgmstream+ffmpeg) -> 252 oggs 21 cues x 12 heróis (2,6MB) em decoded/voice/<hero>/; unitVoice(u,kind,opts) com gate 1 voz/1,7s por unidade, bots 45% esparsos, falloff playAt; hooks: dano leve/pesado na vítima (DmgS/DmgM), KO (DmgL queda), cast (AtkS/AtkM/AtkL ult), Awake; probe_w5f2 8/8 + Math.random determinístico nos checks de dano | W5-F2 (áudio por herói) | TEST_READY.md §W5-F2 |
""")

# ---- LIFELINE: append
s = open('LIFELINE.md', encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s[:2000] else '\n'
entry = """
### [2026-10-23] W5-F2 — Vozes de batalha por herói: bancos PL_1XXX do APK
**Agente:** human · **Provider:** none · **Model:** human

**O quê:** cada ninja do Storm tem um voice bank próprio (`PL_<nexo>.xfbin`)
no `sound.awb` com 78 cues de batalha. Decodificadas 21 cues × 12 heróis do
Nuba (252 oggs, 2,6 MB) e ligadas nos momentos de combate via `unitVoice`
(gate por unidade 1,7 s, bots esparsos, falloff por distância).

**Por quê:** o pedido do usuário era voz original no momento de cada
hit/jutsu/morte *de cada herói* — os 78 grunts `S_dXX_rear` do battle ACB
eram compartilhados (sem mapa char->dXX em data algum; scan do APK inteiro
deu 0 hits). Os PL_1XXX eliminam a necessidade do mapa: o arquivo É por
herói, com DmgS/M/L, AtkS/M/L, Combo, Awake por ninja.

**Como:** extract_pl_banks (ACB embutido no xfbin) -> vgmstream (56
subsongs inline HCA) -> ffmpeg mono q2 -> decoded/voice/<hero>/.
w5f2_voice_patcher 5 edições; probe_w5f2 8/8 com Math.random mockado
(determinismo dos checks de dano em bots).
""".replace('\n', nl)
open('LIFELINE.md', 'w', encoding='utf-8', newline='').write(s + entry)
ok.append('LIFELINE.md')
print('DOCS OK:', ok)
