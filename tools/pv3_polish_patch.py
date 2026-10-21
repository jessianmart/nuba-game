"""PV3 — PERF E POLIMENTO MOBILE (docs/PIVOT_MOBILE.md §3, fase PV3).
Escopo entregue aqui: PV3.1 (quality governor mobile + VFX cap) e PV3.3
(haptics + PWA manifest instalavel). PV3.2 (arena merge) e PV3.4 (smoke em
device real) ficam fora deste patch.

Edits:
  E1 game.js — window.__GOV: em mobile aplica dpr cap 1.25 (pref do perfil
     respeitada ate 1.25) + expoe vfxCap 24; applyQuality passa a atualizar
     o governor (a pagina de ajustes nao pode furar o cap mobile).
  E2 game.js — VFX cap no loop de update: acima do cap descarta o VFX mais
     antigo (remove do arenaGroup e do array), sem tocar os frescos.
  E3 game.js — haptic(): helper com throttle 60ms + gate de perfil
     (data.haptics === false desliga); hooks em dealDamage — levou dano 18ms,
     acertou 12ms, morreu [40,60,40].
  E4 PWA — manifest.webmanifest (landscape, theme #f97316, fullscreen) +
     icones 192/512 quadrados gerados do logo.png via Pillow + metas no head.
Run: python tools/pv3_polish_patch.py   (cwd = repo root)
"""
import json
import os
import re
import shutil
import struct
import subprocess

GJ, HTML, CSS = 'public/game.js', 'public/index.html', 'public/styles.css'
MANIFEST = 'public/manifest.webmanifest'
for f in (GJ, HTML):
    shutil.copy2(f, f + '.bak_pv3')

g = open(GJ, 'r', encoding='utf-8', newline='').read()
h = open(HTML, 'r', encoding='utf-8', newline='').read()
c = open(CSS, 'r', encoding='utf-8', newline='').read()


def rep(t, old, new, what, n=1):
    k = t.count(old)
    assert k == n, f'{what}: esperava {n} ocorrencia(s), achei {k}'
    return t.replace(old, new, 1 if n == 1 else None)


# ---------------- E1: governor ----------------
E1_ANCHOR = """renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
window.__renderer = renderer; // W1.2: validação E2E de qualidade"""
E1_NEW = """renderer.setPixelRatio(Math.min(window.devicePixelRatio, 1.75));
// PV3.1: quality governor automatico. Mobile tem dpr cap 1.25 e teto de 24 VFX
// (GPU fraca, tela pequena); desktop mantem 1.75. A preferencia do perfil manda
// ATE o cap — 'high' em mobile ainda vale 1.25, nunca 1.75.
window.__GOV = (function () {
  let pref = 'high';
  try {
    const d = loadProfileData();
    if (d && typeof d.quality === 'string') pref = d.quality;
  } catch (e) {}
  const mob = !!(window.__DEVICE && window.__DEVICE.isMobile);
  const CAPS = { low: 0.75, med: 1.25, high: 1.75 };
  const cap = mob ? Math.min(CAPS[pref] || 1.25, 1.25) : (CAPS[pref] || 1.75);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, cap));
  return { mobile: mob, pref: pref, dprCap: cap, vfxCap: mob ? 24 : Infinity };
})();
window.__renderer = renderer; // W1.2: validação E2E de qualidade"""
g = rep(g, E1_ANCHOR, E1_NEW, 'E1 governor')

# applyQuality nao pode furar o cap mobile
E1B_ANCHOR = """  const applyQuality = (q) => {
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, QUALITY_CAPS[q] || 1.75));
    for (const k of Object.keys(pills)) if (pills[k]) pills[k].classList.toggle('active', k === q);
  };"""
E1B_NEW = """  const applyQuality = (q) => {
    // PV3.1: respeita o cap do governor (mobile nunca passa de 1.25)
    const _mob = !!(window.__DEVICE && window.__DEVICE.isMobile);
    const _cap = _mob ? Math.min(QUALITY_CAPS[q] || 1.25, 1.25) : (QUALITY_CAPS[q] || 1.75);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, _cap));
    if (window.__GOV) { window.__GOV.pref = q; window.__GOV.dprCap = _cap; window.__GOV.vfxCap = _mob ? 24 : Infinity; }
    for (const k of Object.keys(pills)) if (pills[k]) pills[k].classList.toggle('active', k === q);
  };"""
g = rep(g, E1B_ANCHOR, E1B_NEW, 'E1b applyQuality')

# ---------------- E2: VFX cap ----------------
E2_ANCHOR = """  updateShadowClones(simDt); // SPP: clones 3D (congelam com o mundo no juice)
  // Update VFX
  for (let i = vfxList.length - 1; i >= 0; i--) {"""
E2_NEW = """  updateShadowClones(simDt); // SPP: clones 3D (congelam com o mundo no juice)
  // PV3.1: VFX cap — acima do teto descarta o mais ANTIGO (o frescor do impacto
  // importa; efeito velho ja entregou o feedback). So roda no mobile (cap 24).
  if (window.__GOV && vfxList.length > window.__GOV.vfxCap) {
    let _wi = 0;
    for (let _k = 1; _k < vfxList.length; _k++) if (vfxList[_k].age > vfxList[_wi].age) _wi = _k;
    const _w = vfxList[_wi];
    if (_w && _w.mesh && _w.mesh.parent) _w.mesh.parent.remove(_w.mesh);
    vfxList.splice(_wi, 1);
  }
  // Update VFX
  for (let i = vfxList.length - 1; i >= 0; i--) {"""
