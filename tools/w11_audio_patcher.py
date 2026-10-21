# -*- coding: utf-8 -*-
"""W1.1 ÁUDIO AUTÊNTICO: AudioBank (48 cues do Storm) + SKILL_SFX_MAP por herói
+ hooks (UI, match flow, combate, skills, awakening, morte, level).
Aditivo: sons só SOMAM ao procedural existente (fallback intacto). Rollback: *.bak_w11"""
import io, sys, shutil
def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {name}')
    shutil.copyfile(path, path + '.bak_w11')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

CORE = '''const sfx = new SoundFX();

// ==================== W1.1 ÁUDIO AUTÊNTICO (banks CRIWARE ACB do Storm) ====================
// 48 cues extraídas com tools/extract_audio.py -> public/assets/audio/decoded/*.ogg
const SKILL_SFX_MAP = {
  '1nrt': { q: 'rasen', w: 'zanei_open', e: 'shunshin', r: 'oogi' },
  '1ssk': { q: 'chidori', w: 'goukakyu', e: 'shunshin', r: 'oogi' },
  '1skr': { q: 'senpu', w: 'sabaku', e: 'shunshin', r: 'oogi' },
  '1kks': { q: 'raikiri', w: 'goheki', e: 'shunshin', r: 'oogi' },
  '1roc': { q: 'reppu', w: 'senpu', e: 'shunshin', r: 'oogi' },
  '1itc': { q: 'genjyutu', w: 'crow1', e: 'itachi_eye', r: 'oogi' },
  '1gar': { q: 'sabaku', w: 'gaara_sandhit', e: 'sabaku', r: 'oogi' },
  '1hnt': { q: 'housenka', w: 'byakugan', e: 'housenka', r: 'oogi' },
  '1nej': { q: 'kaiten', w: 'hakke_hit', e: 'kaiten', r: 'oogi' },
  '1jry': { q: 'goheki', w: 'fire_lp', e: 'shunshin', r: 'oogi' }
};
const AUTH_SFX = {
  bank: {}, log: [], volume: 0.85, _last: {},
  THROTTLE: { ko: 450, down: 250, dash: 220, hit_s: 90, punch_hit: 110, kick_hit: 110, menu_slct: 60 },
  preload(name) {
    if (this.bank[name]) return this.bank[name];
    try { const a = new Audio('assets/audio/decoded/' + name + '.ogg'); a.preload = 'auto'; this.bank[name] = a; } catch (e) {}
    return this.bank[name] || null;
  },
  play(name, opts) {
    if (sfx.enabled === false) return false;
    const now = performance.now();
    const min = (opts && opts.min) || this.THROTTLE[name] || 70;
    if (this._last[name] && now - this._last[name] < min) return false;
    const a = this.preload(name);
    if (!a) return false;
    try { a.currentTime = 0; a.volume = this.volume * ((opts && opts.vol) || 1); const p = a.play(); if (p && p.catch) p.catch(function () {}); } catch (e) {}
    this._last[name] = now;
    this.log.push(name); if (this.log.length > 14) this.log.shift();
    return true;
  }
};
window.AUTH_SFX = AUTH_SFX; // W1.1: validação E2E
window.SKILL_SFX_MAP = SKILL_SFX_MAP;
(function () { const _cl = sfx.clink.bind(sfx); sfx.clink = function () { AUTH_SFX.play('menu_slct', { vol: 0.65 }); _cl(); }; })(); // W1.1: cliques de UI'''

