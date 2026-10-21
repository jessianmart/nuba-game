"""Docs PV3 (governor + VFX cap + haptics + PWA).
Run: python tools/pv3_docs_update.py   (cwd = repo root)
"""
F46 = '| 46 | PV3.1+PV3.3 — Perf e polimento mobile | `window.__GOV` (governor no boot): mobile detectado por UA/touch → dpr cap 1.25 e teto de 24 VFX, desktop segue 1.75/ilimitado; `applyQuality` da pagina de ajustes respeita o cap mobile (nao fura por cima); VFX cap no loop de update descarta o efeito mais ANTIGO acima do teto (remove do arenaGroup); `haptic(pattern)` com throttle 60ms + gate `data.haptics === false` — 18ms levou dano, 12ms acertou, [40,60,40] morreu (so mobile); PWA instalavel: `public/manifest.webmanifest` (fullscreen, orientation landscape, theme #f97316) + icones 192/512 quadrados gerados do logo.png via Pillow (fundo #0b0d12 real do body) + metas no head (theme-color, apple-mobile-web-app-capable); PV3.2 (arena merge) e PV3.4 (smoke device real) fora deste patch; validado probe_pv3_polish (governor 4/4, pico natural 273 VFX → capado ≤24, haptics 18/12, PWA 9/9) + bateria 38/38 zero erros | PV3 (perf/polimento) | docs/PIVOT_MOBILE.md §PV3 |'

NOTA_PV3 = '''### Fase PV3 — status de entrega (2026-10-21)

| Item | Status | Evidencia |
|---|---|---|
| PV3.1 Quality governor (dpr cap 1.25 + VFX cap 24 em mobile) | ENTREGUE | `window.__GOV` no boot; `probe_pv3_polish` 4/4 (pixelRatio real = 1.25) |
| PV3.1 VFX cap no loop | ENTREGUE | pico natural de **273 VFX** na injecao de 40 impactos → **≤24** apos o cap |
| PV3.2 Arena merge (sd00a 122 meshes → ~20) | PENDENTE | pipeline Blender disponivel (`tools/vila_blender_optimize.py`) |
| PV3.3 Haptics + audio unlock + PWA manifest | ENTREGUE (haptics + PWA) | `haptic()` throttle 60ms + gate de perfil; `manifest.webmanifest` + icones 192/512; `probe_pv3_polish` PWA 9/9 |
| PV3.4 Smoke em device real (LAN/tunnel) | PENDENTE (depende do usuario) | checklist no probe responsivo |

'''

PIVOT = 'docs/PIVOT_MOBILE.md'
d = open(PIVOT, encoding='utf-8', newline='').read()
anchor = '### Fase PV4 — Touch HUD V2 (entregue 2026-10-21, pedido do usuario)'
assert d.count(anchor) == 1, f'ancora PV4: {d.count(anchor)}'
d = d.replace(anchor, NOTA_PV3.replace('\n', '\r\n') + anchor, 1)
open(PIVOT, 'w', encoding='utf-8', newline='').write(d)

p = open('PROJECT.md', encoding='utf-8', newline='').read()
a45 = ' | PV4 (HUD touch) | docs/PIVOT_MOBILE.md §PV4 |'
assert p.count(a45) == 1, f'ancora 45: {p.count(a45)}'
p = p.replace(a45, a45 + '\r\n' + F46, 1)
open('PROJECT.md', 'w', encoding='utf-8', newline='').write(p)

t = open('TEST_READY.md', encoding='utf-8', newline='').read()
t += '''

### PV3 — PERF E POLIMENTO MOBILE (governor + VFX cap + haptics + PWA) — validado 2026-10-21
- `tools/probe_pv3_polish.py` (UA iPhone setado ANTES do load, senao o governor
  lido no boot nao ve mobile):
  - GOVERNOR 4/4: `__GOV.mobile=true`, `dprCap=1.25`, `renderer.getPixelRatio()=1.25`
    (cap REALMENTE aplicado), `vfxCap=24`. Desktop segue 1.75/ilimitado.
  - VFX CAP: injecao de 40 impactos gerou **pico natural de 273 VFX simultaneos**
    (evidencia de que o cap mobile e necessario) → com cap 24 o array convergiu
    para ≤24 em 2s. O cap roda no loop de update e descarta o efeito MAIS ANTIGO.
  - HAPTICS: `haptic(18)` ao levar dano, `haptic(12)` ao acertar, `[40,60,40]` ao
    morrer; throttle 60ms; gate `data.haptics === false`.
  - PWA 9/9: `Page.getAppManifest` sem erros (orientation landscape, theme
    #f97316, display fullscreen, icones 192/512) + link/meta no head + 200 nos
    2 icones e no manifest.
- Bateria `pv3`: verify EXIT 0 + suite 38/38 zero console errors.
- Pitfalls encontrados: (1) hits perto da base sao bloqueados pelo SPAWN GUARD —
  probes que injetam dano precisam zerar `target.spawnShield`; (2) o governor e
  lido no BOOT, entao so `body.classList.add('touch')` NAO liga o caminho mobile —
  precisa `Emulation.setUserAgentOverride` antes do `Page.navigate`.
- Novos `.bak`: game.js.bak_pv3, index.html.bak_pv3.
- PV3.2 (arena merge) e PV3.4 (smoke em device real) seguem pendentes.
'''
open('TEST_READY.md', 'w', encoding='utf-8', newline='').write(t)
print('[ok] docs PV3: PROJECT.md #46, PIVOT_MOBILE status PV3, TEST_READY secao PV3')