g = rep(g, E2_ANCHOR, E2_NEW, 'E2 VFX cap')

# ---------------- E3: haptics ----------------
E3_ANCHOR = "function dealDamage(attacker, target, amount, skillName) {"
E3_NEW = """// PV3.3: haptics com throttle + gate de perfil (data.haptics === false desliga).
// Throttle 60ms evita buzz continuo em atk rapido / dano por tick de zona.
let _lastHaptic = 0;
function haptic(pattern) {
  if (!navigator.vibrate) return;
  const now = performance.now();
  if (now - _lastHaptic < 60) return;
  _lastHaptic = now;
  try {
    const d = loadProfileData();
    if (d && d.haptics === false) return;
  } catch (e) {}
  try { navigator.vibrate(pattern); } catch (err) {}
}

function dealDamage(attacker, target, amount, skillName) {"""
g = rep(g, E3_ANCHOR, E3_NEW, 'E3 helper haptic')

E3B_ANCHOR = """  target.hp = Math.max(0, target.hp - dmg);
"""
E3B_NEW = """  target.hp = Math.max(0, target.hp - dmg);

  // PV3.3: haptics — levou dano (18ms) > acertou (12ms)
  if (window.__GOV && window.__GOV.mobile) {
    if (target.isPlayer) haptic(18); else if (attacker.isPlayer) haptic(12);
  }
"""
g = rep(g, E3B_ANCHOR, E3B_NEW, 'E3b haptic dano')

E3C_ANCHOR = """  if (target.hp <= 0) {
    target.deadTimer = activeMatchCfg.respawn != null ? activeMatchCfg.respawn : 6.0;"""
E3C_NEW = """  if (target.hp <= 0) {
    if (window.__GOV && window.__GOV.mobile && target.isPlayer) haptic([40, 60, 40]); // PV3.3: morri
    target.deadTimer = activeMatchCfg.respawn != null ? activeMatchCfg.respawn : 6.0;"""
g = rep(g, E3C_ANCHOR, E3C_NEW, 'E3c haptic morte')

# ---------------- E4: PWA ----------------
# cor de fundo real do jogo (fallback #0b0d12)
m = re.search(r'body\s*\{[^}]*?background(?:-color)?\s*:\s*([^;\n}]+)', c)
BG = '#0b0d12'
if m:
    cand = m.group(1).strip()
    hm = re.search(r'#([0-9a-fA-F]{3,8})', cand)
    if hm:
        BG = '#' + hm.group(1)
print(f'[i] background do body detectado: {BG}')

try:
    from PIL import Image
except ImportError:
    subprocess.run(['pip', 'install', 'pillow'], check=True, capture_output=True)
    from PIL import Image

src = Image.open('public/assets/logo/logo.png').convert('RGBA')
for size in (192, 512):
    bg = Image.new('RGBA', (size, size), BG)
    inner = int(size * 0.76)
    r = min(inner / src.width, inner / src.height)
    lg = src.resize((max(1, int(src.width * r)), max(1, int(src.height * r))), Image.LANCZOS)
    bg.paste(lg, ((size - lg.width) // 2, (size - lg.height) // 2), lg)
    out = f'public/assets/logo/icon-{size}.png'
    bg.convert('RGB').save(out, 'PNG', optimize=True)
    print(f'[ok] {out} ({os.path.getsize(out)} bytes)')

manifest = {
    "name": "NUBA: Arena de Batalha Ninja",
    "short_name": "NUBA",
    "description": "MOBA ninja mobile-first: combate 3v3, classico 5v5 e Realeza na Vila.",
    "start_url": "./index.html",
    "scope": "./",
    "display": "fullscreen",
    "orientation": "landscape",
    "background_color": BG,
    "theme_color": "#f97316",
    "lang": "pt-BR",
    "icons": [
        {"src": "assets/logo/icon-192.png", "sizes": "192x192", "type": "image/png", "purpose": "any"},
        {"src": "assets/logo/icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"},
    ],
}
open(MANIFEST, 'w', encoding='utf-8', newline='\n').write(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
print(f'[ok] {MANIFEST}')

E4_ANCHOR = '  <link rel="icon" href="assets/logo/logo.webp" />'
E4_NEW = """  <link rel="icon" href="assets/logo/logo.webp" />
  <!-- PV3.3: PWA instalavel (landscape, tema Storm laranja) -->
  <link rel="manifest" href="manifest.webmanifest" />
  <link rel="apple-touch-icon" href="assets/logo/icon-192.png" />
  <meta name="theme-color" content="#f97316" />
  <meta name="mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-capable" content="yes" />
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
  <meta name="apple-mobile-web-app-title" content="NUBA" />"""
h = rep(h, E4_ANCHOR, E4_NEW, 'E4 metas PWA', n=1)

open(GJ, 'w', encoding='utf-8', newline='').write(g)
open(HTML, 'w', encoding='utf-8', newline='').write(h)

r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
print('PV3 PATCH DONE')
