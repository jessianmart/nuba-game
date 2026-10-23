"""W5-SFX: SFX/vozes autênticos posicionados na batalha — nada de som genérico.

Cada edicao tem assert count==1 com fallback CRLF->LF, backup .bak_w5sfx,
autoverificacao pos-write (contagem de marcadores) e node --check no final.

Principios (pedido do usuario):
  - Som CORRETO por momento de batalha: impacto=kunai_hit/punch_hit/kick_hit,
    queda pesada=ground_hit, KO=down+ko, cast=voz do heroi (SKILL_SFX_MAP),
    ressurreicao=stand_up, baú=box_open+chakura_get, fim de awakening=awake_off,
    ult pronto=max_gauge. ZERO bleeps sintetizados em batalha.
  - Volume OBDEDECE a distancia: AUTH_SFX.playAt(name, x, z) — falloff
    pow(1 - d/60, 1.2)*1.4 a partir da camera (window.__camera, PV4.2);
    abaixo de 0.06 vira silencio (luta distante some).
Run: python tools/w_sfx_patcher.py   (cwd = repo root)
"""
import subprocess

GAME = 'public/game.js'
MARK = 'W5:'
import shutil
shutil.copy2(GAME, GAME + '.bak_w5sfx')
s = open(GAME, encoding='utf-8', newline='').read()


def rep(old, new, label):
    """Substituicao com fallback de final de linha e assert de unicidade."""
    global s
    for sep in ('\r\n', '\n'):
        o, n = old.replace('\n', sep), new.replace('\n', sep)
        c = s.count(o)
        if c == 1:
            s = s.replace(o, n, 1)
            print(f'[ok] {label}')
            return
        if c > 1:
            raise SystemExit(f'[{label}] ANCORO DUPLICADA ({c})')
    raise SystemExit(f'[{label}] ANCORO NAO ENCONTRADA')


# E0: THROTTLE — novos cues com limites proprios
rep("""  THROTTLE: { ko: 450, down: 250, dash: 220, hit_s: 90, punch_hit: 110, kick_hit: 110, menu_slct: 60 },""",
    """  THROTTLE: { ko: 450, down: 250, dash: 220, hit_s: 90, punch_hit: 110, kick_hit: 110, menu_slct: 60, kunai_swing: 90, shuriken: 110, kunai_hit: 60, ground_hit: 240, box_open: 1200, awake_off: 1500 },""",
    'E0 THROTTLE')

# E1: playAt + pick dentro de AUTH_SFX (antes do fechamento do objeto)
rep("""    this._last[name] = now;
    this.log.push(name); if (this.log.length > 14) this.log.shift();
    return true;
  }
};""",
    """    this._last[name] = now;
    this.log.push(name); if (this.log.length > 14) this.log.shift();
    return true;
  },
  playAt(name, x, z, opts) { // W5: SFX autêntico posicionado — volume obedece à distância da câmera
    const cam = window.__camera;
    if (!cam) return this.play(name, opts);
    const d = Math.hypot(cam.position.x - (x || 0), cam.position.z - (z || 0));
    const base = (opts && opts.vol) || 1;
    const v = Math.pow(1 - Math.min(d / 60, 1), 1.2) * 1.4 * base;
    if (v < 0.06) return false;
    const played = this.play(name, { vol: Math.min(v, 1), min: opts && opts.min });
    if (played) { this.lastPlays = this.lastPlays || []; this.lastPlays.push({ n: name, v: Math.round(Math.min(v, 1) * 100) / 100, d: Math.round(d) }); if (this.lastPlays.length > 24) this.lastPlays.shift(); }
    return played;
  },
  pick(a, b) { this._alt = this._alt || {}; this._alt[a] = !this._alt[a]; return this._alt[a] ? a : b; } // W5: variação hit1/hit2
};""",
    'E1 playAt/pick')

# E2: dealDamage — impacto posicionado + tombo pesado em dano alto
rep("""  sfx.hit();
  AUTH_SFX.play('hit_s', { vol: 0.55 }); // W1.1""",
    """  AUTH_SFX.playAt('hit_s', target.x, target.z, { vol: 0.55 }); // W5: impacto posicionado
  if (dmg >= 180) AUTH_SFX.playAt(AUTH_SFX.pick('ground_hit', 'ground_hit2'), target.x, target.z, { vol: 0.85, min: 260 }); // W5: tombo pesado autêntico""",
    'E2 dealDamage impacto')

