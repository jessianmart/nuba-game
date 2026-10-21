# -*- coding: utf-8 -*-
"""SPAWN GUARD: imortalidade curta (4s) perto da propria base perto de spawn/respawn,
mitiga spawn trap; atacar quebra a propria protecao. Rollback: *.bak_spawnguard"""
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
        print('  [OK] append')
    shutil.copyfile(path, path + '.bak_spawnguard')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

CSS = """
/* ==================== SPAWN GUARD: brilho dourado no rotulo enquanto imortal ==================== */
.unit-label.shielded {
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.85), 0 0 16px rgba(251, 191, 36, 0.55);
}
"""

ok = True
ok &= apply('public/index.html', [('cache-bust game v29', 'game.js?v=28', 'game.js?v=29')])
ok &= apply('public/game.js', [
    ('shield no spawn inicial',
     '        deadTimer: 0,',
     '        deadTimer: 0,\n        spawnShield: 4.0, // SPAWN GUARD: imortalidade curta perto da base'),
    ('bloqueio de dano + quebra ao atacar',
     '  if (target.deadTimer > 0) return;',
     '  if (target.deadTimer > 0) return;\n'
     '  if (target.spawnShield > 0) { // SPAWN GUARD: imortal perto da propria base\n'
     '    const _sgp = basePos(target.team);\n'
     '    if (Math.hypot(target.x - _sgp.x, target.z - _sgp.z) < 16) return;\n'
     '  }\n'
     '  attacker.spawnShield = 0; // atacar quebra a propria protecao'),
    ('shield no respawn + anel dourado',
     '      if (u.deadTimer <= 0) {\n        u.hp = u.maxHp;',
     '      if (u.deadTimer <= 0) {\n        u.spawnShield = 4.0; // SPAWN GUARD\n'
     '        spawnVFX(u.x, 1.0, u.z, 0xfbbf24, 3.4, 0.55, \'ring\', u.heroId);\n'
     '        u.hp = u.maxHp;'),
    ('decay do shield (dt real)',
     '    if (u.deadTimer <= 0 && Math.hypot(u.x - bx, u.z - bz) < 14.5) {',
     '    if (u.spawnShield > 0) u.spawnShield = Math.max(0, u.spawnShield - dt); // SPAWN GUARD\n'
     '    if (u.deadTimer <= 0 && Math.hypot(u.x - bx, u.z - bz) < 14.5) {'),
    ('brilho no rotulo enquanto imortal',
     '    if (u.deadTimer <= 0) {\n      const hpFill = u.labelEl.querySelector(\'.u-hp-fill\');',
     '    if (u.deadTimer <= 0) {\n      u.labelEl.classList.toggle(\'shielded\', u.spawnShield > 0); // SPAWN GUARD\n'
     '      const hpFill = u.labelEl.querySelector(\'.u-hp-fill\');'),
], append=CSS)
print('SPAWN GUARD:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
