# -*- coding: utf-8 -*-
"""P1 JUICE PATCH — surgical additive patcher for NUBA public/game.js.

Applies the P1 Juice Pass (hitstop + camera shake + kill slow-mo + FOV punch
+ hit VFX upgrade) with strict safety:
  - every anchor MUST occur exactly once (abort otherwise, file untouched)
  - backup written to public/game.js.bak_p1juice on first run
  - original EOL style (CRLF/LF) preserved
Run from the goofy-mendeleev repo root.
"""
import io, os, shutil, sys

PATH = 'public/game.js'
BAK = 'public/game.js.bak_p1juice'

patches = []
def P(name, old, new):
    patches.append((name, old, new))

# --------------------------------------------------------------------------
# P-A: JUICE system module (state, helpers, flash texture, shake solver)
# --------------------------------------------------------------------------
P('A: juice module', """const keys = {};
""", """const keys = {};

// ============================================================================
// P1 JUICE SYSTEM — Hitstop, Camera Shake, Kill Slow-Mo & FOV Punch
// Additive combat-feel layer (docs/UI_SKIN_CONTRACT.md §5 compliant): scales
// ONLY simulation cadence + camera offsets. Match clock, cooldowns, respawn
// timers and every DOM contract keep real dt (E2E suite safety).
// ============================================================================
const JUICE = {
  hitstop: 0,      // seconds of combat freeze remaining
  timeScale: 1,    // live sim timescale (0 during hitstop, <1 in slow-mo)
  slowTarget: 1,   // target timescale while the slow-mo window is active
  slowTimer: 0,    // seconds remaining of the slow-mo window
  trauma: 0,       // camera shake energy 0..1 (linear decay)
  fovPunch: 0,     // cinematic zoom-in punch (degrees, fast decay)
  t: 0             // juice clock in real time (drives shake noise)
};

function juiceHitstop(d) { JUICE.hitstop = Math.max(JUICE.hitstop, d); }
function juiceShake(power) { JUICE.trauma = Math.min(1, JUICE.trauma + power); }
function juiceFovPunch(deg) { JUICE.fovPunch = Math.max(JUICE.fovPunch, deg); }
function juiceSlowmo(scale, dur) {
  if (scale < JUICE.slowTarget || JUICE.slowTimer <= 0) JUICE.slowTarget = scale;
  JUICE.slowTimer = Math.max(JUICE.slowTimer, dur);
}

// Procedural radial flash texture for impact pops (additive sprite VFX)
const flashTexture = (() => {
  const c = document.createElement('canvas');
  c.width = c.height = 128;
  const ctx = c.getContext('2d');
  const g = ctx.createRadialGradient(64, 64, 2, 64, 64, 62);
  g.addColorStop(0, 'rgba(255,255,255,1)');
  g.addColorStop(0.35, 'rgba(255,255,255,0.85)');
  g.addColorStop(0.75, 'rgba(255,255,255,0.25)');
  g.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = g;
  ctx.fillRect(0, 0, 128, 128);
  return new THREE.CanvasTexture(c);
})();

function updateJuice(dt) {
  JUICE.t += dt;
  if (JUICE.hitstop > 0) JUICE.hitstop = Math.max(0, JUICE.hitstop - dt);
  if (JUICE.slowTimer > 0) {
    JUICE.slowTimer = Math.max(0, JUICE.slowTimer - dt);
  } else {
    JUICE.slowTarget = 1;
  }
  const targetScale = JUICE.hitstop > 0 ? 0 : JUICE.slowTarget;
  // Snap hard INTO the freeze, breathe softly out of it
  const rate = targetScale < JUICE.timeScale ? 45 : 6.5;
  JUICE.timeScale += (targetScale - JUICE.timeScale) * Math.min(1, dt * rate);
  JUICE.trauma = Math.max(0, JUICE.trauma - dt * 1.35);
  JUICE.fovPunch = Math.max(0, JUICE.fovPunch - dt * 30);
  // Cinematic zoom punch (48 = native PerspectiveCamera fov)
  const fov = 48 - JUICE.fovPunch;
  if (camera.fov !== fov) {
    camera.fov = fov;
    camera.updateProjectionMatrix();
  }
}

// Additive trauma shake applied AFTER the camera solves its target position.
// Offsets are re-clamped so the stage safety contract (Y >= 2.2, [-lim, lim])
// holds even mid-shake.
function applyCameraShake() {
  if (JUICE.trauma <= 0.001) return;
  const t2 = JUICE.trauma * JUICE.trauma;
  const tt = JUICE.t * 37.7;
  const amp = 2.1 * t2;
  camera.position.x += Math.sin(tt * 1.13 + 3.1) * amp;
  camera.position.y += Math.sin(tt * 1.71 + 1.7) * amp * 0.72;
  camera.position.z += Math.sin(tt * 0.97 + 5.9) * amp;
  camera.position.x = clampCamera(camera.position.x);
  camera.position.z = clampCamera(camera.position.z);
  camera.position.y = Math.max(2.2, camera.position.y);
}
""")

