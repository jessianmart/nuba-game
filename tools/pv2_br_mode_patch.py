"""PV2 — REALEZA NA VILA (modo BR jogavel). docs/PIVOT_MOBILE.md §PV2.
- MATCH_CONFIGS.br_vila real (arena sa00z, solo 10, sem respawn, zona 65->6 em 6 fases)
- startBRMatch: spawn solo no layout real (br_vila_layout.json), zona 結界 visual, 12 baús
- updateBR no updateMatch: zona encolhe, dano fora, coleta de baús, last-standing
- morte permanente BR (gate no rebirth), sem overlay de respawn, HUD VIVOS/FASE
- chip do mode-picker habilitado
Run: python tools/pv2_br_mode_patch.py   (cwd = repo root)
"""
import shutil

GJ = 'public/game.js'
HTML = 'public/index.html'
CSS = 'public/styles.css'
shutil.copy2(GJ, GJ + '.bak_pv2')
shutil.copy2(HTML, HTML + '.bak_pv2')
shutil.copy2(CSS, CSS + '.bak_pv2')

g = open(GJ, 'r', encoding='utf-8', newline='').read()          # LF
h = open(HTML, 'r', encoding='utf-8', newline='').read()        # CRLF
c = open(CSS, 'r', encoding='utf-8', newline='').read()         # CRLF


def rep(text, old, new, what, n=1):
    k = text.count(old)
    assert k == n, f'{what}: esperava {n} ocorrencia(s), achei {k}'
    return text.replace(old, new, 1 if n == 1 else None)


# ============ game.js ============
# E1 — config real do BR
g = rep(g,
        "  br_vila:       { label: 'REALEZA NA VILA', mode: 'br', arena: 'sd00a', players: 10, squad: 1 } // PV2 (§2.3)",
        "  br_vila:       { label: 'REALEZA NA VILA', mode: 'br', arena: 'sa00z', players: 10, squad: 1, teamSize: 5, killTarget: null, time: 180, respawn: null, overtime: 0, zoneStart: 65, zoneMin: 6, zonePhases: 6, phaseTime: 25 }, // PV2 (§2.3) — layout real via br_vila_layout.json",
        'E1 config br_vila')

# E2 — estado global do BR
g = rep(g,
        "let selectedModeId = 'dm_3v3';                      // default do lobby (decisao #1 do plano)",
        "let selectedModeId = 'dm_3v3';                      // default do lobby (decisao #1 do plano)\n"
        "let brState = null;                                 // PV2: estado do BR (zona 結界/baús/vivos) — null fora do modo",
        'E2 brState global')

# E3 — branch BR no startMatch + cleanup visual em modos normais
g = rep(g,
        "  const others = rosterMeta.filter(h => h.id !== playerHero.id);",
        "  const others = rosterMeta.filter(h => h.id !== playerHero.id);\n"
        "  document.body.classList.toggle('br-mode', CFG.mode === 'br'); // PV2: gate CSS do HUD BR\n"
        "  if (CFG.mode === 'br') { await startBRMatch(CFG, playerHero, others); return; } // PV2: branch total — spawn solo na vila\n"
        "  cleanupBRVisuals(); // PV2: partida DM nova — remove zona/baús de um BR anterior",
        'E3 branch BR startMatch')

# E4 — santuários só fora do BR
g = rep(g,
        "  createBaseSanctuary(basePos('blue').x, basePos('blue').z, 0x3b82f6);\n"
        "  createBaseSanctuary(basePos('red').x, basePos('red').z, 0xef4444);",
        "  if (activeMatchCfg.mode !== 'br') { // PV2: BR nao tem bases — a vila e' o mapa\n"
        "    createBaseSanctuary(basePos('blue').x, basePos('blue').z, 0x3b82f6);\n"
        "    createBaseSanctuary(basePos('red').x, basePos('red').z, 0xef4444);\n"
        "  }",
        'E4 santuarios gate')

# E5a — deadTimer null-safe (BR usa 6.0 apenas pela anim down)
g = rep(g,
        "    target.deadTimer = activeMatchCfg.respawn; // respawn por modo (legacy 6s, 3v3 5s)",
        "    target.deadTimer = activeMatchCfg.respawn != null ? activeMatchCfg.respawn : 6.0; // respawn por modo (legacy 6s, 3v3 5s; PV2: BR = anim down normal, rebirth gate torna permanente)",
        'E5a deadTimer BR')

