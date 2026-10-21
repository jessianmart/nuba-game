"""PV1-B fix1 — camada touch herda pointer-events:none do HUD overlay (pass-through).
O HUD usa pointer-events:none nos containers; a camada de INPUT touch precisa de auto.
Run: python pv1b_fix1_pointer_events.py   (cwd = repo root)
Backup: public/styles.css.bak_pv1b2
"""
import shutil


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


p = 'public/styles.css'
b = p + '.bak_pv1b2'
if not shutil.os.path.exists(b):
    shutil.copy2(p, b)
    print('[backup]', b)

c = rd(p)
ANCHOR = '/* ==== PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==== */'
assert c.count(ANCHOR) == 1
FIX = ANCHOR + """
/* FIX pv1b2: HUD overlays usam pointer-events:none (pass-through pro canvas) — heranca
   matava a zona do joystick. A camada de INPUT touch reativa explicitamente.
   Quando #touch-controls esta display:none, nada intercepta (desktop/lobby intactos). */
#touch-controls, #touch-joystick, #touch-cluster, .tbtn { pointer-events: auto; }"""
c = c.replace(ANCHOR, FIX, 1)
wr(p, c)
print('[ok] pointer-events: auto na camada touch (controls/joystick/cluster/botoes)')
