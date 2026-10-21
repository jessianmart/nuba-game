"""PV1-B — Controles touch: joystick flutuante + cluster de skills + auto-aim (docs/PIVOT_MOBILE.md §2.4).

- #touch-controls (aditivo, dentro do #hud-screen): joystick esq. + 6 botoes dir.
- Joystick escreve window.INPUT.moveX/moveZ (merged no PV0); ATK segura INPUT.fire.
- Skills: tap = executeSkill com auto-aim (findAimTarget + facing lock).
- Chakra hold: INPUT.chakra merge na linha de charge (F17).
- Visivel SOMENTE com body.touch + partida ativa (CSS gate) — desktop intocado.
- Câmera: moba follow-cam já e' estilo Brawl (decisao registrada no plano) — zero mudanca.

Run:  python pv1b_touch_controls_patch.py   (cwd = repo root)
Backups: public/{game.js,index.html,styles.css}.bak_pv1b
"""
import os
import shutil


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def backup(p, tag):
    b = p + '.bak_' + tag
    if not os.path.exists(b):
        shutil.copy2(p, b)
        print('[backup]', b)


def sub1(text, old, new, what):
    n = text.count(old)
    assert n == 1, f'{what}: esperava 1 ocorrencia, achei {n}'
    return text.replace(old, new, 1)


ok = []

# ================= index.html =================
i = rd('public/index.html')
backup('public/index.html', 'pv1b')
assert 'id="touch-controls"' not in i
ANCHOR = '''            <div class="ability-body">
              <span class="ability-name">Chakra</span>
              <span class="ability-cost">+32 CK/s</span>
            </div>
          </button>
        </div>
      </div>'''
TOUCH_HTML = ANCHOR + '''

          <!-- PV1.3/PV1.4: controles touch (docs/PIVOT_MOBILE.md §2.4) — visível só em body.touch + partida -->
          <div id="touch-controls">
            <div id="touch-joystick"><div id="joystick-base"></div><div id="joystick-knob"></div></div>
            <div id="touch-cluster">
              <button type="button" class="tbtn tbtn-r" id="tbtn-r" aria-label="Ougi Supremo"><img src="assets/ui/skin/icon_r.png" alt="R"></button>
              <button type="button" class="tbtn tbtn-c" id="tbtn-c" aria-label="Concentrar Chakra"><img src="assets/ui/skin/icon_c.png" alt="F"></button>
              <button type="button" class="tbtn tbtn-q" id="tbtn-q" aria-label="Ninjutsu Primário"><img src="assets/ui/skin/icon_q.png" alt="Q"></button>
              <button type="button" class="tbtn tbtn-e" id="tbtn-e" aria-label="Kawarimi"><img src="assets/ui/skin/icon_e.png" alt="ESPAÇO"></button>
              <button type="button" class="tbtn tbtn-w" id="tbtn-w" aria-label="Ninjutsu Secundário"><img src="assets/ui/skin/icon_w.png" alt="E"></button>
              <button type="button" class="tbtn tbtn-atk" id="tbtn-atk" aria-label="Ataque Básico"><img src="assets/ui/skin/icon_atk.png" alt="ATK"></button>
            </div>
          </div>'''
i = sub1(i, ANCHOR, TOUCH_HTML, 'touch controls html')
wr('public/index.html', i)
ok.append('index.html: #touch-controls (joystick + cluster)')

# ================= game.js =================
g = rd('public/game.js')
backup('public/game.js', 'pv1b')

# 1. INPUT ganha campo chakra
g = sub1(
    g,
    '  fire: false                         // botao ATK touch segurado\n};',
    '''  fire: false,                        // botao ATK touch segurado
  chakra: false                       // botao de concentrar chakra segurado (PV1.4)
};''',
    'INPUT.chakra field')

# 2. merge do chakra hold na linha de charge (F17 keyboard intocado)
g = sub1(
    g,
    "  const charging = keys['ShiftLeft'] || keys['ShiftRight'] || keys['KeyF'];",
    "  const charging = keys['ShiftLeft'] || keys['ShiftRight'] || keys['KeyF'] || (window.INPUT && window.INPUT.chakra);",
    'chakra charge merge')

