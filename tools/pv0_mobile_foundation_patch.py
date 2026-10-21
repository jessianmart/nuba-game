"""PV0 Mobile Foundation — viewport/safe-area, rotate overlay, device detect, INPUT state.

Fonte: docs/PIVOT_MOBILE.md (plano de pivotagem aprovado 2026-10-21).
Run:  python pv0_mobile_foundation_patch.py   (cwd = repo root goofy-mendeleev)
Backups: public/{game.js,index.html,styles.css}.bak_pv0
Zero mudanca de comportamento desktop: INPUT default 0/false e' aditivo.
"""
import os
import re
import shutil


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def backup(p):
    b = p + '.bak_pv0'
    if not os.path.exists(b):
        shutil.copy2(p, b)
        print('[backup]', b)


ok = []

# ---------------- game.js ----------------
g = rd('public/game.js')
backup('public/game.js')

assert 'window.INPUT' not in g, 'INPUT ja existe — revisar antes de prosseguir'
assert 'window.__DEVICE' not in g, '__DEVICE ja existe'

HEAD = "import * as THREE from 'three';\nwindow.THREE = THREE;\n"
assert g.count(HEAD) == 1, 'ancora HEAD do game.js nao bate'
DEV_BLOCK = HEAD + """
// ============================================================================
// PV0.2 DEVICE DETECTION + PV0.3 INPUT STATE (Mobile Foundation — docs/PIVOT_MOBILE.md)
// ============================================================================
window.__DEVICE = {
  isTouch: ('ontouchstart' in window) || (navigator.maxTouchPoints || 0) > 0,
  isMobile: /Android|iPhone|iPad|iPod|Mobile/i.test(navigator.userAgent) ||
            ((navigator.maxTouchPoints || 0) > 0 && Math.min(screen.width, screen.height) < 820),
  dpr: window.devicePixelRatio || 1
};
if (window.__DEVICE.isTouch) document.body.classList.add('touch');

// PV0.3: estado unico de input analogico — teclado E touch escrevem aqui (§2.4 do plano)
window.INPUT = {
  moveX: 0, moveZ: 0,                 // joystick analogico -1..1 (moveZ +1 = frente)
  aimX: 0, aimZ: 0, aimActive: false, // drag-aim manual (vetor unitario)
  fire: false                         // botao ATK touch segurado
};
"""
g = g.replace(HEAD, DEV_BLOCK, 1)

MOVE_ANCHOR = "  if (keys['KeyA'] || keys['ArrowLeft']) inputRight -= 1;"
assert g.count(MOVE_ANCHOR) == 1, 'ancora de movimento (keys ArrowLeft) nao bate'
g = g.replace(MOVE_ANCHOR, MOVE_ANCHOR + """
  // PV0.3: joystick analogico soma com as teclas digitais e clampa em [-1, 1]
  inputForward = Math.max(-1, Math.min(1, inputForward + (window.INPUT ? window.INPUT.moveZ : 0)));
  inputRight = Math.max(-1, Math.min(1, inputRight + (window.INPUT ? window.INPUT.moveX : 0)));""", 1)

FIRE_ANCHOR = "  if (mouseDown) executeSkill(u, 'atk');"
assert g.count(FIRE_ANCHOR) == 1, 'ancora de ataque (mouseDown atk) nao bate'
g = g.replace(
    FIRE_ANCHOR,
    "  if (mouseDown || (window.INPUT && window.INPUT.fire)) executeSkill(u, 'atk');",
    1,
)
wr('public/game.js', g)
ok.append('game.js: __DEVICE + body.touch + window.INPUT + merge joystick/fire')

# ---------------- index.html ----------------
i = rd('public/index.html')
backup('public/index.html')

VP_OLD = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />'
assert i.count(VP_OLD) == 1, 'ancora viewport nao bate'
VP_NEW = '<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover" />'
i = i.replace(VP_OLD, VP_NEW, 1)

assert 'id="rotate-overlay"' not in i
m = re.search(r'<body[^>]*>', i)
assert m, 'tag <body> nao encontrada'
OVERLAY = m.group(0) + """
  <!-- PV0: aviso de orientacao (landscape-only) — ver docs/PIVOT_MOBILE.md decisao #3 -->
  <div id="rotate-overlay" aria-hidden="true">
    <div class="rotate-phone"></div>
    <span class="rotate-text">GIRE O DISPOSITIVO</span>
    <span class="rotate-sub">O NUBA joga na horizontal — a vila e as arenas foram feitas para telas largas</span>
  </div>"""
i = i.replace(m.group(0), OVERLAY, 1)
wr('public/index.html', i)
ok.append('index.html: viewport-fit=cover + #rotate-overlay')

# ---------------- styles.css ----------------
c = rd('public/styles.css')
backup('public/styles.css')
assert 'PV0 MOBILE FOUNDATION' not in c
CSS_BLOCK = """

/* ==== PV0 MOBILE FOUNDATION (docs/PIVOT_MOBILE.md) ==== */
html, body { overscroll-behavior: none; }
#game-canvas { touch-action: none; }
body.touch button, body.touch .nav-tab { touch-action: manipulation; }
:root {
  --safe-top: env(safe-area-inset-top, 0px);
  --safe-bottom: env(safe-area-inset-bottom, 0px);
  --safe-left: env(safe-area-inset-left, 0px);
  --safe-right: env(safe-area-inset-right, 0px);
}

/* Aviso de orientacao: so aparece em PORTRAIT + touch (decisao #3 do plano) */
#rotate-overlay {
  display: none;
  position: fixed; inset: 0; z-index: 9999;
  background: #07090d;
  flex-direction: column; align-items: center; justify-content: center; gap: 16px;
}
#rotate-overlay .rotate-phone {
  width: 44px; height: 74px;
  border: 3px solid #f97316; border-radius: 9px;
  animation: nubaRotateHint 1.8s ease-in-out infinite;
}
#rotate-overlay .rotate-text { color: #f2f4f7; font-size: 21px; letter-spacing: 3px; font-weight: 600; }
#rotate-overlay .rotate-sub { color: #8b95a3; font-size: 12.5px; max-width: 320px; text-align: center; }
@keyframes nubaRotateHint { 0%, 15% { transform: rotate(0deg); } 55%, 100% { transform: rotate(-90deg); } }
@media (orientation: portrait) { body.touch #rotate-overlay { display: flex; } }
"""
c = c.rstrip() + '\n' + CSS_BLOCK
wr('public/styles.css', c)
ok.append('styles.css: bloco MOBILE FOUNDATION (overscroll, touch-action, safe-area, rotate overlay)')

print('\n'.join('[ok] ' + s for s in ok))
print('\nPV0 PATCH APPLIED. Proximo: node --check public/game.js && bateria (verify + suite).')