# --------------------------------------------------------------------------
# P-B: updateMatch head — juice tick + simDt derivation
# --------------------------------------------------------------------------
P('B: updateMatch head', """function updateMatch(dt, elapsed) {
  matchTimeRemaining = Math.max(0, matchTimeRemaining - dt);
""", """function updateMatch(dt, elapsed) {
  updateJuice(dt);
  // P1 JUICE: simDt drives combat cadence (units/AI/projectiles/VFX).
  // Clock, cooldowns, respawn and regen keep real dt (E2E contracts safe).
  const simDt = dt * JUICE.timeScale;
  matchTimeRemaining = Math.max(0, matchTimeRemaining - dt);
""")

# --------------------------------------------------------------------------
# P-C1..C3: unit cadence timers + player/AI updates on simDt
# --------------------------------------------------------------------------
P('C1: comboResetTimer', """    if (u.comboResetTimer > 0) {
      u.comboResetTimer -= dt;
      if (u.comboResetTimer <= 0) u.comboStep = 0;
    }
""", """    if (u.comboResetTimer > 0) {
      u.comboResetTimer -= simDt; // P1 JUICE: combo window freezes in hitstop
      if (u.comboResetTimer <= 0) u.comboStep = 0;
    }
""")

P('C2: animTimer freeze', """    if (u.animTimer > 0) {
      u.animTimer -= dt;
    }
""", """    if (u.animTimer > 0) {
      u.animTimer -= simDt; // P1 JUICE: THE hitstop — action animations freeze
    }
""")

P('C3: player/AI simDt', """    if (u.isPlayer) {
      updatePlayerUnit(u, dt);
    } else {
      updateAIBotUnit(u, dt);
    }
""", """    if (u.isPlayer) {
      updatePlayerUnit(u, simDt); // P1 JUICE: movement/AI scale with hitstop & slow-mo
    } else {
      updateAIBotUnit(u, simDt);
    }
""")

# --------------------------------------------------------------------------
# P-C4/C5: projectile & VFX loops — shadow dt with simDt (single-point patch)
# --------------------------------------------------------------------------
P('C4: projectiles simDt', """  // Update Projectiles
  for (let i = projectiles.length - 1; i >= 0; i--) {
    const p = projectiles[i];
    p.life -= dt;
""", """  // Update Projectiles
  for (let i = projectiles.length - 1; i >= 0; i--) {
    const p = projectiles[i];
    const dt = simDt; // P1 JUICE: kunai freeze mid-air in hitstop, drift in slow-mo
    p.life -= dt;
""")

P('C5: vfx simDt', """  // Update VFX
  for (let i = vfxList.length - 1; i >= 0; i--) {
    const v = vfxList[i];
    v.age += dt;
""", """  // Update VFX
  for (let i = vfxList.length - 1; i >= 0; i--) {
    const v = vfxList[i];
    const dt = simDt; // P1 JUICE: VFX freeze with the world, play slow on kills
    v.age += dt;
""")

# --------------------------------------------------------------------------
# P-C6: new 'flash' VFX style branch
# --------------------------------------------------------------------------
P('C6: flash vfx style', """    } else if (v.style === 'hit_star') {
      v.mesh.rotation.x += dt * 12;
      v.mesh.rotation.y += dt * 16;
      v.mesh.scale.multiplyScalar(Math.max(0.01, 1 - dt * 4.0));
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, 1 - t);
    } else if (v.style === 'spark') {
""", """    } else if (v.style === 'hit_star') {
      v.mesh.rotation.x += dt * 12;
      v.mesh.rotation.y += dt * 16;
      v.mesh.scale.multiplyScalar(Math.max(0.01, 1 - dt * 4.0));
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, 1 - t);
    } else if (v.style === 'flash') {
      // P1 JUICE: white radial impact flash — explosive pop, instant fade
      const pop = 1 + t * 9;
      v.mesh.scale.set(pop, pop, 1);
      if (v.mesh.material) v.mesh.material.opacity = Math.max(0, 0.9 * (1 - t * 3.2));
    } else if (v.style === 'spark') {
""")