# E5b — label de morte BR (dealDamage)
g = rep(g,
        "        <div class=\"ko-label-world\">☠️ K.O.</div>\n"
        "        <div class=\"respawn-timer-world\">蘇生 ${Math.ceil(target.deadTimer)}s</div>",
        "        ${activeMatchCfg.respawn == null ? '<div class=\"ko-label-world\">☠️ ELIMINADO</div>' : `<div class=\"ko-label-world\">☠️ K.O.</div><div class=\"respawn-timer-world\">蘇生 ${Math.ceil(target.deadTimer)}s</div>`}",
        'E5b label morte BR')

# E5c — label de morte BR (tick do corpo)
g = rep(g,
        "          <div class=\"ko-label-world\">☠️ K.O.</div>\n"
        "          <div class=\"respawn-timer-world\">蘇生 ${Math.ceil(u.deadTimer)}s</div>",
        "          ${activeMatchCfg.respawn == null ? '<div class=\"ko-label-world\">☠️ ELIMINADO</div>' : `<div class=\"ko-label-world\">☠️ K.O.</div><div class=\"respawn-timer-world\">蘇生 ${Math.ceil(u.deadTimer)}s</div>`}",
        'E5c label tick BR')

# E6 — rebirth gate (morte permanente no BR)
g = rep(g,
        "      if (u.deadTimer <= 0) {\n"
        "        u.spawnShield = 4.0; // SPAWN GUARD",
        "      if (u.deadTimer <= 0) {\n"
        "        if (activeMatchCfg.respawn == null) { // PV2: BR — morte permanente (nao renasce)\n"
        "          u.deadTimer = 999;\n"
        "          u.mesh.visible = false;\n"
        "          if (u.labelEl) { u.labelEl.style.display = 'flex'; u.labelEl.classList.add('dead'); u.labelEl.innerHTML = '<div class=\"ko-label-world\">☠️ ELIMINADO</div>'; }\n"
        "        } else {\n"
        "        u.spawnShield = 4.0; // SPAWN GUARD",
        'E6a rebirth gate')
g = rep(g,
        "        renderTopTeamPortraits();\n"
        "        updateScoreboardTables();\n"
        "      }\n"
        "      continue;",
        "        renderTopTeamPortraits();\n"
        "        updateScoreboardTables();\n"
        "        } // PV2: fim do else (respawn normal)\n"
        "      }\n"
        "      continue;",
        'E6b rebirth else close')

# E7 — fim de tempo BR (sem prorrogação)
g = rep(g,
        "  } else if (matchTimeRemaining <= 0) {\n"
        "    if (scoreBlue === scoreRed && !matchOvertime) {",
        "  } else if (matchTimeRemaining <= 0) {\n"
        "    if (activeMatchCfg.mode === 'br') { // PV2: BR nao tem prorrogacao — decide por vivos/HP\n"
        "      const _alive = units.filter(u => u.deadTimer <= 0);\n"
        "      if (_alive.length === 1) brEndMatch(_alive[0].isPlayer, 'ÚLTIMO DE PÉ');\n"
        "      else {\n"
        "        const _best = _alive.slice().sort((a, b) => (b.hp / b.maxHp) - (a.hp / a.maxHp))[0];\n"
        "        brEndMatch(!!(_best && _best.isPlayer), 'TEMPO ESGOTADO');\n"
        "      }\n"
        "      return;\n"
        "    }\n"
        "    if (scoreBlue === scoreRed && !matchOvertime) {",
        'E7 timeout BR')

# E8 — tick do BR no updateMatch
g = rep(g,
        "  // Central Scroll Shrine Buff Orb",
        "  // PV2: tick do modo Realeza na Vila (zona/baús/last-standing)\n"
        "  if (activeMatchCfg && activeMatchCfg.mode === 'br' && brState && matchActive && !matchEnding) updateBR(dt);\n"
        "\n"
        "  // Central Scroll Shrine Buff Orb",
        'E8 updateBR tick')

# E9 — __matchState.br p/ E2E
g = rep(g,
        "  get time() { return matchTimeRemaining; },",
        "  get time() { return matchTimeRemaining; },\n"
        "  get br() { return brState; }, // PV2: estado BR p/ E2E",
        'E9 matchstate br')