# E3: morte — down/ko posicionados
rep("""    AUTH_SFX.play('down', { vol: 0.8 }); AUTH_SFX.play('ko', { vol: 0.9 }); // W1.1""",
    """    AUTH_SFX.playAt('down', target.x, target.z, { vol: 0.8 }); AUTH_SFX.playAt('ko', target.x, target.z, { vol: 0.9 }); // W5: KO posicionado""",
    'E3 down/ko')

# E4: remove sfx.ko() genérico duplicado
rep("""    // SFX: Dramatic KO defeat audio
    sfx.ko();""",
    """    // W5: genérico removido — 'down'+'ko' autênticos tocam posicionados acima""",
    'E4 remove sfx.ko')

# E5: melee — punch/kick autênticos com variação, no alvo
rep("""        if (hitIdx === 2) sfx.kick();
        else { sfx.hit(); if (hitIdx === 3) sfx.kick(); }
        AUTH_SFX.play(hitIdx === 2 ? 'kick_hit' : 'punch_hit', { vol: 0.6 }); // W1.1""",
    """        AUTH_SFX.playAt(hitIdx === 2 ? AUTH_SFX.pick('kick_hit', 'kick_hit2') : AUTH_SFX.pick('punch_hit', 'punch_hit2'), meleeTarget.x, meleeTarget.z, { vol: 0.62 }); // W5: soco/chute autêntico com variação""",
    'E5 melee punch/kick')

# E6: arremesso — kunai_swing (golpe 1) / shuriken (2-3), posicionado
rep("""      if (unit.isPlayer) sfx.shuriken();""",
    """      AUTH_SFX.playAt(hitIdx === 1 ? 'kunai_swing' : 'shuriken', unit.x, unit.z, { vol: hitIdx === 1 ? 0.7 : 0.75 }); // W5: arremesso autêntico por golpe""",
    'E6 arremesso')

# E7: remove genéricos de cast (vozes por herói já tocam via SKILL_SFX_MAP)
rep("""  // Ninjutsu / Kawarimi / Ultimate Audio
  if (unit.isPlayer) {
    if (slot === 'r') sfx.ultimate();
    else if (slot === 'e') sfx.kawarimi();
    else sfx.jutsu();
  }""",
    """  // W5: genéricos de cast removidos — vozes autênticas do herói tocam via SKILL_SFX_MAP""",
    'E7 remove cast genérico')

# E8: vozes de cast posicionadas + swing alternado no atk
rep("""  if (_authSfx) AUTH_SFX.play(_authSfx, { vol: 0.8 });
  else if (slot === 'atk') AUTH_SFX.play('punch_swing', { vol: 0.5 });""",
    """  if (_authSfx) AUTH_SFX.playAt(_authSfx, unit.x, unit.z, { vol: 0.8 }); // W5: voz do herói posicionada
  else if (slot === 'atk') AUTH_SFX.playAt(AUTH_SFX.pick('punch_swing', 'kick_swing'), unit.x, unit.z, { vol: 0.5 }); // W5: swing alternado""",
    'E8 cast voices')

# E9: dash posicionado
rep("""    AUTH_SFX.play('dash', { vol: 0.5 }); // W1.1""",
    """    AUTH_SFX.playAt('dash', unit.x, unit.z, { vol: 0.5 }); // W5: dash posicionado""",
    'E9 dash')

# E10: awakening aberto posicionado
rep("""    AUTH_SFX.play('awake_open', { vol: 0.9 }); AUTH_SFX.play('awake_flash', { vol: 0.8 }); // W1.1""",
    """    AUTH_SFX.playAt('awake_open', unit.x, unit.z, { vol: 0.9 }); AUTH_SFX.playAt('awake_flash', unit.x, unit.z, { vol: 0.8 }); // W5: awakening posicionado""",
    'E10 awake open')

# E11: level up posicionado
rep("""    AUTH_SFX.play('level_up', { vol: 0.75 }); // W1.1""",
    """    AUTH_SFX.playAt('level_up', attacker.x, attacker.z, { vol: 0.75 }); // W5: level up posicionado""",
    'E11 level up')

# E12: ressurreição autêntica
rep("""        // Resurrect Audio SFX
        sfx.resurrect();""",
    """        // W5: ressurreição autêntica posicionada
        AUTH_SFX.playAt(AUTH_SFX.pick('stand_up1', 'stand_up2'), u.x, u.z, { vol: 0.85, min: 900 });""",
    'E12 resurrect')

