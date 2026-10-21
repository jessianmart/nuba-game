# -*- coding: utf-8 -*-
"""W1.2 AJUSTES (settings page): 5a aba do lobby — som (toggle+volume), graficos
(pixel ratio), game feel (juice gate), controles (display). Persiste no perfil.
Rollback: *.bak_w12. Atomico: aborta sem escrever se qualquer ancora falhar."""
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
    shutil.copyfile(path, path + '.bak_w12')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

AJUSTES_PAGE = '''    <!-- W1.2 AJUSTES: som, graficos, game feel e controles -->
    <section id="page-ajustes" class="lobby-page" data-page="ajustes" role="tabpanel" aria-hidden="true">
      <div class="ajustes-grid">
        <section class="profile-section">
          <header><h4>SOM</h4><span>áudio do combate</span></header>
          <div class="pref-row">
            <div><strong>Efeitos sonoros</strong><span>jutsus, impactos e ougi do Storm</span></div>
            <label class="pref-switch"><input type="checkbox" id="aj-sound" checked /><span></span></label>
          </div>
          <div class="pref-row">
            <div><strong>Volume das cues</strong><span id="aj-volume-label">85%</span></div>
            <input type="range" id="aj-volume" class="aj-slider" min="0" max="100" step="5" value="85" aria-label="Volume" />
          </div>
        </section>

        <section class="profile-section">
          <header><h4>GRÁFICOS</h4><span>resolução de render</span></header>
          <div class="pref-row">
            <div><strong>Qualidade</strong><span>pixel ratio do WebGL</span></div>
            <div class="aj-pills">
              <button type="button" id="aj-q-low" class="pill-btn">BAIXA</button>
              <button type="button" id="aj-q-med" class="pill-btn">MÉDIA</button>
              <button type="button" id="aj-q-high" class="pill-btn active">ALTA</button>
            </div>
          </div>
        </section>

        <section class="profile-section">
          <header><h4>GAME FEEL</h4><span>impacto cinematográfico</span></header>
          <div class="pref-row">
            <div><strong>Screen shake & hitstop</strong><span>tremor de câmera e slow-mo de abate</span></div>
            <label class="pref-switch"><input type="checkbox" id="aj-juice" checked /><span></span></label>
          </div>
        </section>

        <section class="profile-section">
          <header><h4>CONTROLES</h4><span>teclado e mouse</span></header>
          <div class="aj-keys">
            <div><kbd>W A S D</kbd><span>mover</span></div>
            <div><kbd>← ↑ ↓ →</kbd><span>mover (setas)</span></div>
            <div><kbd>MOUSE</kbd><span>combo de taijutsu</span></div>
            <div><kbd>Q / 1</kbd><span>jutsu 1</span></div>
            <div><kbd>E / 2</kbd><span>jutsu 2</span></div>
            <div><kbd>ESPAÇO / 3</kbd><span>kawarimi</span></div>
            <div><kbd>R / 4</kbd><span>ultimate</span></div>
            <div><kbd>C</kbd><span>câmera livre</span></div>
            <div><kbd>H</kbd><span>ajudas</span></div>
            <div><kbd>TAB</kbd><span>placar</span></div>
          </div>
        </section>
      </div>
    </section>'''

INIT_AJUSTES = '''// ==================== W1.2 AJUSTES (página de configurações) ====================
function initAjustes() {
  const ajSound = document.getElementById('aj-sound');
  const prefSound = document.getElementById('pref-sound');
  const ajVol = document.getElementById('aj-volume');
  const ajVolLabel = document.getElementById('aj-volume-label');
  const ajJuice = document.getElementById('aj-juice');
  const pills = { low: document.getElementById('aj-q-low'), med: document.getElementById('aj-q-med'), high: document.getElementById('aj-q-high') };
  if (!ajSound) return;
  const QUALITY_CAPS = { low: 0.75, med: 1.25, high: 1.75 };
  const persistPatch = (patch) => { const d = loadProfileData(); Object.assign(d, patch); saveProfileData(d); };
  const applyQuality = (q) => {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, QUALITY_CAPS[q] || 1.75));
    for (const k of Object.keys(pills)) if (pills[k]) pills[k].classList.toggle('active', k === q);
  };
  const data = loadProfileData();
  ajSound.checked = data.sound !== false;
  const vol = typeof data.volume === 'number' ? Math.max(0, Math.min(1, data.volume)) : 0.85;
  if (typeof AUTH_SFX !== 'undefined') AUTH_SFX.volume = vol;
  if (ajVol) ajVol.value = Math.round(vol * 100);
  if (ajVolLabel) ajVolLabel.textContent = Math.round(vol * 100) + '%';
  applyQuality(QUALITY_CAPS[data.quality] ? data.quality : 'high');
  const juiceOn = data.juice !== false;
  JUICE.enabled = juiceOn;
  if (ajJuice) ajJuice.checked = juiceOn;
  ajSound.addEventListener('change', () => {
    sfx.enabled = ajSound.checked;
    if (prefSound) prefSound.checked = ajSound.checked;
    persistPatch({ sound: ajSound.checked });
    if (ajSound.checked) { sfx.init(); sfx.clink(); }
  });
  if (prefSound) prefSound.addEventListener('change', () => { ajSound.checked = prefSound.checked; });
  if (ajVol) {
    ajVol.addEventListener('input', () => {
      const v = Math.max(0, Math.min(1, Number(ajVol.value) / 100));
      if (typeof AUTH_SFX !== 'undefined') AUTH_SFX.volume = v;
      if (ajVolLabel) ajVolLabel.textContent = Math.round(v * 100) + '%';
    });
    ajVol.addEventListener('change', () => persistPatch({ volume: Math.max(0, Math.min(1, Number(ajVol.value) / 100)) }));
  }
  if (ajJuice) ajJuice.addEventListener('change', () => { JUICE.enabled = ajJuice.checked; persistPatch({ juice: ajJuice.checked }); });
  for (const k of Object.keys(pills)) if (pills[k]) pills[k].addEventListener('click', () => { applyQuality(k); persistPatch({ quality: k }); });
}'''