# 3. bloco touch no fim do arquivo (mesmo escopo de modulo: units/executeSkill/matchActive)
assert 'initTouchControls' not in g
TOUCH_JS = '''

// ============================================================================
// PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) — escreve em window.INPUT
// ============================================================================
(function initTouchControls() {
  const clamp1 = (v) => Math.max(-1, Math.min(1, v));
  const joy = document.getElementById('touch-joystick');
  const base = document.getElementById('joystick-base');
  const knob = document.getElementById('joystick-knob');

  if (joy && base && knob) {
    let joyId = null, cx = 0, cy = 0;
    const R = 56, DEAD = 0.18;
    const place = (x, y) => {
      base.style.left = (x - 60) + 'px'; base.style.top = (y - 60) + 'px';
      knob.style.left = (x - 30) + 'px'; knob.style.top = (y - 30) + 'px';
    };
    joy.addEventListener('pointerdown', (e) => {
      if (joyId !== null) return;
      joyId = e.pointerId;
      try { joy.setPointerCapture(joyId); } catch (err) {}
      cx = e.clientX; cy = e.clientY;
      place(cx, cy);
      joy.classList.add('active');
      e.preventDefault();
    });
    joy.addEventListener('pointermove', (e) => {
      if (e.pointerId !== joyId) return;
      const dx = e.clientX - cx, dy = e.clientY - cy;
      const len = Math.hypot(dx, dy) || 1;
      const cl = Math.min(len, R);
      const nx = dx / len, ny = dy / len;
      knob.style.transform = 'translate(' + (nx * cl).toFixed(1) + 'px,' + (ny * cl).toFixed(1) + 'px)';
      const mag = cl / R;
      if (mag < DEAD) { window.INPUT.moveX = 0; window.INPUT.moveZ = 0; }
      else { window.INPUT.moveX = clamp1(nx * mag); window.INPUT.moveZ = clamp1(-ny * mag); }
      e.preventDefault();
    });
    const joyEnd = (e) => {
      if (e.pointerId !== joyId) return;
      joyId = null;
      window.INPUT.moveX = 0; window.INPUT.moveZ = 0;
      knob.style.transform = 'translate(0,0)';
      joy.classList.remove('active');
    };
    joy.addEventListener('pointerup', joyEnd);
    joy.addEventListener('pointercancel', joyEnd);
  }

  // PV1.4: auto-aim — alvo inimigo mais próximo em alcance (teste/inspeção: window.findAimTarget)
  function findAimTarget(unit, range) {
    let best = null, bestD = Infinity;
    for (const t of units) {
      if (t === unit || t.team === unit.team || t.deadTimer > 0) continue;
      const d = Math.hypot(t.x - unit.x, t.z - unit.z);
      if (d <= range && d < bestD) { best = t; bestD = d; }
    }
    return best;
  }
  window.findAimTarget = findAimTarget;

  const SLOT_BTNS = [['tbtn-atk', 'atk'], ['tbtn-q', 'q'], ['tbtn-w', 'w'], ['tbtn-e', 'e'], ['tbtn-r', 'r']];
  for (const [id, slot] of SLOT_BTNS) {
    const btn = document.getElementById(id);
    if (!btn) continue;
    btn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      if (!matchActive) return;
      const player = units.find(u => u.isPlayer);
      if (!player) return;
      if (slot === 'atk') {
        window.INPUT.fire = true;
      } else {
        const tgt = findAimTarget(player, 46);
        if (tgt) {
          player.rotY = Math.atan2(tgt.x - player.x, tgt.z - player.z);
          player.mesh.rotation.y = player.rotY;
        }
        executeSkill(player, slot);
      }
      if (navigator.vibrate) { try { navigator.vibrate(12); } catch (err) {} }
      btn.classList.add('pressed');
    });
    const up = () => {
      if (slot === 'atk') window.INPUT.fire = false;
      btn.classList.remove('pressed');
    };
    btn.addEventListener('pointerup', up);
    btn.addEventListener('pointercancel', up);
    btn.addEventListener('pointerleave', up);
  }

  const btnC = document.getElementById('tbtn-c');
  if (btnC) {
    btnC.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      window.INPUT.chakra = true;
      btnC.classList.add('pressed');
    });
    const upc = () => { window.INPUT.chakra = false; btnC.classList.remove('pressed'); };
    btnC.addEventListener('pointerup', upc);
    btnC.addEventListener('pointercancel', upc);
    btnC.addEventListener('pointerleave', upc);
  }
})();
'''
g = g.rstrip() + '\n' + TOUCH_JS
wr('public/game.js', g)
ok.append('game.js: initTouchControls (joystick + cluster + auto-aim) + INPUT.chakra + merge charge')