ok = apply('public/game.js', [
    ('core AudioBank + mapa por heroi',
     'const sfx = new SoundFX();',
     CORE),
    ('executeSkill: som por skill',
     '  activeSkillVfxAnim = ((SKILL_VFX_ANIM[unit.heroId] || {})[slot]) || null; // SPP: anim por skill',
     '  activeSkillVfxAnim = ((SKILL_VFX_ANIM[unit.heroId] || {})[slot]) || null; // SPP: anim por skill\n'
     "  const _authSfx = ((SKILL_SFX_MAP[unit.heroId] || {})[slot]) || null; // W1.1\n"
     "  if (_authSfx) AUTH_SFX.play(_authSfx, { vol: 0.8 });\n"
     "  else if (slot === 'atk') AUTH_SFX.play('punch_swing', { vol: 0.5 });"),
    ('dealDamage: hit autentico (com contexto único)',
     '  // Synchronized SFX on damage impact\n  sfx.hit();',
     '  // Synchronized SFX on damage impact\n  sfx.hit();\n  AUTH_SFX.play(\'hit_s\', { vol: 0.55 }); // W1.1'),
    ('morte: down + ko',
     '    target.deadTimer = 6.0; // 6s respawn countdown total',
     '    target.deadTimer = 6.0; // 6s respawn countdown total\n'
     "    AUTH_SFX.play('down', { vol: 0.8 }); AUTH_SFX.play('ko', { vol: 0.9 }); // W1.1"),
    ('level up',
     '    attacker.level = Math.min(10, attacker.level + 1);',
     '    attacker.level = Math.min(10, attacker.level + 1);\n'
     "    AUTH_SFX.play('level_up', { vol: 0.75 }); // W1.1"),
    ('awakening',
     '    unit.awakenedTimer = 14.0; // 14 seconds of Awakening Mode!',
     '    unit.awakenedTimer = 14.0; // 14 seconds of Awakening Mode!\n'
     "    AUTH_SFX.play('awake_open', { vol: 0.9 }); AUTH_SFX.play('awake_flash', { vol: 0.8 }); // W1.1"),
    ('dash',
     "    unit.state = 'dash';",
     "    unit.state = 'dash';\n    AUTH_SFX.play('dash', { vol: 0.5 }); // W1.1"),
    ('prorrogacao = tempo esgotado',
     '      matchTimeRemaining = 60; // T5: prorrogacao de 1 minuto',
     '      matchTimeRemaining = 60; // T5: prorrogacao de 1 minuto\n'
     "      AUTH_SFX.play('time_up', { vol: 0.9 }); // W1.1"),
    ('fim de partida: result',
     '  if (matchActive) recordMatchResult(win);',
     '  if (matchActive) recordMatchResult(win);\n'
     "  AUTH_SFX.play('result', { vol: 0.9 }); // W1.1"),
    ('troca de aba do lobby',
     '  const target = LOBBY_PAGES.includes(page) ? page : \'play\';\n  lobbyPage = target;',
     '  const target = LOBBY_PAGES.includes(page) ? page : \'play\';\n  lobbyPage = target;\n'
     "  AUTH_SFX.play('page_slct', { vol: 0.7 }); // W1.1"),
    ('arena chip: stage_change',
     '      sfx.click ? sfx.click() : sfx.hit();',
     '      sfx.click ? sfx.click() : sfx.hit();\n'
     "      AUTH_SFX.play('stage_change', { vol: 0.75 }); // W1.1"),
    ('combo taijutsu autentico',
     '      if (unit.isPlayer) {\n        if (hitIdx === 2) sfx.kick();\n        else { sfx.hit(); if (hitIdx === 3) sfx.kick(); }\n      }',
     '      if (unit.isPlayer) {\n        if (hitIdx === 2) sfx.kick();\n        else { sfx.hit(); if (hitIdx === 3) sfx.kick(); }\n'
     "        AUTH_SFX.play(hitIdx === 2 ? 'kick_hit' : 'punch_hit', { vol: 0.6 }); // W1.1\n"
     '      }'),
    ('inicio de partida: battle_start',
     '  for (const c of shadowClones) { try { arenaGroup.remove(c.mesh); } catch (e) {} } // SPP',
     '  for (const c of shadowClones) { try { arenaGroup.remove(c.mesh); } catch (e) {} } // SPP\n'
     "  AUTH_SFX.play('battle_start', { vol: 0.9 }); // W1.1"),
])
print('W1.1:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