# E10 — bloco PV2 (append no fim do game.js)
PV2_BLOCK = '''

// ============================================================================
// PV2: REALEZA NA VILA — modo battle royale solo na Vila Konoha (sa00z)
// Layout real de spawns/baús/zona via assets/data/br_vila_layout.json (raycast)
// ============================================================================

function cleanupBRVisuals() {
  if (brState) {
    if (brState.zoneMesh) { try { arenaGroup.remove(brState.zoneMesh); } catch (e) {} }
    for (const ch of (brState.chests || [])) { try { arenaGroup.remove(ch.mesh); } catch (e) {} }
  }
  brState = null;
}

async function startBRMatch(CFG, playerHero, others) {
  let layout = null;
  try {
    layout = await fetch('assets/data/br_vila_layout.json?v=9').then(r => r.json());
  } catch (e) { console.warn('[PV2] layout BR indisponivel — usando anel geometrico', e); }
  const ring = (layout && Array.isArray(layout.spawnRing) && layout.spawnRing.length >= CFG.players)
    ? layout.spawnRing : null;
  const roster = [playerHero, ...others.slice(0, CFG.players - 1)];
  const meshes = await Promise.all(roster.map(h2 => loadCharacter3DModel(h2.id)));
  const zoneStart = (layout && layout.zoneRadiusStart) || CFG.zoneStart || 65;
  brState = {
    phase: 0,
    zoneTimer: CFG.phaseTime || 25,
    zoneR: zoneStart,
    zoneTargetR: zoneStart,
    zoneStart,
    zoneMin: (layout && layout.zoneRadiusMin) || CFG.zoneMin || 6,
    zonePhases: CFG.zonePhases || 6,
    center: (layout && layout.zoneCenter) || { x: 0, z: 0 },
    damageTick: 1.0,
    chests: [],
    zoneMesh: null,
    alive: roster.length
  };
  for (let i = 0; i < roster.length; i++) {
    const h2 = roster[i];
    const isPlayer = i === 0;
    const mesh = meshes[i];
    const ringGeo = new THREE.RingGeometry(1.45, 1.85, 32);
    const ringColor = isPlayer ? 0x22c55e : 0xa855f7;
    const ringMesh = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: ringColor, side: THREE.DoubleSide }));
    ringMesh.rotation.x = -Math.PI / 2;
    ringMesh.position.y = 0.08;
    mesh.add(ringMesh);
    const auraMesh = createHeroAwakeningAuraMesh(h2.id, h2.color || 0xff7b00);
    auraMesh.visible = false;
    mesh.add(auraMesh);
    const sp = ring ? ring[i] : { x: Math.cos(i / roster.length * Math.PI * 2) * (zoneStart * 0.8), z: Math.sin(i / roster.length * Math.PI * 2) * (zoneStart * 0.8) };
    mesh.position.set(sp.x, 0, sp.z);
    arenaGroup.add(mesh);
    const labelEl = document.createElement('div');
    labelEl.className = `unit-label ${isPlayer ? 'player' : 'red'}`;
    labelEl.innerHTML = `
      <span class="u-name">${isPlayer ? '★ ' + h2.name : h2.name.split(' ')[0]} <small class="u-lvl">Lv.1</small></span>
      <div class="u-hp-bg"><div class="u-hp-fill" style="width:100%"></div></div>
      <div class="u-ck-bg"><div class="u-ck-fill" style="width:100%"></div></div>
    `;
    document.getElementById('world-labels').appendChild(labelEl);
    const kit = HERO_KITS[h2.id] || HERO_KITS['1nrt'];
    const hs = HERO_STATS[h2.id] || HERO_STATS.__d;
    units.push({
      id: `solo_${i}`,
      heroId: h2.id,
      name: h2.name,
      portrait: h2.portrait,
      team: `solo_${i}`,
      isPlayer,
      mesh, auraMesh, labelEl, kit,
      x: sp.x, z: sp.z, spawnX: sp.x, spawnZ: sp.z,
      rotY: Math.atan2(brState.center.z - sp.z, brState.center.x - sp.x),
      hp: Math.round(hs.hp * HERO_HP_SCALE),
      maxHp: Math.round(hs.hp * HERO_HP_SCALE),
      chakra: 100, maxChakra: 100,
      level: 1, kills: 0, deaths: 0, assists: 0, killStreak: 0, lastKillAt: 0,
      speed: (isPlayer ? 21.5 : 19.5) * hs.spd,
      state: 'idle', animTimer: 0, animDuration: 0,
      comboStep: 0, comboResetTimer: 0, awakenedTimer: 0, deadTimer: 0, spawnShield: 3.0,
      cds: { atk: 0, q: 0, w: 0, e: 0, r: 0 },
      aiTarget: null, aiStrafeDir: Math.random() < 0.5 ? 1 : -1
    });
  }
  const player = units.find(u => u.isPlayer);
  if (player) { tpCamYaw = player.rotY; tpCamPitch = 0.32; }
  setupHUDPlayerInfo(playerHero);
  renderTopTeamPortraits();
  // Zona 結界 — cilindro translúcido (roxo chakra), escala = raio atual
  const zoneGeo = new THREE.CylinderGeometry(1, 1, 40, 64, 1, true);
  const zoneMat = new THREE.MeshBasicMaterial({ color: 0xa855f7, transparent: true, opacity: 0.22, side: THREE.DoubleSide, depthWrite: false });
  brState.zoneMesh = new THREE.Mesh(zoneGeo, zoneMat);
  brState.zoneMesh.scale.set(brState.zoneR, 1, brState.zoneR);
  brState.zoneMesh.position.set(brState.center.x, 18, brState.center.z);
  arenaGroup.add(brState.zoneMesh);
  // Baús de chakra nas posições reais do layout
  const chestGeo = new THREE.BoxGeometry(1.6, 1.2, 1.2);
  const chestMat = new THREE.MeshBasicMaterial({ color: 0xf59e0b });
  const chestPos = (layout && Array.isArray(layout.chests)) ? layout.chests : [];
  for (const cp of chestPos) {
    const cm = new THREE.Mesh(chestGeo, chestMat);
    cm.position.set(cp.x, 0.9, cp.z);
    arenaGroup.add(cm);
    brState.chests.push({ x: cp.x, z: cp.z, mesh: cm, taken: false, bob: Math.random() * Math.PI * 2 });
  }
  const _goalEl = document.querySelector('.match-goal-txt');
  if (_goalEl) _goalEl.textContent = 'SOBREVIVA · ÚLTIMO DE PÉ';
  updateBRHUD();
  playMatchIntro([playerHero], [roster.slice(1)]); // PV2: intro 1 vs todos — banner custom via activeMatchCfg
}

function updateBRHUD() {
  const el = document.getElementById('br-alive');
  const ph = document.getElementById('br-phase');
  if (el) renderSkinDigits(el, String(brState ? brState.alive : 0));
  if (ph) ph.textContent = brState ? `FASE ${Math.min(brState.phase, brState.zonePhases)}/${brState.zonePhases}` : '';
}

function brEndMatch(playerWon, reason) {
  if (matchEnding) return;
  scoreBlue = playerWon ? 1 : 0;
  scoreRed = playerWon ? 0 : 1;
  endMatch(playerWon ? `REALEZA NA VILA — ${reason}! VITÓRIA!` : `REALEZA NA VILA — ${reason}... DERROTA`);
}

function updateBR(dt) {
  const alive = units.filter(u => u.deadTimer <= 0);
  brState.alive = alive.length;
  updateBRHUD();
  // ---- Zona 結界: fases + encolhimento contínuo ----
  if (brState.phase < brState.zonePhases) {
    brState.zoneTimer -= dt;
    if (brState.zoneTimer <= 0) {
      brState.phase++;
      brState.zoneTimer = 25;
      const span = brState.zoneStart - brState.zoneMin;
      brState.zoneTargetR = Math.max(brState.zoneMin, brState.zoneStart - brState.phase * span / brState.zonePhases);
      showBanner(brState.phase >= brState.zonePhases
        ? '結界 FINAL! NENHUM ESCONDERIJO!'
        : `結界 ESTÁ ENCOLHENDO — FASE ${brState.phase}/${brState.zonePhases}`, 2000);
    }
    const shrinkSpeed = (brState.zoneStart - brState.zoneMin) / (25 * brState.zonePhases);
    brState.zoneR = Math.max(brState.zoneTargetR, brState.zoneR - dt * shrinkSpeed);
    if (brState.zoneMesh) brState.zoneMesh.scale.set(brState.zoneR, 1, brState.zoneR);
  }
  // ---- Dano fora da zona (chakra drain 結界) ----
  brState.damageTick -= dt;
  if (brState.damageTick <= 0) {
    brState.damageTick = 1.0;
    for (const u of alive) {
      const d = Math.hypot(u.x - brState.center.x, u.z - brState.center.z);
      if (d > brState.zoneR + 1.5) dealDamage(u, u, 2 + brState.phase, '結界');
    }
  }
  // ---- Baús: bob visual + coleta por proximidade ----
  for (const ch of brState.chests) {
    if (ch.taken) continue;
    ch.bob += dt * 2.4;
    ch.mesh.position.y = 0.9 + Math.sin(ch.bob) * 0.18;
    ch.mesh.rotation.y += dt * 1.2;
    for (const u of alive) {
      if (Math.hypot(u.x - ch.x, u.z - ch.z) < 2.6) {
        ch.taken = true;
        ch.mesh.visible = false;
        spawnSmokePuff(ch.x, 1.2, ch.z, 2.5);
        u.hp = Math.min(u.maxHp, u.hp + 35);
        u.chakra = Math.min(u.maxChakra, u.chakra + 50);
        if (u.isPlayer) showBanner('BAÚ DE CHAKRA! +35 HP · +50 CHAKRA', 1400);
        break;
      }
    }
  }
  // ---- Last standing ----
  if (alive.length <= 1 && !matchEnding) {
    const winner = alive[0];
    if (winner && winner.isPlayer) brEndMatch(true, 'ÚLTIMO DE PÉ');
    else brEndMatch(false, winner ? `${winner.name} VENCEU` : 'TODOS CAÍRAM');
  }
}
'''
g = g.rstrip() + '\n' + PV2_BLOCK

