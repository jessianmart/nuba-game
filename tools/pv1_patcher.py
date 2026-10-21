# -*- coding: utf-8 -*-
"""PV1.3+PV1.4+PV1.5 (docs/PIVOT_MOBILE.md): controles touch completos.
PV1.3 joystick flutuante (42% esq, r64, dead-zone .18) -> INPUT.moveX/moveZ
PV1.4 cluster de skills (ATK hold=INPUT.fire; Q/W/R/E tap=executeSkill)
PV1.4c gate: touch NAO simula mouse (pointerdown global)
PV1.5a thirdperson auto em touch; PV1.5b pan off em touch
Aditivo total; suite legada 38/38 deve seguir verde. Rollback: *.bak_pv1"""
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
    shutil.copyfile(path, path + '.bak_pv1')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

TOUCH_DOM = '''  <div id="hud-screen" class="screen">
    <!-- PV1.3/PV1.4: controles touch (aditivos — visiveis apenas em body.touch) -->
    <div id="touch-joystick" class="touch-only" aria-hidden="true">
      <div id="touch-joystick-base"></div>
      <div id="touch-joystick-knob"></div>
    </div>
    <div id="touch-cluster" class="touch-only" aria-hidden="true">
      <button type="button" id="tc-atk" class="tc-btn tc-atk" data-slot="atk" aria-label="Ataque Básico (segure)">ATK</button>
      <button type="button" id="tc-q" class="tc-btn" data-slot="q" aria-label="Jutsu 1">Q</button>
      <button type="button" id="tc-w" class="tc-btn" data-slot="w" aria-label="Jutsu 2">W</button>
      <button type="button" id="tc-e" class="tc-btn tc-kawarimi" data-slot="e" aria-label="Kawarimi">K</button>
      <button type="button" id="tc-r" class="tc-btn tc-ult" data-slot="r" aria-label="Ultimate">R</button>
    </div>'''

TOUCH_JS = '''
// ============================================================================
// PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) — joystick + cluster
// ============================================================================
window.__cameraMode = () => cameraMode; // PV1.5a: leitura E2E do modo de câmera
function initTouchControls() {
  const joy = document.getElementById('touch-joystick');
  const base = document.getElementById('touch-joystick-base');
  const knob = document.getElementById('touch-joystick-knob');
  if (!joy || !base || !knob || !window.__DEVICE.isTouch) return;
  const JOY_R = 64, DEAD = 0.18; // §2.4: r 64px, dead-zone 0.18
  let joyId = null, ox = 0, oy = 0;
  const place = (x, y, dx, dy) => {
    base.style.left = x + 'px'; base.style.top = y + 'px';
    knob.style.left = (x + dx) + 'px'; knob.style.top = (y + dy) + 'px';
  };
  joy.addEventListener('pointerdown', (e) => {
    if (joyId !== null) return; // pointerId exclusivo (§2.4)
    joyId = e.pointerId;
    try { joy.setPointerCapture(e.pointerId); } catch (err) {}
    ox = e.clientX; oy = e.clientY; // spawn flutuante no toque
    joy.classList.add('live');
    place(ox, oy, 0, 0);
    e.preventDefault();
  });
  joy.addEventListener('pointermove', (e) => {
    if (e.pointerId !== joyId) return;
    let dx = e.clientX - ox, dy = e.clientY - oy;
    const d = Math.hypot(dx, dy);
    if (d > JOY_R) { dx = dx / d * JOY_R; dy = dy / d * JOY_R; }
    place(ox, oy, dx, dy);
    let nx = dx / JOY_R, ny = dy / JOY_R;
    if (Math.hypot(nx, ny) < DEAD) { nx = 0; ny = 0; }
    window.INPUT.moveX = nx;   // direita = +X (igual D)
    window.INPUT.moveZ = -ny;  // dedo p/ cima = frente (igual W)
  });
  const joyEnd = (e) => {
    if (e.pointerId !== joyId) return;
    joyId = null; joy.classList.remove('live');
    window.INPUT.moveX = 0; window.INPUT.moveZ = 0;
  };
  joy.addEventListener('pointerup', joyEnd);
  joy.addEventListener('pointercancel', joyEnd);

  // PV1.4: cluster — espelha o keydown (mesmos guards: matchActive + isPlayer)
  document.querySelectorAll('#touch-cluster .tc-btn').forEach((btn) => {
    const slot = btn.dataset.slot;
    btn.addEventListener('pointerdown', (e) => {
      e.preventDefault();
      if (!matchActive) return;
      const player = units.find(u => u.isPlayer);
      if (!player) return;
      if (slot === 'atk') window.INPUT.fire = true; // segurar = combo (consumido em updatePlayerUnit)
      else executeSkill(player, slot); // auto-face nearest enemy nativo do executeSkill = auto-aim
    });
    const fireEnd = () => { if (slot === 'atk') window.INPUT.fire = false; };
    btn.addEventListener('pointerup', fireEnd);
    btn.addEventListener('pointercancel', fireEnd);
    btn.addEventListener('pointerleave', fireEnd);
  });
}
initTouchControls();'''

