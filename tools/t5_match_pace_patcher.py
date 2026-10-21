# -*- coding: utf-8 -*-
"""T5 MATCH PACE: HP x1.5 + dano x0.9 (TTK ~1.67x mais longo) + prorrogacao de 1 min no
empate + morte subita apos prorrogacao empatada. Rollback: *.bak_t5"""
import io, sys, shutil

def apply(path, patches, append=None):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {name}')
    if append:
        s = s.rstrip('\n') + '\n' + append
        print('  [OK] append CSS')
    shutil.copyfile(path, path + '.bak_t5')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

CSS = """
/* ==================== T5: PRORROGAcao — timer em destaque ==================== */
#match-timer.overtime {
  color: #f97316 !important;
  filter: drop-shadow(0 0 10px rgba(249, 115, 22, 0.85));
}
#match-timer.sudden {
  color: #ef4444 !important;
  filter: drop-shadow(0 0 10px rgba(239, 68, 68, 0.9));
  animation: t5-pulse 0.9s ease-in-out infinite;
}
@keyframes t5-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.55; } }
"""

ok = True
ok &= apply('public/index.html', [
    ('cache-bust game v31', 'game.js?v=30', 'game.js?v=31'),
    ('cache-bust styles v18', 'styles.css?v=17', 'styles.css?v=18'),
])
ok &= apply('public/styles.css', [], append=CSS)
ok &= apply('public/game.js', [
    ('estado T5 + escalas globais',
     'let matchTimeRemaining = 300; // 5:00',
     'let matchTimeRemaining = 300; // 5:00\n'
     'let matchOvertime = false; // T5: prorrogacao de 1 min no empate\n'
     'let matchSuddenDeath = false; // T5: morte subita apos prorrogacao empatada\n'
     'const HERO_HP_SCALE = 1.5; // T5: resistencia geral — HP x1.5 (demora mais a matar)\n'
     'const HERO_DMG_SCALE = 0.9; // T5: dano global x0.9'),
    ('HP escalado no spawn',
     '        hp: hs.hp,\n        maxHp: hs.hp,',
     '        hp: Math.round(hs.hp * HERO_HP_SCALE), // T5\n'
     '        maxHp: Math.round(hs.hp * HERO_HP_SCALE), // T5'),
    ('dano global escalado',
     "  const dmg = Math.max(1, Math.round(dmgRaw * ((HERO_STATS[target.heroId] || HERO_STATS.__d).dr))); // P2: dano recebido por heroi",
     "  const dmg = Math.max(1, Math.round(dmgRaw * HERO_DMG_SCALE * ((HERO_STATS[target.heroId] || HERO_STATS.__d).dr))); // T5 escala global + P2 dano por heroi"),
    ('prorrogacao + morte subita no timer',
     "  if (matchTimeRemaining <= 0) {\n    endMatch(scoreBlue >= scoreRed ? 'FIM DE TEMPO — VITÓRIA TIME AZUL!' : 'FIM DE TEMPO — VITÓRIA TIME VERMELHO!');\n    return;\n  }",
     '  if (matchSuddenDeath) {\n'
     '    // T5 MORTE SUBITA: timer congelado — o proximo abate decide\n'
     '  } else if (matchTimeRemaining <= 0) {\n'
     "    if (scoreBlue === scoreRed && !matchOvertime) {\n"
     '      matchOvertime = true;\n'
     '      matchTimeRemaining = 60; // T5: prorrogacao de 1 minuto\n'
     "      showBanner('PRORROGAÇÃO! 1 MINUTO PARA DESEMPATAR', 2400);\n"
     "      const _mt = document.getElementById('match-timer');\n"
     "      if (_mt) _mt.classList.add('overtime');\n"
     '      return;\n'
     '    }\n'
     '    if (scoreBlue === scoreRed) {\n'
     '      matchSuddenDeath = true; // T5: empatou a prorrogacao — morte subita\n'
     "      showBanner('MORTE SÚBITA! O PRÓXIMO ABATE VENCE', 2400);\n"
     "      const _mt2 = document.getElementById('match-timer');\n"
     "      if (_mt2) _mt2.classList.add('sudden');\n"
     '      return;\n'
     '    }\n'
     "    endMatch(scoreBlue > scoreRed ? 'FIM DE TEMPO — VITÓRIA TIME AZUL!' : 'FIM DE TEMPO — VITÓRIA TIME VERMELHO!');\n"
     '    return;\n'
     '  }'),
    ('morte subita decide no abate',
     "    if (scoreBlue >= TARGET_KILLS || scoreRed >= TARGET_KILLS) {\n      endMatch(scoreBlue >= TARGET_KILLS ? 'VITÓRIA DO TIME KONOHA AZUL!' : 'VITÓRIA DO TIME RIVAL VERMELHO!');\n    }",
     "    if (matchSuddenDeath) {\n"
     "      endMatch(scoreBlue > scoreRed ? 'MORTE SÚBITA — VITÓRIA TIME AZUL!' : 'MORTE SÚBITA — VITÓRIA TIME VERMELHO!'); // T5\n"
     "    } else if (scoreBlue >= TARGET_KILLS || scoreRed >= TARGET_KILLS) {\n"
     "      endMatch(scoreBlue >= TARGET_KILLS ? 'VITÓRIA DO TIME KONOHA AZUL!' : 'VITÓRIA DO TIME RIVAL VERMELHO!');\n"
     '    }'),
    ('reset T5 no start5v5Match',
     '  matchTimeRemaining = 300;',
     '  matchTimeRemaining = 300;\n'
     '  matchOvertime = false; // T5\n'
     '  matchSuddenDeath = false; // T5\n'
     "  const _mtReset = document.getElementById('match-timer');\n"
     "  if (_mtReset) _mtReset.classList.remove('overtime', 'sudden');"),
    ('expose __matchState para debug/teste',
     'window.HERO_STATS = HERO_STATS; // P2 (validacao)',
     'window.HERO_STATS = HERO_STATS; // P2 (validacao)\n'
     'window.__matchState = {\n'
     '  get time() { return matchTimeRemaining; },\n'
     '  set time(v) { matchTimeRemaining = Math.max(0, v); },\n'
     '  get overtime() { return matchOvertime; },\n'
     '  get suddenDeath() { return matchSuddenDeath; },\n'
     '  get blue() { return scoreBlue; },\n'
     '  get red() { return scoreRed; }\n'
     '}; // T5 (debug/teste)'),
])
print('T5 MATCH PACE:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