# ================= styles.css =================
c = rd('public/styles.css')
backup('public/styles.css', 'pv1b')
assert 'TOUCH CONTROLS' not in c
c = c.rstrip() + '''

/* ==== PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==== */
#touch-controls { display: none; }
body.touch #hud-screen.active #touch-controls { display: block; }

#touch-joystick {
  position: fixed; left: 0; bottom: 0;
  width: 44vw; height: 52vh; z-index: 80; touch-action: none;
}
#joystick-base, #joystick-knob { position: fixed; pointer-events: none; opacity: 0; transition: opacity 0.12s; }
#touch-joystick.active #joystick-base, #touch-joystick.active #joystick-knob { opacity: 1; }
#joystick-base {
  width: 120px; height: 120px; border-radius: 50%;
  border: 2px solid rgba(249, 115, 22, 0.45);
  background: radial-gradient(circle, rgba(10, 14, 20, 0.55), rgba(10, 14, 20, 0.15));
}
#joystick-knob {
  width: 60px; height: 60px; border-radius: 50%;
  background: radial-gradient(circle, rgba(249, 115, 22, 0.85), rgba(249, 115, 22, 0.45));
  border: 2px solid rgba(255, 255, 255, 0.25);
}

#touch-cluster {
  position: fixed; right: calc(12px + var(--safe-right, 0px)); bottom: calc(12px + var(--safe-bottom, 0px));
  z-index: 80; touch-action: none;
  display: grid;
  grid-template-columns: 62px 62px 88px; grid-template-rows: 62px 62px 88px; gap: 8px;
}
.tbtn {
  width: 100%; height: 100%; border-radius: 50%; cursor: pointer; padding: 0;
  border: 2px solid rgba(148, 163, 184, 0.4);
  background: radial-gradient(circle, rgba(10, 14, 20, 0.72), rgba(10, 14, 20, 0.45));
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.08s, border-color 0.08s;
  -webkit-tap-highlight-color: transparent;
}
.tbtn img { width: 56%; height: 56%; object-fit: contain; pointer-events: none; filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.65)); }
.tbtn.pressed { transform: scale(0.9); border-color: #f97316; box-shadow: 0 0 14px rgba(249, 115, 22, 0.35); }
.tbtn-r  { grid-area: 1 / 3; }
.tbtn-c  { grid-area: 2 / 2; }
.tbtn-q  { grid-area: 2 / 3; }
.tbtn-e  { grid-area: 3 / 1; }
.tbtn-w  { grid-area: 3 / 2; }
.tbtn-atk { grid-area: 3 / 3; border-color: rgba(249, 115, 22, 0.55); }

/* em modo touch o badge de tecla nao faz sentido (§2.4: esconder, nao remover) */
body.touch .ability-key { display: none; }
'''
wr('public/styles.css', c)
ok.append('styles.css: bloco TOUCH CONTROLS + .ability-key oculto em body.touch')

print('\n'.join('[ok] ' + s for s in ok))
print('\nPV1-B PATCH APPLIED. Proximo: node --check + probe touch + bateria.')
