"""W7 patcher: HUDs de batalha com estética shadcn/sonner + Framer Motion
vanilla (motion.esm.js vendored — spring física real).
- #streak-banner (SEQUENCIA): SAI do meio da tela -> toast compacto no canto
  sup. direito, blur+border fino, badge laranja, flare OFF, Motion spring.
- #center-banner (ULT): pill compacta com blur, sem border-image pesado,
  spring pop via Motion, duração 2100ms.
- GSAP fallback preservado; DOM IDs + classes hidden/show intactos (suite).
"""
import re
import shutil
import subprocess


def apply_edits(path, edits):
    shutil.copy2(path, path + '.bak_w7')
    s = open(path, encoding='utf-8', newline='').read()
    n = 0
    for old, new in edits:
        done = False
        for sep in ('\r\n', '\n'):
            o, nn = old.replace('\n', sep), new.replace('\n', sep)
            if s.count(o) == 1:
                s = s.replace(o, nn, 1)
                n += 1
                done = True
                break
        if not done:
            c = sum(s.count(old.replace('\n', sep)) for sep in ('\r\n', '\n'))
            raise SystemExit(f'ANCORA FALHOU em {path} (edit {n+1}, count={c}): {old[:80]!r}')
    open(path, 'w', encoding='utf-8', newline='').write(s)
    return n


