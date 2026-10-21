# -*- coding: utf-8 -*-
"""PV1c: adota o DOM/CSS touch dos agentes (ids joystick-base/knob, .tbtn com icones
do skin, .active) e rewira o JS. (1) index: remove os 2 blocos duplicados meus;
(2) styles: remove meu bloco CSS PV1 (o CSS deles ja tem tudo, inclusive
pointer-events); (3) game.js: ids deles + chakra hold + pressed visual.
Rollback: *.bak_pv1c"""
import io, sys, shutil

def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {path}:{name}')
    shutil.copyfile(path, path + '.bak_pv1c')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

def cut_lines(path, start_marker, end_marker, keep_start, name):
    """Deleta linhas [start_marker .. end_marker) ou (.. ] conforme keep flags.
    keep_start=True: mantem a linha start_marker, deleta ate (excl.) end_marker."""
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    lines = src.replace('\r\n', '\n').split('\n')
    si = next(i for i, l in enumerate(lines) if start_marker in l)
    ei = next(i for i in range(si + 1, len(lines)) if end_marker in lines[i])
    del lines[si + (1 if keep_start else 0):ei]
    shutil.copyfile(path, path + '.bak_pv1c')
    io.open(path, 'w', encoding='utf-8', newline='').write(eol.join(lines) if eol == '\r\n' else '\n'.join(lines))
    print(f'  [OK] {path}:{name} (linhas {si}..{ei} removidas)')
    return True

ok1 = cut_lines('public/index.html',
    '<div id="hud-screen" class="screen">',
    '<!-- Top Bar: 5v5 MOBA Scoreboard & Timer Strip -->',
    True, 'remover os 2 blocos touch duplicados (meus)')

ok2 = cut_lines('public/styles.css',
    '/* ==================== PV1 TOUCH CONTROLS (docs/PIVOT_MOBILE.md',
    'escondidos no touch */',
    False, 'remover bloco CSS PV1 meu (o dos agentes prevalece)')

ok3 = apply('public/game.js', [
    ('joystick: ids do DOM dos agentes',
     "  const base = document.getElementById('touch-joystick-base');\n  const knob = document.getElementById('touch-joystick-knob');",
     "  const base = document.getElementById('joystick-base');\n  const knob = document.getElementById('joystick-knob');"),
    ('joystick: classe visual .active (CSS deles)',
     "  ox = e.clientX; oy = e.clientY; // spawn flutuante no toque\n  joy.classList.add('live');",
     "  ox = e.clientX; oy = e.clientY; // spawn flutuante no toque\n  joy.classList.add('active');"),
    ('joystick: release .active',
     "  joyId = null; joy.classList.remove('live');",
     "  joyId = null; joy.classList.remove('active');"),
    ('cluster: mapa .tbtn -> slots (DOM deles)',
     "  document.querySelectorAll('#touch-cluster .tc-btn').forEach((btn) => {\n    const slot = btn.dataset.slot;",
     "  const TBTN_SLOT = { 'tbtn-atk': 'atk', 'tbtn-q': 'q', 'tbtn-w': 'w', 'tbtn-e': 'e', 'tbtn-r': 'r', 'tbtn-c': 'chakra' };\n  document.querySelectorAll('#touch-cluster .tbtn').forEach((btn) => {\n    const slot = TBTN_SLOT[btn.id];\n    if (!slot) return;"),
    ('cluster: pressed visual no touch',
     "    btn.addEventListener('pointerdown', (e) => {\n      e.preventDefault();\n      if (!matchActive) return;",
     "    btn.addEventListener('pointerdown', (e) => {\n      e.preventDefault();\n      btn.classList.add('pressed');\n      if (!matchActive) return;"),
    ('cluster: hold chakra (consumo ja existe em charging L5126)',
     "      if (slot === 'atk') window.INPUT.fire = true; // segurar = combo (consumido em updatePlayerUnit)\n      else executeSkill(player, slot);",
     "      if (slot === 'atk') window.INPUT.fire = true; // segurar = combo (consumido em updatePlayerUnit)\n      else if (slot === 'chakra') window.INPUT.chakra = true; // concentrar chakra (F touch)\n      else executeSkill(player, slot);"),
    ('cluster: release chakra + pressed off',
     "    const fireEnd = () => { if (slot === 'atk') window.INPUT.fire = false; };",
     "    const fireEnd = () => { if (slot === 'atk') window.INPUT.fire = false; if (slot === 'chakra') window.INPUT.chakra = false; btn.classList.remove('pressed'); };"),
])

print('PV1c:', 'APLICADO' if (ok1 and ok2 and ok3) else 'ABORTADO')
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