# E13: ult pronto — sting uma única vez (player)
rep("""    u.chakra = Math.min(u.maxChakra, u.chakra + dt * 5.5);""",
    """    u.chakra = Math.min(u.maxChakra, u.chakra + dt * 5.5);
    const _ultReady = u.isPlayer && u.chakra >= u.maxChakra && u.cds.r <= 0; // W5: ult pronto (anuncia 1x)
    if (_ultReady && !u._ultReadyAnnounced) AUTH_SFX.playAt('max_gauge', u.x, u.z, { vol: 0.85, min: 2500 });
    u._ultReadyAnnounced = _ultReady;""",
    'E13 max_gauge')

# E14: fim do awakening
rep("""      if (u.awakenedTimer <= 0) u.auraMesh.visible = false;""",
    """      if (u.awakenedTimer <= 0) { u.auraMesh.visible = false; AUTH_SFX.playAt('awake_off', u.x, u.z, { vol: 0.7, min: 1500 }); } // W5: fim do awakening""",
    'E14 awake_off')

# E15: impacto de projétil metálico autêntico (era menu select!)
rep("""          if (p.owner.isPlayer && (p.type === 'shuriken' || p.type === 'kunai')) {
            sfx.clink(); // Metallic ninja weapon impact clink!
          }""",
    """          if (p.type === 'shuriken' || p.type === 'kunai') {
            AUTH_SFX.playAt(AUTH_SFX.pick('kunai_hit', 'kunai_hit2'), target.x, target.z, { vol: 0.7, min: 60 }); // W5: impacto metálico autêntico
          }""",
    'E15 kunai_hit')

# E16: projétil que erra crava longe (som posicional sutil)
rep("""    if (hit || p.life <= 0) {
      arenaGroup.remove(p.mesh);""",
    """    if (hit || p.life <= 0) {
      if (!hit && (p.type === 'kunai' || p.type === 'shuriken')) AUTH_SFX.playAt('kunai_hit_wall', p.x, p.z, { vol: 0.4, min: 400 }); // W5: crava no chão
      arenaGroup.remove(p.mesh);""",
    'E16 kunai_hit_wall')

# E17: baú do BR autêntico
rep("""        ch.taken = true;
        ch.mesh.visible = false;""",
    """        ch.taken = true;
        ch.mesh.visible = false;
        AUTH_SFX.playAt('box_open', ch.x, ch.z, { vol: 0.9, min: 1200 }); AUTH_SFX.playAt('chakura_get', ch.x, ch.z, { vol: 0.8, min: 1200 }); // W5: baú BR autêntico""",
    'E17 chest BR')

# E18: lobby — card click autêntico
rep("""      sfx.init();
      sfx.hit();""",
    """      sfx.init();
      AUTH_SFX.play('menu_slct', { vol: 0.6 }); // W5: UI autêntica""",
    'E18 lobby card')

# E19: pose toggle autêntico
rep("""    sfx.init();
    sfx.jutsu();""",
    """    sfx.init();
    AUTH_SFX.play('menu_fix', { vol: 0.7 }); // W5: UI autêntica""",
    'E19 pose btn')

# E20: botão de chakra (cheat) autêntico
rep("""        sfx.jutsu();""",
    """        AUTH_SFX.play('chakura_use', { vol: 0.7 }); // W5: chakra autêntico""",
    'E20 chakra btn')

# E21: chip de arena sem fallback genérico
rep("""      sfx.click ? sfx.click() : sfx.hit();""",
    """      sfx.click(); // W5: sem fallback genérico""",
    'E21 arena chip')

open(GAME, 'w', encoding='utf-8', newline='').write(s)

# ---- autoverificacao pos-escrita ----
s2 = open(GAME, encoding='utf-8', newline='').read()
n = s2.count(MARK)
assert n >= 20, f'so {n} marcadores W5:'
for gone in ['sfx.hit();', 'sfx.ko();', 'sfx.shuriken();', 'sfx.ultimate();', 'sfx.kawarimi();', 'sfx.resurrect();', 'sfx.jutsu();']:
    assert gone not in s2, f'generico ainda presente: {gone}'
for must in ['playAt(name, x, z, opts)', 'kunai_hit', 'box_open', 'awake_off', 'max_gauge', 'stand_up1']:
    assert must in s2, f'hook ausente: {must}'
print(f'[SELF-CHECK] {n} marcadores W5; zero chamadas genericas de batalha')

r = subprocess.run(['node', '--check', GAME], capture_output=True, text=True)
print('[node --check]', 'OK' if r.returncode == 0 else r.stderr[:400])
raise SystemExit(0 if r.returncode == 0 else 1)
