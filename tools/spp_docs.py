# -*- coding: utf-8 -*-
"""Docs SPP: TEST_READY.md §13 + PROJECT.md feature 34. Rodar apos bateria SPP verde."""
import io, sys

def apply(path, patches, append=None):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        if s.count(old) != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {s.count(old)} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {path}: {name}')
    if append:
        s = s.rstrip('\n') + '\n' + append
        print(f'  [OK] {path}: append')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = True

ok &= apply('TEST_READY.md', [], append="""

---

## 13. Re-Verification — SPP: Skill Presentation Pass (2026-10-20)

### Pedido do usuário
- "Usar o REA pra extrair os visuais e direções das skills corretamente... clones das sombras
  parecer os clones 3D do Naruto, o rasengan com casting e visual... assim como todos" +
  "se necessário usar o Blender, MCP, para alinear as animações de skills e efeitos"

### Nota de ferramentas
- **REA**: não está instalado na máquina — e é desnecessário: os chunks que importam
  (`nuccChunkAnm` skl1/skl2, `eff1`/spc, `bod1`) JÁ foram decodificados pelo toolchain Python
  próprio do repo (APK_REVERSE.md §3) — castings 19-bone por herói em `animations.json`,
  VFX em `skill_vfx.json`, modelos com rig em `models/*.json`
- **Blender**: 5.2 instalado; não existe MCP de Blender no catálogo Hermes — headless via CLI
  (`blender -b --python`), o mesmo fluxo já comprovado do `tools/blender_validate_all.py`

### Implementação (SPP v1)
- **Kage Bunshin REAL (Naruto W)**: `spawnShadowClones` — 3 clones 3D com o modelo extraído
  do próprio Naruto (`cloneCharacterModel` + rig de 20 bones), opacidade 0.85, **poof de
  fumaça na invocação**, perseguição pela arena (busca 999 — lição M6.2), anim `run` real,
  dano em contato (60% do kit) + poof; TTL 4.5s com poof de saída; reset no rematch
- **Anim procedural por skill**: `SKILL_VFX_ANIM` (10 heróis × 4 slots): spin (rasengan,
  chidori, kaiten, palms), thrust (fireball, water dragon, toad fire, air palm), pulse
  (selos, areia, auras), rise (fumacas, amaterasu) — engine no update do `vfxList`
- **Facing**: VFX extraído nasce com `rotation.y = rotY` do caster (extGrp encara a direção
  do cast) + `faceDir` para thrust
- Exposição E2E: `window.SKILL_VFX_ANIM` + `window.__shadowClones()` (padrão M7)
- Aditivo por design: nenhum dano/cooldown existente mudou — suite-safe

### Como o SPP se encaixa no que já existia
- O rasengan do Naruto Q JÁ tinha bind no osso da mão (13) e o chidori no 9 (P1 JUICE);
  o SPP adiciona a camada de anim + facing que faltava nos casts que usam `spawnVFX` puro

### Validação
- Smoke determinístico SPP: 9/9 PASS — 3 clones spawnam rigados, perseguem (delta pos real),
  dano em contato + poof, TTL limpa, Q com anim spin, reset no rematch
- Bugs de smoke achados e corrigidos no caminho: (1) W do Naruto tem branch específico que
  nunca chega no genérico `clone_burst` — clones wired no branch certo; (2) busca de alvo
  dos clones tinha raio 45 (cidade-fantasma M6.2 de novo) → 999
- Bateria: verify + suite 38/38 isolado (`spp_*.log`)
- Auditoria Blender (direções): `tools/spp_blender_audit.py` → `spp_blender_report.json`
  (bbox/eixo principal/yaw sugerido por modelo; directionais ganham bake)
- Rollbacks: `public/*.bak_spp` + `public/*.bak_sppexp`

**Verdict: SPP v1 DONE — Kage Bunshin invoca clones 3D de verdade e as 40 skills têm anim + direção.**""")

ok &= apply('PROJECT.md', [
    ('feature 34',
     'antes empate dava vitória silenciosa ao azul; `window.__matchState` para debug | Game Balance | TEST_READY.md §12 |',
     'antes empate dava vitória silenciosa ao azul; `window.__matchState` para debug | Game Balance | TEST_READY.md §12 |\n'
     '| 34 | SPP: clones 3D + anim por skill + facing | **Kage Bunshin real**: `spawnShadowClones` invoca 3 clones 3D com o modelo extraído do Naruto (rig 20 bones, poof de fumaça, perseguição em arena aberta, dano em contato, TTL com poof); `SKILL_VFX_ANIM` 10×4 (spin/thrust/pulse/rise) no update do `vfxList`; VFX extraído nasce virado para o `rotY` do caster; smoke 9/9; REA desnecessário (chunks já decodizados pelo toolchain do repo); Blender 5.2 headless p/ auditoria de direções (`tools/spp_blender_audit.py`) | Presentation | TEST_READY.md §13 |'),
])

print('DOCS SPP:', 'PARCIAL' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
