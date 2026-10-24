"""W7 docs: PIVOT_MOBILE §8.7, TEST_READY §W7, PROJECT row 53, LIFELINE append."""
ok = []


def patch(path, anchor, insert_after=True, text=''):
    s = open(path, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s[:2000] else '\n'
    a = anchor.replace('\n', nl)
    assert s.count(a) == 1, f'ancora != 1 em {path}: {anchor[:60]!r}'
    t = text.replace('\n', nl)
    s = s.replace(a, (a + t) if insert_after else (t + a), 1)
    open(path, 'w', encoding='utf-8', newline='').write(s)
    ok.append(path)


# ---- PIVOT_MOBILE §8.7 após a §8.6 (frase final)
patch('docs/PIVOT_MOBILE.md',
      'aplicam LIVE (`MUSIC.applySettings()` / `AUTH_SFX.volume`) e\npersistem no perfil (`music`, `musicVol`, `sfxVol` no schema do\nloadProfileData). Probe `tools/probe_w6_music.py` **7/7**.',
      True, """

### 8.7 W7 — HUDs com estética shadcn + Framer Motion vanilla (2026-10-23)

Pedido: usar shadcn + framer motion nos HUDs de batalha, aliviando o peso
dos informativos no meio da tela (SEQUÊNCIA e ULT). **Decisão de engenharia**
documentada: shadcn/ui literal exige React+Tailwind+bundler — incompatível
com o runtime vanilla (DOM inviolável §UI_SKIN_CONTRACT, suite 47/47 lê
IDs/classes); aplicamos os **design tokens e o pattern Sonner** (toast
compacto no canto, blur + border fino, não-bloqueante) e o **Framer Motion
vanilla de verdade**: bundle `framer-motion@12/dom/+esm` (motion.dev, mesmo
autor) vendored em `public/assets/vendor/` (3 arquivos, 141 KB / ~40 KB
gzip) — spring FÍSICA (stiffness/damping), não ease curve. Import dinâmico
com fallback GSAP (`w7Spring`) — o jogo nunca quebra se a lib falhar.

- **`#streak-banner` (SEQUÊNCIA)**: sai do MEIO (era top 18% left 50%,
  340px de largura, border-image 12px, flare infinito) → toast estilo sonner
  no canto sup. direito (top 74px/right 12px, w 184px medido, h 43px),
  backdrop-blur 10px, border 1px white/9%, badge laranja no count
  (rgba(249,115,22,.16) pill), kanji 19px/text 12px, flare desativado,
  keyframes streakPop OFF (eram translateX(-50%) — voariam no novo
  layout). Entrada: spring y -10→0 + scale .94→1 (stiffness 380/damping
  26); vida 1.6s via pulseSkinHook (auto-dismiss).
- **`#center-banner` (ULT)**: pill compacta top 28% (era 36%), padding
  10px 26px (era 16px 60px), border-image 14px → 1px white/10% + radius
  16px + blur 12px, font 19px (era 26px), duração 2600→2100ms, pop spring
  scale .94→1 (stiffness 520/damping 34) com x/y -50% constantes nos
  keyframes (transform-clash-free).
- Touch: streak top 64px/padding 6px 12px; center top 22%/font 14px.
- IDs + classes hidden/show intactos (suite lê center-banner.hidden);
  `gsap-anim` class órfã removida do fluxo do streak.

Probe `tools/probe_w7_hud.py` **6/6 desktop + 6/6 mobile** (vendor 200 ×3,
MOTION.animate fn, center pill w 302/h 48/top 28%, streak rightPct 99/top
74/h 43, hidden semantics, 0 console errors) + screenshots
`w7_banner_desktop.png` / `w7_banner_mobile.png`.""")

# ---- TEST_READY
patch('TEST_READY.md',
      '### W6 — MÚSICA DE FUNDO + SETTINGS FUNCIONAIS — validado 2026-10-23',
      False,
      """### W7 — HUDS SHADCN + FRAMER MOTION VANILLA — validado 2026-10-23
- `python tools/probe_w7_hud.py` -> **6/6 desktop + 6/6 mobile** (C1 vendor
  motion 200 x3; C2 window.MOTION.animate fn; C3 center-pill w<=480/h<=80/
  top 22-34% + spring transform inline; C4 streak right>60% VW/top 74px/
  h<64; C5 hidden semantics; C6 zero console errors).
- Probe roda startMatch ANTES dos checks de banner (HUD só é visível em
  partida — rects 0 no lobby são falso-negativo).
- Motion bundle: assets/vendor/{motion,motion-dom,motion-utils}.esm.js —
  imports jsdelivr reescritos para caminhos locais; validado com
  `node --input-type=module` antes do browser.
""")

# ---- PROJECT row 53
patch('PROJECT.md',
      '| 52 | W6 — Música de fundo (bgm.awb) + settings de áudio funcionais',
      False,
      """| 53 | W7 — HUDs de batalha: estética shadcn + Framer Motion vanilla | framer-motion@12/dom/+esm (motion.dev) vendored (3 arquivos 141KB/~40KB gzip) com import dinâmico e fallback GSAP (w7Spring); #streak-banner vira toast estilo sonner no canto sup. direito (era centro, 340px, border-image 12px, flare infinito -> agora 184px, blur+border 1px, badge laranja, flare off, spring y-10->0); #center-banner vira pill compacta top 28% (era 36%, padding 60px, border-image 14px -> 10px 26px, border 1px+blur, font 19px, pop spring, 2100ms); keyframes streakPop OFF (translateX voaria no novo layout); IDs/classes hidden intactos (suite); probe 6/6 desktop+mobile | W7 (HUD/motion) | TEST_READY.md §W7 |
""")

# ---- LIFELINE append
s = open('LIFELINE.md', encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s[:2000] else '\n'
entry = """
### [2026-10-23] W7 — HUDs com estética shadcn + Framer Motion vanilla
**Agente:** human · **Provider:** none · **Model:** human

**O quê:** os informativos de SEQUÊNCIA e ULT saem do meio da tela —
streak vira toast compacto no canto sup. direito, ult vira pill discreta
top 28% — ambos com blur, border fino e spring física do Framer Motion.

**Por quê:** pedido do usuário ("pode usar um shadcn, e framer motion,
para huds da batalha? aliviar o peso dos informativos no meio da tela,
de sequencia, e ulti, com excelência, busque pesquisa e referências").
Pesquisa: pattern Sonner (toast no canto, não-bloqueante) + motion.dev
(spring física). Decisão: shadcn/ui literal (React+Tailwind+bundler)
inviável no runtime vanilla com DOM inviolável — tokens/pattern aplicados
no CSS puro; Motion vanilla vendored entra de verdade.

**Como:** bundle framer-motion@12/dom/+esm (141KB, imports jsdelivr
rescritos local) + w7Spring helper com fallback GSAP; CSS compacto
(blur 10-12px, border 1px rgba white/9-10%, radius 12-16px); flare
infinito OFF; keyframes streakPop OFF (translateX(-50%) voaria no
canto); probe 6/6 desktop+mobile com screenshots.
""".replace('\n', nl)
open('LIFELINE.md', 'w', encoding='utf-8', newline='').write(s + entry)
ok.append('LIFELINE.md')
print('DOCS OK:', ok)