CSS = '''
/* ==================== PV1 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==================== */
#touch-joystick { position: fixed; left: 0; bottom: 0; width: 42%; height: 62%; z-index: 90; touch-action: none; display: none; }
#touch-joystick-base { position: fixed; width: 128px; height: 128px; border-radius: 50%; border: 2px solid rgba(201,162,39,.55); background: rgba(8,9,15,.35); opacity: 0; transform: translate(-50%,-50%); transition: opacity .12s; pointer-events: none; }
#touch-joystick-knob { position: fixed; width: 56px; height: 56px; border-radius: 50%; background: rgba(201,162,39,.85); box-shadow: 0 0 18px rgba(201,162,39,.4); opacity: 0; transform: translate(-50%,-50%); transition: opacity .12s; pointer-events: none; }
#touch-joystick.live #touch-joystick-base, #touch-joystick.live #touch-joystick-knob { opacity: 1; }
#touch-cluster { position: fixed; right: calc(14px + env(safe-area-inset-right)); bottom: calc(108px + env(safe-area-inset-bottom)); z-index: 90; display: none; grid-template-columns: repeat(2, 76px); grid-auto-rows: 76px; gap: 10px; touch-action: none; }
body.touch #touch-joystick { display: block; }
body.touch #touch-cluster { display: grid; }
.tc-btn { width: 76px; height: 76px; border-radius: 50%; border: 2px solid rgba(201,162,39,.5); background: rgba(18,20,28,.72); color: #fbbf24; font-family: 'Barlow Condensed', sans-serif; font-size: 21px; letter-spacing: 1px; cursor: pointer; }
.tc-atk { grid-row: span 2; width: 96px; height: 96px; background: rgba(139,26,26,.55); border-color: rgba(201,162,39,.8); font-size: 18px; align-self: end; }
.tc-ult { border-color: rgba(255,80,0,.75); color: #ff9d5c; }
.tc-kawarimi { border-color: rgba(163,230,53,.5); color: #d4f99b; }
.tc-btn:active { transform: scale(.92); }
body.touch .ability-key { display: none; } /* §2.4: badges de tecla escondidos no touch */'''

ok1 = apply('public/index.html', [
    ('DOM: touch joystick + cluster (topo do hud-screen)',
     '  <div id="hud-screen" class="screen">',
     TOUCH_DOM),
])

ok2 = apply('public/styles.css', [
    ('CSS touch controls (append)', CSS_MARKER := '.aj-keys kbd', CSS_MARKER),
]) if False else apply('public/styles.css', [
    ('CSS touch controls (apos bloco W1.2)',
     "body.touch .ability-key { display: none; } /* PV1.3 placeholder */" if False else ".aj-keys kbd { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px; color: #fbbf24; background: rgba(201, 162, 39, 0.08); border: 1px solid rgba(201, 162, 39, 0.3); border-radius: 4px; padding: 3px 7px; min-width: 52px; text-align: center; }",
     ".aj-keys kbd { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px; color: #fbbf24; background: rgba(201, 162, 39, 0.08); border: 1px solid rgba(201, 162, 39, 0.3); border-radius: 4px; padding: 3px 7px; min-width: 52px; text-align: center; }\n" + CSS),
])

ok3 = apply('public/game.js', [
    ('JS: initTouchControls (apos definicao de INPUT)',
     "  chakra: false                       // botao de concentrar chakra segurado (PV1.4)\n};",
     "  chakra: false                       // botao de concentrar chakra segurado (PV1.4)\n};\n" + TOUCH_JS),
    ('PV1.4c: touch nao simula mouse (atk/pan fantasma)',
     "  window.addEventListener('pointerdown', (e) => {\n    if (e.button === 2) {",
     "  window.addEventListener('pointerdown', (e) => {\n    if (e.pointerType === 'touch') return; // PV1.4c: touch tem controles proprios (joystick/cluster)\n    if (e.button === 2) {"),
    ('PV1.5b: pan de camera off em touch',
     "    } else if (matchActive && cameraMode === 'thirdperson' && (rightMouseDown || mouseDown)) {",
     "    } else if (matchActive && cameraMode === 'thirdperson' && !window.__DEVICE.isTouch && (rightMouseDown || mouseDown)) {"),
    ('PV1.5a: thirdperson auto ao iniciar partida em touch',
     "  lastMatchConfigId = MATCH_CONFIGS[configId] ? configId : 'dm_legacy_5v5';",
     "  lastMatchConfigId = MATCH_CONFIGS[configId] ? configId : 'dm_legacy_5v5';\n  if (window.__DEVICE.isTouch && cameraMode !== 'thirdperson') toggleCameraMode(); // PV1.5a: câmera mobile"),
])

print('PV1:', 'APLICADO' if (ok1 and ok2 and ok3) else 'ABORTADO')
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