CSS = [
    # 1. center-banner -> pill shadcn compacta (sem border-image, sem anim CSS — Motion assume)
    ('''.center-banner {
  pointer-events: none;
  position: fixed;
  top: 36%;
  left: 50%;
  transform: translate(-50%, -50%);
  background-color: rgba(10, 11, 18, 0.9);
  background-image: var(--skin-banners);
  background-repeat: no-repeat;
  background-position: center;
  background-size: auto 100%;
  border: 14px solid transparent;
  border-image: var(--skin-panel-orange) var(--skin-frame-slice) fill round;
  padding: 16px 60px;
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 900;
  letter-spacing: 2.5px;
  text-transform: uppercase;
  color: var(--storm-gold-light);
  text-shadow: 0 0 20px rgba(201, 162, 39, 0.8), 0 2px 10px rgba(0, 0, 0, 0.9);
  text-align: center;
  z-index: 50;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8);
  animation: bannerPop 0.4s var(--ease-bounce);
}''',
     '''.center-banner {
  /* W7: pill compacta estilo shadcn — blur + border fino, Motion spring no JS */
  pointer-events: none;
  position: fixed;
  top: 28%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(9, 9, 11, 0.72);
  -webkit-backdrop-filter: blur(12px);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  padding: 10px 26px;
  max-width: min(84vw, 480px);
  font-family: var(--font-display);
  font-size: 19px;
  font-weight: 900;
  letter-spacing: 1.5px;
  text-transform: uppercase;
  color: var(--storm-gold-light);
  text-shadow: 0 0 14px rgba(201, 162, 39, 0.55), 0 2px 8px rgba(0, 0, 0, 0.85);
  text-align: center;
  z-index: 50;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}'''),
    # 2. streak-banner -> bloco position+caixa inteiro (canto, compacto)
    ('''/* ==================== KILL STREAK BANNER (SEQUENCIA DE ABATES) ==================== */
.streak-banner {
  position: fixed;
  top: 18%;
  left: 50%;
  transform: translateX(-50%);
  z-index: 55;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  min-width: 340px;
  max-width: 90vw;
  padding: 10px 54px;
  overflow: hidden;
  background: rgba(10, 11, 18, 0.94);
  border: 12px solid transparent;
  border-image: var(--skin-panel-orange) var(--skin-frame-slice) fill round;
  box-shadow: 0 18px 44px rgba(0, 0, 0, 0.8), 0 0 30px rgba(201, 162, 39, 0.25);
}''',
     '''/* ==================== KILL STREAK BANNER (W7: toast estilo sonner no canto — shadcn + Motion) ==================== */
.streak-banner {
  position: fixed;
  top: 74px;
  right: 12px;
  left: auto;
  transform: none;
  z-index: 55;
  pointer-events: none;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 9px;
  min-width: 0;
  max-width: min(74vw, 320px);
  padding: 7px 14px;
  overflow: hidden;
  background: rgba(9, 9, 11, 0.68);
  -webkit-backdrop-filter: blur(10px);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.09);
  border-radius: 12px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.35);
}'''),
    # 3. keyframes streakPop OFF (transform X-based voaria com o novo canto)
    ('.streak-banner.show { animation: streakPop 0.45s var(--ease-bounce) both; }',
     '.streak-banner.show { animation: none; } /* W7: Motion spring assume (GSAP fallback) */'),
    # 4. flare off + internals compactos (badge laranja no count)
    ('''@keyframes streakFlarePulse {
  0%, 100% { opacity: 0.45; transform: translate(-50%, -50%) scale(1); }
  50% { opacity: 0.95; transform: translate(-50%, -50%) scale(1.07); }
}''',
     '''@keyframes streakFlarePulse { /* W7: flare desativado — toast limpo */
  0%, 100% { opacity: 0; }
}'''),
    ('''.streak-kanji {
  font-family: 'Noto Sans JP', sans-serif;
  font-weight: 900;
  font-size: 30px;
  letter-spacing: 5px;
  line-height: 1;
  color: var(--storm-gold-light);
  text-shadow: 0 0 14px rgba(232, 201, 106, 0.7), 0 2px 8px rgba(0, 0, 0, 0.9);
}''',
     '''.streak-kanji {
  font-family: 'Noto Sans JP', sans-serif;
  font-weight: 900;
  font-size: 19px;
  letter-spacing: 3px;
  line-height: 1;
  color: var(--storm-gold-light);
  text-shadow: 0 0 10px rgba(232, 201, 106, 0.6), 0 1px 6px rgba(0, 0, 0, 0.85);
}'''),
    ('''.streak-text {
  font-family: var(--font-display);
  font-size: 22px;
  font-weight: 900;
  letter-spacing: 4px;
  text-transform: uppercase;
  color: #ffffff;
  text-shadow: 0 2px 10px rgba(0, 0, 0, 0.95);
}''',
     '''.streak-text {
  font-family: var(--font-display);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #ffffff;
  text-shadow: 0 1px 6px rgba(0, 0, 0, 0.9);
}'''),
    ('''.streak-count {
  font-family: var(--font-display);
  font-size: 42px;
  font-weight: 900;
  line-height: 1;
  color: var(--storm-gold-light);
  text-shadow: 0 0 22px rgba(232, 201, 106, 0.9), 0 3px 12px rgba(0, 0, 0, 0.95);
}''',
     '''.streak-count {
  font-family: var(--font-display);
  font-size: 17px;
  font-weight: 900;
  line-height: 1.35;
  padding: 1px 9px;
  border-radius: 999px;
  background: rgba(249, 115, 22, 0.16);
  border: 1px solid rgba(249, 115, 22, 0.4);
  color: var(--storm-gold-light);
  text-shadow: 0 1px 5px rgba(0, 0, 0, 0.85);
}'''),
    # 5. touch overrides do novo design
    ('''body.touch .streak-banner { top: 84px; min-width: 220px; padding: 6px 24px; gap: 10px; border-width: 8px; }
body.touch .streak-kanji { font-size: 19px; letter-spacing: 3px; }
body.touch .streak-text { font-size: 13px; letter-spacing: 2px; }
body.touch .streak-count { font-size: 26px; }''',
     '''body.touch .streak-banner { top: 64px; padding: 6px 12px; gap: 8px; }
body.touch .streak-kanji { font-size: 16px; letter-spacing: 2px; }
body.touch .streak-text { font-size: 11px; letter-spacing: 1.5px; }
body.touch .streak-count { font-size: 14px; padding: 1px 8px; }'''),
    ('body.touch .center-banner { top: 24%; font-size: 15px; letter-spacing: 1.5px; padding: 8px 24px; border-width: 8px; }',
     'body.touch .center-banner { top: 22%; font-size: 14px; letter-spacing: 1px; padding: 7px 16px; }'),
]
n = apply_edits('public/styles.css', CSS)
print(f'styles.css: {n}/{len(CSS)}')

