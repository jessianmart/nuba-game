"""W8: equalizacao de mix — voz/skills/musica no mesmo patamar PERCEBIDO,
com degraus reais (medicao RMS: musica -14dB, skills -16.6dB picos -9.2,
voz -15.8dB). Problema raiz: boost 1.4x no playAt saturava voz/tombo/cast
NO MESMO CLAMP (play faz master x min(falloff*boost*cue, 1)).
Plano (audio eff = master 0.85 x cue):
  voz 0.92 -> 0.78 (referencia) | ground 0.90 -> 0.765 | cast 0.80 -> 0.68
  melee 0.62->0.80 | hit_s 0.55->0.70 | kunai 0.70 | sword 0.45/0.6->0.65
  musica: menu 0.385 (mantém, ~12dB abaixo) | battle 0.38->0.55 baseVol
Eff. batalha: 0.55 x musicVol 0.55 = 0.3025 (audivel sem brigar).
"""
import shutil
import subprocess


def apply_edits(path, edits):
    shutil.copy2(path, path + '.bak_w8')
    s = open(path, encoding='utf-8', newline='').read()
    n = 0
    for old, new in edits:
        done = False
        for sep in ('\r\n', '\n'):
            o, nn = old.replace('\n', sep), new.replace('\n', sep)
            if s.count(o) == 1:
                s = s.replace(o, nn, 1)
                n += 1
                done = True
                break
        if not done:
            c = sum(s.count(old.replace('\n', sep)) for sep in ('\r\n', '\n'))
            raise SystemExit(f'ANCORA FALHOU em {path} (edit {n+1}, count={c}): {old[:70]!r}')
    open(path, 'w', encoding='utf-8', newline='').write(s)
    return n


EDITS = [
    # 1. falloff: boost 1.4 -> 1.0 (headroom — saturava os canais no mesmo clamp)
    ("    const v = Math.pow(1 - Math.min(d / 60, 1), 1.2) * 1.4 * base;",
     "    const v = Math.pow(1 - Math.min(d / 60, 1), 1.2) * base; // W8: boost 1.4->1.0 (equalizacao)"),
    # 2. voz do heroi: referencia do mix (leve reducao pra skills subirem com headroom)
    ("  const played = AUTH_SFX.playAt('voice/' + u.heroId + '/' + cue, u.x, u.z, { vol: (opts && opts.vol) || 0.95 });",
     "    const played = AUTH_SFX.playAt('voice/' + u.heroId + '/' + cue, u.x, u.z, { vol: (opts && opts.vol) || 0.92 }); // W8"),
    # 3-4. hit pequeno e tombo pesado
    ("  AUTH_SFX.playAt('hit_s', target.x, target.z, { vol: 0.55 }); // W5: impacto posicionado",
     "  AUTH_SFX.playAt('hit_s', target.x, target.z, { vol: 0.7 }); // W8"),
    ("  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.85, min: 260 }); // W5: tombo pesado autêntico",
     "  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.9, min: 260 }); // W8"),
    # 5. melee soco/chute — maior gap: 0.62 empatava 3dB abaixo da voz
    ("        AUTH_SFX.playAt(hitIdx === 2 ? AUTH_SFX.pick('kick_hit', 'kick_hit2') : AUTH_SFX.pick('punch_hit', 'punch_hit2'), meleeTarget.x, meleeTarget.z, { vol: 0.62 }); // W5: soco/chute autêntico com variação",
     "        AUTH_SFX.playAt(hitIdx === 2 ? AUTH_SFX.pick('kick_hit', 'kick_hit2') : AUTH_SFX.pick('punch_hit', 'punch_hit2'), meleeTarget.x, meleeTarget.z, { vol: 0.8 }); // W8: soco/chute no patamar do mix"),
    # 6-7. sword hit (dois hooks, cada um com seu valor)
    ("      try { AUTH_SFX.play('sword_hit', { vol: 0.45 }); } catch (e) {}",
     "      try { AUTH_SFX.play('sword_hit', { vol: 0.65 }); } catch (e) {} // W8"),
    ("  try { AUTH_SFX.play('sword_hit', { vol: 0.6 }); } catch (e) {}",
     "  try { AUTH_SFX.play('sword_hit', { vol: 0.65 }); } catch (e) {} // W8"),
    # 8. musica de batalha: baseVol 0.38 -> 0.55 (eff 0.3025 — audivel, ~8dB abaixo da voz)
    ("  baseVol: { menu: 0.7, battle: 0.38 },",
     "  baseVol: { menu: 0.7, battle: 0.55 }, // W8: equalizado (eff 0.55 x musicVol)"),
]
n = apply_edits('public/game.js', EDITS)
print(f'game.js: {n}/{len(EDITS)} edicoes')

chk = open('public/game.js', encoding='utf-8', newline='').read()
assert chk.count('W8') >= 7, chk.count('W8')
assert 'baseVol: { menu: 0.7, battle: 0.55 }' in chk.replace('\r\n', '\n')
r = subprocess.run(['node', '--check', 'public/game.js'], capture_output=True, text=True)
assert r.returncode == 0, r.stderr[:400]
print('node --check OK — W8 MIX BALANCE COMPLETO')