CSS = '''/* ==================== W1.2 AJUSTES ==================== */
#page-ajustes .ajustes-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 14px; width: 100%; align-content: start; }
#page-ajustes .profile-section { margin: 0; }
#page-ajustes .pref-row { padding: 10px 0; }
.aj-slider { accent-color: rgba(201, 162, 39, 0.95); width: 170px; height: 22px; cursor: pointer; }
.aj-pills { display: inline-flex; gap: 8px; }
.aj-pills .pill-btn.active { background: rgba(139, 26, 26, 0.55); }
.aj-keys { display: grid; grid-template-columns: 1fr 1fr; gap: 8px 18px; }
.aj-keys > div { display: flex; align-items: center; gap: 10px; font-size: 11px; color: #cbd5e1; }
.aj-keys kbd { font-family: 'Barlow Condensed', sans-serif; font-size: 11px; letter-spacing: 1px; color: #fbbf24; background: rgba(201, 162, 39, 0.08); border: 1px solid rgba(201, 162, 39, 0.3); border-radius: 4px; padding: 3px 7px; min-width: 52px; text-align: center; }'''

ok1 = apply('public/index.html', [
    ('nav: 5a aba AJUSTES',
     '        <button type="button" class="nav-tab" role="tab" aria-selected="false" aria-controls="page-perfil" data-page="perfil">PERFIL</button>\n      </nav>',
     '        <button type="button" class="nav-tab" role="tab" aria-selected="false" aria-controls="page-perfil" data-page="perfil">PERFIL</button>\n'
     '        <button type="button" class="nav-tab" role="tab" aria-selected="false" aria-controls="page-ajustes" data-page="ajustes">AJUSTES</button>\n'
     '      </nav>'),
    ('pagina de ajustes (pos-perfil)',
     '    </section>\n  </div>\n\n  <!-- ==================== IN-GAME MOBA 5v5 HUD ==================== -->',
     '    </section>\n\n' + AJUSTES_PAGE + '\n  </div>\n\n  <!-- ==================== IN-GAME MOBA 5v5 HUD ==================== -->'),
])

ok2 = apply('public/styles.css', [
    ('css ajustes (append)',
     '.cd-radial-overlay, .cd-overlay { font-size: 15px; }',
     '.cd-radial-overlay, .cd-overlay { font-size: 15px; }\n\n' + CSS),
])

ok3 = apply('public/game.js', [
    ('renderer exposto p/ E2E',
     'renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));',
     'renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));\nwindow.__renderer = renderer; // W1.2: validação E2E de qualidade'),
    ('JUICE.enabled master gate',
     '  t: 0             // juice clock in real time (drives shake noise)\n};',
     '  t: 0,            // juice clock in real time (drives shake noise)\n'
     '  enabled: true    // W1.2: master gate da página de Ajustes\n};'),
    ('gate das 3 juice fns one-liner',
     'function juiceHitstop(d) { JUICE.hitstop = Math.max(JUICE.hitstop, d); }\nfunction juiceShake(power) { JUICE.trauma = Math.min(1, JUICE.trauma + power); }\nfunction juiceFovPunch(deg) { JUICE.fovPunch = Math.max(JUICE.fovPunch, deg); }',
     'function juiceHitstop(d) { if (JUICE.enabled === false) return; JUICE.hitstop = Math.max(JUICE.hitstop, d); }\n'
     'function juiceShake(power) { if (JUICE.enabled === false) return; JUICE.trauma = Math.min(1, JUICE.trauma + power); }\n'
     'function juiceFovPunch(deg) { if (JUICE.enabled === false) return; JUICE.fovPunch = Math.max(JUICE.fovPunch, deg); }'),
    ('gate do juiceSlowmo',
     'function juiceSlowmo(scale, dur) {',
     'function juiceSlowmo(scale, dur) {\n  if (JUICE.enabled === false) return; // W1.2'),
    ('LOBBY_PAGES + ajustes',
     "const LOBBY_PAGES = ['play', 'ninjas', 'arenas', 'perfil'];",
     "const LOBBY_PAGES = ['play', 'ninjas', 'arenas', 'perfil', 'ajustes'];"),
    ('profile fallback: volume/quality/juice',
     "arenas: [], sound: true };",
     "arenas: [], sound: true, volume: 0.85, quality: 'high', juice: true };"),
    ('boot: initAjustes() + definicao',
     '  sfx.enabled = loadProfileData().sound !== false;\n}',
     '  sfx.enabled = loadProfileData().sound !== false;\n  initAjustes(); // W1.2: wire da página de Ajustes\n}\n\n' + INIT_AJUSTES),
])

print('W1.2:', 'APLICADO' if (ok1 and ok2 and ok3) else 'ABORTADO')
sys.exit(0 if (ok1 and ok2 and ok3) else 1)