open(GJ, 'w', encoding='utf-8', newline='').write(g)
print('[ok] game.js: E1-E10 aplicados')

# ============ index.html ============
h = rep(h,
        '<button type="button" class="mode-chip" data-mode="br_vila" disabled>REALEZA NA VILA<small>em breve · PV2</small></button>',
        '<button type="button" class="mode-chip" data-mode="br_vila">REALEZA NA VILA<small>10 ninjas · zona 結界 · solo</small></button>',
        'H1 chip BR')
h = rep(h,
        '<span class="match-goal-txt">META: 30 ABATES</span>',
        '<span class="match-goal-txt">META: 30 ABATES</span>\r\n'
        '          <div id="br-hud"><span class="br-alive-label">VIVOS</span> <span id="br-alive" data-digits="true">10</span> <span class="br-phase" id="br-phase">FASE 0/6</span></div>',
        'H2 br-hud')
open(HTML, 'w', encoding='utf-8', newline='').write(h)
print('[ok] index.html: chip BR habilitado + #br-hud')

# ============ styles.css ============
CSS_BLOCK = '''\r\n
/* ==== PV2: REALEZA NA VILA (docs/PIVOT_MOBILE.md §PV2) ==== */
#br-hud { display: none; }
body.br-mode #hud-screen.active #br-hud {
  display: inline-flex; align-items: center; gap: 10px;
  font-family: 'Storm Title', 'Poppins', sans-serif; font-size: 13px;
  color: #e9d5ff; letter-spacing: 1px; text-shadow: 0 0 8px rgba(168, 85, 247, 0.6);
}
body.br-mode #hud-screen.active #br-hud .br-alive-label { opacity: 0.8; font-size: 11px; }
body.br-mode #hud-screen.active #br-hud .br-phase { color: #c4b5fd; font-size: 11px; opacity: 0.9; }
body.br-mode #hud-screen.active .team-group.blue,
body.br-mode #hud-screen.active .team-group.red { display: none; } /* BR e solo — sem placar de times */
body.br-mode #player-death-overlay { display: none !important; } /* BR: sem overlay de respawn */
'''
c = c.rstrip() + CSS_BLOCK
open(CSS, 'w', encoding='utf-8', newline='').write(c)
print('[ok] styles.css: gates PV2')

# ============ verificações ============
import json  # noqa: E402
import subprocess  # noqa: E402
r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] node --check limpo')
lay = json.load(open('public/assets/data/br_vila_layout.json', encoding='utf-8'))
assert len(lay['spawnRing']) == 10, 'layout precisa de 10 spawns'
print(f"[ok] layout: {len(lay['spawnRing'])} spawns, zona {lay['zoneRadiusStart']}->{lay['zoneRadiusMin']}, {len(lay['chests'])} baús")
print('PV2 PATCH DONE')