# --------------------------------------------------------------------------
# P-D1: dealDamage impact juice (weight + distance gates)
# --------------------------------------------------------------------------
P('D1: impact juice', """  // Cel-shaded impact hit spark burst on damage impact
  spawnHitSparks(target.x, 2.2, target.z, attacker.awakenedTimer > 0 ? 0xf97316 : 0xfde047);
""", """  // Cel-shaded impact hit spark burst on damage impact
  // P1 JUICE: hitstop + shake + zoom scaled by damage weight, player
  // involvement and distance (no shake fatigue from distant bot fights)
  const juiceW = dmg >= 300 ? 3 : (dmg >= 180 ? 2 : (dmg >= 60 ? 1 : 0));
  const juicePl = units.find(x => x.isPlayer);
  const juiceDist = juicePl ? Math.hypot(target.x - juicePl.x, target.z - juicePl.z) : 999;
  const juiceNear = THREE.MathUtils.clamp(1 - (juiceDist - 14) / 34, 0, 1);
  const juiceScale = (attacker.isPlayer || target.isPlayer) ? 1 : juiceNear * 0.7;
  spawnHitSparks(target.x, 2.2, target.z, attacker.awakenedTimer > 0 ? 0xf97316 : 0xfde047, 0.7 + 0.25 * juiceW);
  if (juiceScale > 0.05) {
    const juiceHs = [0.018, 0.03, 0.052, 0.082][juiceW] * juiceScale;
    if (juiceHs >= 0.012) juiceHitstop(juiceHs);
    juiceShake((0.05 + juiceW * 0.115) * juiceScale);
    if (juiceW >= 3) juiceFovPunch(3.0 * juiceScale);
  }
""")

# --------------------------------------------------------------------------
# P-D2: kill branch — deep slow-mo + hitstop + heavy shake
# --------------------------------------------------------------------------
P('D2: kill drama', """    // SFX: Dramatic KO defeat audio
    sfx.ko();
""", """    // SFX: Dramatic KO defeat audio
    sfx.ko();

    // P1 JUICE: kill drama — deep slow-mo + hitstop + heavy shake.
    // Full drama when the player is involved; distant bot kills stay subtle.
    const ultKill = juiceW === 3;
    if (attacker.isPlayer || target.isPlayer) {
      juiceHitstop(ultKill ? 0.13 : 0.08);
      juiceSlowmo(ultKill ? 0.22 : 0.34, ultKill ? 0.75 : 0.45);
      juiceShake(ultKill ? 0.55 : 0.35);
      juiceFovPunch(ultKill ? 5.5 : 3.2);
    } else if (juiceNear > 0.3) {
      juiceHitstop(0.05);
      juiceShake(0.18 * juiceNear);
    }
""")

P('D3: ko sparks intensity', """    spawnHitSparks(target.x, 2.0, target.z, 0xff2222);
""", """    spawnHitSparks(target.x, 2.0, target.z, 0xff2222, 1.7);
""")

# --------------------------------------------------------------------------
# P-E: ultimate cast drama (player-gated)
# --------------------------------------------------------------------------
P('E: ult cast drama', """  // Skin HUD hooks (Ougi ultimate / Kawarimi substitution)
  if (unit.isPlayer) {
    if (slot === 'r') showOugiBanner();
    else if (slot === 'e') flashKawarimi();
  }
""", """  // Skin HUD hooks (Ougi ultimate / Kawarimi substitution)
  if (unit.isPlayer) {
    if (slot === 'r') {
      showOugiBanner();
      // P1 JUICE: ultimate cast drama — wind-up freeze + rising cinematic zoom
      juiceHitstop(0.09);
      juiceSlowmo(0.55, 0.35);
      juiceShake(0.30);
      juiceFovPunch(4.0);
    } else if (slot === 'e') {
      flashKawarimi();
    }
  }
""")

# --------------------------------------------------------------------------
# P-F: applyCameraShake hook at end of camera solver
# --------------------------------------------------------------------------
P('F: camera shake hook', """    if (camera.position.distanceToSquared(lookTarget) > 0.01) {
      camera.lookAt(lookTarget);
    }
  }

  // Update Player HUD Bars
""", """    if (camera.position.distanceToSquared(lookTarget) > 0.01) {
      camera.lookAt(lookTarget);
    }
  }

  // P1 JUICE: additive impact shake on top of the solved camera position
  applyCameraShake();

  // Update Player HUD Bars
""")