GJS = [
    # 1. Motion import + helper (apos o boot do MUSIC)
    ("MUSIC.play('menu'); // W6: trilha do lobby (modeslct)",
     '''MUSIC.play('menu'); // W6: trilha do lobby (modeslct)

// W7: Framer Motion vanilla (dom/+esm vendored em assets/vendor) — spring
// física para os HUDs. Import dinâmico: se falhar, GSAP/CSS seguram o fallback.
let MOTION = null;
import('./assets/vendor/motion.esm.js')
  .then((m) => { MOTION = m; window.MOTION = m; })
  .catch(() => {});
function w7Spring(el, props, opts) {
  if (MOTION && MOTION.animate) {
    try {
      return MOTION.animate(el, props, Object.assign({ type: 'spring', stiffness: 420, damping: 30 }, opts || {}));
    } catch (e) { /* fallback abaixo */ }
  }
  if (window.gsap) {
    try {
      window.gsap.fromTo(el, { scale: 0.9, opacity: 0 },
        { scale: 1, opacity: 1, duration: 0.3, ease: 'back.out(1.8)', overwrite: 'auto' });
    } catch (e) { /* seco */ }
  }
  return null;
}
window.w7Spring = w7Spring;'''),
    # 2. showStreakBanner: Motion spring (GSAP fallback), sem flare infinito
    ('''  pulseSkinHook('streak-banner', 1600);
  const gsapLib = window.gsap;
  if (!gsapLib) return;
  banner.classList.add('gsap-anim');
  gsapLib.fromTo(banner,
    { scale: 0.6, opacity: 0, xPercent: -50 },
    { scale: 1, opacity: 1, xPercent: -50, duration: 0.45, ease: 'back.out(2.2)', overwrite: 'auto' });
  const flare = banner.querySelector('.streak-flare');
  if (flare) {
    gsapLib.fromTo(flare,
      { opacity: 0.35, scale: 1.22, xPercent: -50, yPercent: -50 },
      { opacity: 0.9, scale: 1, xPercent: -50, yPercent: -50, duration: 0.85, ease: 'sine.inOut', repeat: -1, yoyo: true, overwrite: 'auto' });
  }
}''',
     '''  pulseSkinHook('streak-banner', 1600);
  // W7: toast no canto — spring física (Motion) com fallback GSAP; flare desativado
  w7Spring(banner, { opacity: [0, 1], scale: [0.94, 1], y: [-10, 0] }, { stiffness: 380, damping: 26 });
}'''),
    # 3. showBanner: spring pop + duração menor
    ('''function showBanner(text, duration = 2600) {
  const el = document.getElementById('center-banner');
  el.textContent = text;
  el.classList.remove('hidden');
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), duration);
}''',
     '''function showBanner(text, duration = 2100) {
  const el = document.getElementById('center-banner');
  el.textContent = text;
  el.classList.remove('hidden');
  w7Spring(el, { opacity: [0, 1], scale: [0.94, 1], x: ['-50%', '-50%'], y: ['-50%', '-50%'] },
    { stiffness: 520, damping: 34 }); // W7: pill com spring pop (Motion)
  clearTimeout(el._timer);
  el._timer = setTimeout(() => el.classList.add('hidden'), duration);
}'''),
]
n = apply_edits('public/game.js', GJS)
print(f'game.js: {n}/{len(GJS)}')

# cache-buster
for pat in (r'(game\.js\?v=)(\d+)', r'(styles\.css\?v=)(\d+)'):
    s = open('public/index.html', encoding='utf-8', newline='').read()
    m = re.search(pat, s)
    cur = m.group(2)
    s = re.sub(pat, lambda mm: mm.group(1) + str(int(mm.group(2)) + 1), s, count=1)
    open('public/index.html', 'w', encoding='utf-8', newline='').write(s)
    print(f'cache-buster {pat}: v{cur} -> v{int(cur)+1}')

# checks
chk = open('public/game.js', encoding='utf-8', newline='').read()
assert chk.count('W7') >= 5, chk.count('W7')
assert 'w7Spring(banner' in chk and 'w7Spring(el' in chk
css = open('public/styles.css', encoding='utf-8', newline='').read()
assert 'streak-banner {\n  position: fixed;\n  top: 74px;\n  right: 12px;'.replace('\n', '\r\n' if '\r\n' in css[:4000] else '\n') in css or 'top: 74px' in css
r = subprocess.run(['node', '--check', 'public/game.js'], capture_output=True, text=True)
assert r.returncode == 0, r.stderr[:400]
print('node --check OK — W7 PATCHER COMPLETO')
