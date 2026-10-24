"""W5-F2 patcher: vozes de batalha POR HERÓI (PL_1XXX do APK) no game.js.
5 edições: infra (HERO_VOICE_MAP + unitVoice com gate por unidade),
voz de dano na vítima (dealDamage), gemido de KO no kill, voz de ataque
no cast (executeSkill), grito de despertar no awakening.
Anchor único por edição, CRLF/LF detectado por região, backup .bak_w5f2,
autoverificação de marcadores + node --check.
"""
import shutil
import subprocess

P = 'public/game.js'
shutil.copy2(P, P + '.bak_w5f2')
s = open(P, encoding='utf-8', newline='').read()
edits = 0


def rep(old, new):
    global s, edits
    for sep in ('\r\n', '\n'):
        o = old.replace('\n', sep)
        if s.count(o) == 1:
            s = s.replace(o, new.replace('\n', sep), 1)
            edits += 1
            return
    raise SystemExit(f'ANCORA FALHOU ({edits+1}): {old[:60]!r}')


INFRA = """
// W5-F2: vozes de batalha POR HERÓI — bancos PL_1XXX do APK (21 cues/ninja:
// dano leve/médio/pesado, ataque leve/médio/ult, combo, despertar). Gate por
// unidade (1 voz/1.7s padrão), bots 45% mais esparsos, volume pelo playAt.
const VOICE_CUE_SETS = {
  dmg_s: ['S_PL_DmgS1', 'S_PL_DmgS2', 'S_PL_DmgS3'],
  dmg_m: ['S_PL_DmgM1', 'S_PL_DmgM2'],
  dmg_l: ['S_PL_DmgL1', 'S_PL_DmgL2'],
  atk_s: ['S_PL_AtkS1', 'S_PL_AtkS2', 'S_PL_AtkS3'],
  atk_m: ['S_PL_AtkM1', 'S_PL_AtkM2'],
  atk_l: ['S_PL_AtkL1', 'S_PL_AtkL2'],
  combo: ['S_PL_Combo1', 'S_PL_Combo2', 'S_PL_Combo3'],
  awake: ['S_PL_Awake'],
  catch: ['S_PL_Catch'],
  grdb: ['S_PL_GrdBrk1', 'S_PL_GrdBrk2'],
};
window.HERO_VOICE_MAP = {};
['1nrt', '1ssk', '1skr', '1kks', '1roc', '1itc', '1gar', '1hnt', '1nej', '1jry', '1tnd', '1orc'].forEach(function (id) { window.HERO_VOICE_MAP[id] = VOICE_CUE_SETS; });
window._voiceGate = {};
window.unitVoice = function (u, kind, opts) {
  if (!u || !u.heroId || !window.HERO_VOICE_MAP[u.heroId]) return false;
  if (!u.isPlayer && Math.random() < 0.45) return false;
  const set = window.HERO_VOICE_MAP[u.heroId][kind];
  if (!set || !set.length) return false;
  const now = performance.now();
  const min = (opts && opts.min !== undefined) ? opts.min : 1700;
  const key = u.id || u.heroId;
  if (window._voiceGate[key] && now - window._voiceGate[key] < min) return false;
  AUTH_SFX._vAlt = (AUTH_SFX._vAlt || 0) + 1;
  const cue = set[AUTH_SFX._vAlt % set.length];
  const played = AUTH_SFX.playAt('voice/' + u.heroId + '/' + cue, u.x, u.z, { vol: (opts && opts.vol) || 0.95 });
  if (played) window._voiceGate[key] = now;
  return played;
}; // W5-F2"""

# E1: infra apos o export do SKILL_SFX_MAP
rep('window.SKILL_SFX_MAP = SKILL_SFX_MAP;',
    'window.SKILL_SFX_MAP = SKILL_SFX_MAP;\n' + INFRA)

# E2: voz de dano na vitima (dealDamage, apos hit_s/ground_hit)
rep("  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.85, min: 260 }); // W5: tombo pesado autêntico",
    "  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.85, min: 260 }); // W5: tombo pesado autêntico\n"
    "  window.unitVoice(target, dmg >= 180 ? 'dmg_m' : 'dmg_s'); // W5-F2: voz do herói ao levar dano")

# E3: gemido de KO no kill
rep("    AUTH_SFX.playAt('down', target.x, target.z, { vol: 0.8 }); AUTH_SFX.playAt('ko', target.x, target.z, { vol: 0.9 }); // W5: KO posicionado",
    "    AUTH_SFX.playAt('down', target.x, target.z, { vol: 0.8 }); AUTH_SFX.playAt('ko', target.x, target.z, { vol: 0.9 }); // W5: KO posicionado\n"
    "    window.unitVoice(target, 'dmg_l', { min: 0 }); // W5-F2: gemido de queda do herói")

# E4: voz de ataque no cast
rep("  const _authSfx = ((SKILL_SFX_MAP[unit.heroId] || {})[slot]) || null; // W1.1",
    "  const _authSfx = ((SKILL_SFX_MAP[unit.heroId] || {})[slot]) || null; // W1.1\n"
    "  window.unitVoice(unit, slot === 'atk' ? 'atk_s' : (slot === 'r' ? 'atk_l' : 'atk_m'), { min: 4200 }); // W5-F2: voz de ataque do herói")

# E5: grito de despertar
rep("    AUTH_SFX.playAt('awake_open', unit.x, unit.z, { vol: 0.9 }); AUTH_SFX.playAt('awake_flash', unit.x, unit.z, { vol: 0.8 }); // W5: awakening posicionado",
    "    AUTH_SFX.playAt('awake_open', unit.x, unit.z, { vol: 0.9 }); AUTH_SFX.playAt('awake_flash', unit.x, unit.z, { vol: 0.8 }); // W5: awakening posicionado\n"
    "    window.unitVoice(unit, 'awake', { min: 0 }); // W5-F2: grito de despertar do herói")

open(P, 'w', encoding='utf-8', newline='').write(s)
print(f'{edits}/5 edições aplicadas')

chk = open(P, encoding='utf-8', newline='').read()
n = chk.count('W5-F2')
assert n >= 6, f'marcadores W5-F2: {n}'
assert 'unitVoice' in chk and chk.count('unitVoice(') >= 5
r = subprocess.run(['node', '--check', P], capture_output=True, text=True)
assert r.returncode == 0, r.stderr[:400]
print(f'node --check OK — marcadores W5-F2: {n}')