# --------------------------------------------------------------------------
# P-G: lobby fov safety restore
# --------------------------------------------------------------------------
P('G: lobby fov restore', """  if (!matchActive) {
    // Lobby 3D Character Pedestal Camera
    camera.position.set(0, 3.2, 8.2);
    camera.lookAt(0, 2.65, 0);
""", """  if (!matchActive) {
    // Lobby 3D Character Pedestal Camera
    camera.position.set(0, 3.2, 8.2);
    camera.lookAt(0, 2.65, 0);
    if (camera.fov !== 48) { // P1 JUICE: restore native fov after match drama
      camera.fov = 48;
      camera.updateProjectionMatrix();
    }
""")

# --------------------------------------------------------------------------
# P-H: fresh juice state on match start
# --------------------------------------------------------------------------
P('H: match juice reset', """  matchTimeRemaining = 300;
  projectiles = [];
  vfxList = [];
""", """  matchTimeRemaining = 300;
  projectiles = [];
  vfxList = [];
  // P1 JUICE: fresh match, fresh feel state
  JUICE.hitstop = 0;
  JUICE.slowTimer = 0;
  JUICE.slowTarget = 1;
  JUICE.timeScale = 1;
  JUICE.trauma = 0;
  JUICE.fovPunch = 0;
""")

# --------------------------------------------------------------------------
# P-I: expose JUICE for E2E/inspection (additive window hook)
# --------------------------------------------------------------------------
P('I: window.JUICE hook', """window.dealDamage = dealDamage;
""", """window.dealDamage = dealDamage;
window.JUICE = JUICE; // P1 JUICE: exposed for E2E/inspection
""")

# --------------------------------------------------------------------------
# P-J: spawnHitSparks upgrade (flash sprite + intensity scaling)
# --------------------------------------------------------------------------
P('J1: sparks head + flash', """function spawnHitSparks(x, y, z, colorHex = 0xfde047) {
  // 1. Central bright starburst flash
""", """function spawnHitSparks(x, y, z, colorHex = 0xfde047, intensity = 1) {
  // P1 JUICE: intensity 0.75 light hit / 1.0 skill / 1.7 KO & ult impact
  // 0. White radial impact flash (procedural additive sprite)
  const flashMat = new THREE.SpriteMaterial({
    map: flashTexture,
    color: 0xffffff,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending,
    depthWrite: false
  });
  const flashMesh = new THREE.Sprite(flashMat);
  flashMesh.position.set(x, y, z);
  const juiceFs = 3.2 * intensity;
  flashMesh.scale.set(juiceFs, juiceFs, 1);
  arenaGroup.add(flashMesh);
  vfxList.push({ mesh: flashMesh, age: 0, duration: 0.12, style: 'flash' });

  // 1. Central bright starburst flash
""")

P('J2: star scale', """  starMesh.scale.set(1.4, 1.4, 1.4);
""", """  starMesh.scale.set(1.4 * intensity, 1.4 * intensity, 1.4 * intensity);
""")

P('J3: ring radius', """  spawnVFX(x, y, z, colorHex, 2.2, 0.22, 'ring');
""", """  spawnVFX(x, y, z, colorHex, 2.2 * intensity, 0.22, 'ring');
""")

P('J4: shard count', """  const shardCount = 6;
""", """  const shardCount = 6 + Math.round(4 * Math.min(1.7, intensity));
""")

P('J5: shard speed', """  const speed = 7.0 + Math.random() * 6.0;
""", """  const speed = (7.0 + Math.random() * 6.0) * (0.8 + 0.35 * intensity);
""")

# ==========================================================================
# RUN
# ==========================================================================
raw = io.open(PATH, 'r', encoding='utf-8', newline='').read()
eol = '\r\n' if '\r\n' in raw else '\n'
src = raw.replace('\r\n', '\n')

if 'P1 JUICE' in src:
    print('ABORT: game.js already contains P1 JUICE markers (patched before?)')
    sys.exit(1)

fails = []
for name, old, new in patches:
    n = src.count(old)
    if n != 1:
        fails.append((name, n))
if fails:
    for name, n in fails:
        print(f'ANCHOR FAIL [{name}]: {n} occurrences (expected 1)')
    print(f'ABORTED — {len(fails)}/{len(patches)} anchors failed. File NOT touched.')
    sys.exit(1)

if not os.path.exists(BAK):
    shutil.copy2(PATH, BAK)
    print(f'Backup: {BAK}')

for name, old, new in patches:
    src = src.replace(old, new, 1)
    print(f'  [OK] {name}')

out = src if eol == '\n' else src.replace('\n', '\r\n')
io.open(PATH, 'w', encoding='utf-8', newline='').write(out)
print(f'ALL {len(patches)} PATCHES APPLIED (EOL={eol!r} preserved)')
