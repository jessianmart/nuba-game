# -*- coding: utf-8 -*-
"""W-VIS: visual autentico do APK visivel JUNTO ao casting da skill.
Diagnostico do probe: animacao do personagem e autentica (clips FK do APK,
rig anima), mas o visual de skill e (a) procedural minuesculo (esfera 1.0u
vista de camera MOBA ~50u = sliver 104x8px), (b) o modelo extraido do APK
spawna longe do corpo (fim do dash) e efemero (0.52s c/ fade).
Fix:
  P1 Q 1nrt: modelo extraido 'rasengan' (eff1 do APK, raw 253u) BOUND a mao
     direita (bone 13) por TODO o cast (0.75s), escala 0.0105 (~2.65u na mao,
     proporcao Storm). Procedural vira o core glow interno.
  P2 R 1nrt: modelo extraido 'giant_rasengan' (raw 292u) BOUND a mao por
     1.25s, escala 0.019 (~5.5u) — substitui a esfera procedural plantada no
     ar (fallback procedural se o extracted falhar).
  P3 GLOBAL: caminho extracted do spawnVFX dura duration*1.15 -> *1.7 (acompanha
     a janela de cast 0.75s em vez de morrer em 0.52s).
  P4 Telemetria: window.__HAND_VFX() conta compounds hand-bound (gate E2E).
Idempotente + dry-run com validacao de TODAS as ancoras antes de gravar.
Rollback: public/game.js.bak_wvis
"""
import io, shutil, sys

P = 'public/game.js'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

if 'window.__HAND_VFX' in src:
    print('W-VIS ja aplicado — nada a fazer'); sys.exit(0)

# --- ancoras (bytes grepados agora; arquivo sob edicao paralela) ---
A1_ANC = ("      vfxList.push({ mesh: rasMesh, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });\n")
A1_NEW = A1_ANC + (
    "\n"
    "      // W-VIS: modelo EXTRAIDO do APK ('rasengan', eff1) bound a mao direita\n"
    "      // durante TODO o cast (~2.65u, proporcao Storm) — o visual autentico\n"
    "      // junto ao casting; procedural vira o core glow interno\n"
    "      const rasGrp = buildExtractedVfxMeshGroup(unit.heroId, 0x00d4ff, 0.0105, activeSkillVfxModel || 'rasengan');\n"
    "      if (rasGrp) {\n"
    "        rasGrp.position.set(unit.x, 2.5, unit.z);\n"
    "        arenaGroup.add(rasGrp);\n"
    "        vfxList.push({ mesh: rasGrp, age: 0, duration: 0.75, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });\n"
    "      }\n"
)

A2_ANC = (
    "      const giantRas = createRasenganMesh(2.2, 0xff3b00);\n"
    "      giantRas.position.set(ux, 2.8, uz);\n"
    "      arenaGroup.add(giantRas);\n"
    "      vfxList.push({ mesh: giantRas, age: 0, duration: 1.25, style: 'compound' });\n"
)
A2_NEW = (
    "      // W-VIS: giant_rasengan EXTRAIDO do APK bound a mao (forma na mao e explode,\n"
    "      // ~5.5u) — fallback procedural plantado se o extraido nao existir\n"
    "      const giantGrp = buildExtractedVfxMeshGroup(unit.heroId, 0xff3b00, 0.019, activeSkillVfxModel || 'giant_rasengan');\n"
    "      if (giantGrp) {\n"
    "        giantGrp.position.set(ux, 2.8, uz);\n"
    "        arenaGroup.add(giantGrp);\n"
    "        vfxList.push({ mesh: giantGrp, age: 0, duration: 1.25, style: 'compound', bindUnit: unit, bindBoneIdx: 13 });\n"
    "      } else {\n"
    "        const giantRas = createRasenganMesh(2.2, 0xff3b00);\n"
    "        giantRas.position.set(ux, 2.8, uz);\n"
    "        arenaGroup.add(giantRas);\n"
    "        vfxList.push({ mesh: giantRas, age: 0, duration: 1.25, style: 'compound' });\n"
    "      }\n"
)

A3_ANC = "duration: duration * 1.15, style: 'extracted'"
A3_NEW = "duration: duration * 1.7, style: 'extracted'"

A4_ANC = "window.__HITSTUN = { normal: 0.35, heavy: 0.60, source: 'APK storm: dmg0f media 21f, hsta0 36f' }; // telemetria E2E (W-HS)\n"
A4_NEW = A4_ANC + "window.__HAND_VFX = () => vfxList.filter(v => v.style === 'compound' && v.bindUnit).length; // telemetria E2E (W-VIS)\n"

PATCHES = [('P1-Q-rasengan-na-mao', A1_ANC, A1_NEW, 'replace'),
           ('P2-R-giant-na-mao', A2_ANC, A2_NEW, 'replace'),
           ('P3-extracted-duration', A3_ANC, A3_NEW, 'replace'),
           ('P4-telemetria', A4_ANC, A4_NEW, 'replace')]

# --- dry-run: valida TODAS as ancoras ANTES de gravar qualquer byte ---
fails = []
for name, anc, new, mode in PATCHES:
    n = src.count(anc)
    if n != 1:
        fails.append(f'  ancora "{name}" count={n} (esperado 1)')
if fails:
    print('DRY-RUN ABORTADO:'); print('\n'.join(fails)); sys.exit(1)
print('dry-run OK: 4 ancoras unicas')

# --- aplica ---
out = src
for name, anc, new, mode in PATCHES:
    out = out.replace(anc, new)
assert out != src and out.count('__HAND_VFX') == 1 and out.count('duration * 1.7') == 1
assert out.count("activeSkillVfxModel || 'rasengan'") == 1 and out.count("activeSkillVfxModel || 'giant_rasengan'") == 1

shutil.copyfile(P, P + '.bak_wvis')
data = out.replace('\n', eol).encode('utf-8') if eol == '\r\n' else out.encode('utf-8')
io.open(P, 'wb').write(data)
print('W-VIS APLICADO: rasengan/giant_rasengan do APK bound a mao durante o cast; extracted global dura 1.7x; telemetria __HAND_VFX')
