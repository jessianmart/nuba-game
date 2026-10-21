"""PV1-A — MATCH_CONFIGS + startMatch(id) + modo Combate 3v3 (docs/PIVOT_MOBILE.md §2.2, decisao #1).

- start5v5Match -> startMatch(configId) com configs por modo; alias legacy preserva contrato E2E
- dm_3v3: 3+3 ninjas, 15 abates, 3:00, respawn 5s, prorrogacao 30s (T5 reusado)
- dm_legacy_5v5: comportamento byte-a-byte do jogo atual (5+5, 30, 5:00, 6s, 60s)
- Seletor de modo no lobby (#mode-picker): 3v3 default, 5v5 classico, BR "em breve"
- Banner em playMatchIntro usa activeMatchCfg (escopo global — CFG nao existe la)

Run:  python pv1a_match_configs_patch.py   (cwd = repo root)
Backups: public/{game.js,index.html,styles.css}.bak_pv1a
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

# ================= game.js =================
g = rd('public/game.js')
backup('public/game.js', 'pv1a')

# 1. MATCH_CONFIGS apos TARGET_KILLS
g = sub1(
    g,
    'const TARGET_KILLS = 30;',
    '''const TARGET_KILLS = 30;

// ============================================================================
// PV1.1 MATCH CONFIGS (docs/PIVOT_MOBILE.md §2.2 — decisao #1: dm_3v3 e' o default)
// ============================================================================
const MATCH_CONFIGS = {
  dm_3v3:        { label: 'COMBATE 3v3', teamSize: 3, killTarget: 15, time: 180, respawn: 5,  overtime: 30, mode: 'dm' },
  dm_legacy_5v5: { label: 'COMBATE 5v5', teamSize: 5, killTarget: 30, time: 300, respawn: 6,  overtime: 60, mode: 'dm' },
  br_vila:       { label: 'REALEZA NA VILA', mode: 'br', arena: 'sd00a', players: 10, squad: 1 } // PV2 (§2.3)
};
let activeMatchCfg = MATCH_CONFIGS.dm_legacy_5v5;   // modo atual (global — playMatchIntro/tick leem)
let lastMatchConfigId = 'dm_legacy_5v5';           // revanche reusa o modo da partida anterior
let selectedModeId = 'dm_3v3';                      // default do lobby (decisao #1 do plano)''',
    'MATCH_CONFIGS')

# 2. funcao -> startMatch(configId) com resolucao de config
g = sub1(
    g,
    'async function start5v5Match() {',
    '''async function startMatch(configId) {
  const CFG = MATCH_CONFIGS[configId] || MATCH_CONFIGS.dm_legacy_5v5;
  activeMatchCfg = CFG;
  lastMatchConfigId = MATCH_CONFIGS[configId] ? configId : 'dm_legacy_5v5';''',
    'startMatch signature')

# 3. tempo por config (o 'let matchTimeRemaining = 300; // 5:00' do topo NAO e' tocado)
g = sub1(g, '  matchTimeRemaining = 300;',
         '  matchTimeRemaining = CFG.time;', 'match time reset')

# 4. roster por teamSize
g = sub1(
    g,
    '  const blueRoster = [playerHero, ...others.slice(0, 4)];\n  const redRoster = others.slice(4, 9);',
    '  const blueRoster = [playerHero, ...others.slice(0, CFG.teamSize - 1)];\n'
    '  const redRoster = others.slice(CFG.teamSize - 1, 2 * CFG.teamSize - 1);',
    'roster slices')

# 5. circulo de spawn por tamanho real do time
g = sub1(g, '  const offsetAngle = (i / 5) * Math.PI * 2;',
         '  const offsetAngle = (i / teamRoster.length) * Math.PI * 2;',
         'spawn circle')

# 6. goal dinamico no HUD (F04 le no legacy: continua "META: 30 ABATES")
g = sub1(g, '  matchSuddenDeath = false; // T5',
         '''  matchSuddenDeath = false; // T5
  const _goalEl = document.querySelector('.match-goal-txt');
  if (_goalEl) _goalEl.textContent = `META: ${CFG.killTarget} ABATES`;''',
         'goal text update')

# 7. banner em playMatchIntro — escopo global activeMatchCfg (2 ocorrencias identicas)
banner_old = 'showBanner(`COMBATE 5v5 EM ${ARENA.label.toUpperCase()} INICIADO! META: ${TARGET_KILLS} ABATES`);'
banner_new = 'showBanner(`${activeMatchCfg.label} EM ${ARENA.label.toUpperCase()} INICIADO! META: ${activeMatchCfg.killTarget} ABATES`);'
nb = g.count(banner_old)
assert nb == 2, f'banner: esperava 2 ocorrencias, achei {nb}'
g = g.replace(banner_old, banner_new)
ok.append('banner playMatchIntro -> activeMatchCfg.label/killTarget (x2)')

# 8. checagem de vitoria por config
g = sub1(g, '    } else if (scoreBlue >= TARGET_KILLS || scoreRed >= TARGET_KILLS) {',
         '    } else if (scoreBlue >= activeMatchCfg.killTarget || scoreRed >= activeMatchCfg.killTarget) {',
         'kill target check')
g = sub1(g, "      endMatch(scoreBlue >= TARGET_KILLS ? 'VITÓRIA DO TIME KONOHA AZUL!' : 'VITÓRIA DO TIME RIVAL VERMELHO!');",
         "      endMatch(scoreBlue >= activeMatchCfg.killTarget ? 'VITÓRIA DO TIME KONOHA AZUL!' : 'VITÓRIA DO TIME RIVAL VERMELHO!');",
         'victory endMatch')

# 9. prorrogacao por modo
g = sub1(g, '      matchTimeRemaining = 60; // T5: prorrogacao de 1 minuto',
         '      matchTimeRemaining = activeMatchCfg.overtime; // T5: prorrogacao por modo (legacy 60s, 3v3 30s)',
         'overtime')

# 10. respawn por modo
g = sub1(g, '    target.deadTimer = 6.0; // 6s respawn countdown total',
         '    target.deadTimer = activeMatchCfg.respawn; // respawn por modo (legacy 6s, 3v3 5s)',
         'respawn timer')

# 11. btn-arena-play -> modo selecionado
g = sub1(
    g,
    '''  const btnArenaPlay = document.getElementById('btn-arena-play');
  if (btnArenaPlay) {
    btnArenaPlay.addEventListener('click', () => {
      sfx.init();
      sfx.click();
      start5v5Match();
    });
  }''',
    '''  const btnArenaPlay = document.getElementById('btn-arena-play');
  if (btnArenaPlay) {
    btnArenaPlay.addEventListener('click', () => {
      sfx.init();
      sfx.click();
      startMatch(selectedModeId);
    });
  }''',
    'btn-arena-play')

# 12. btn-start-match -> modo selecionado + wiring do #mode-picker
g = sub1(
    g,
    '''  document.getElementById('btn-start-match').addEventListener('click', () => {
    start5v5Match();
  });''',
    '''  document.getElementById('btn-start-match').addEventListener('click', () => {
    startMatch(selectedModeId);
  });

  // PV1.1: seletor de modo (#mode-picker) — decisao #1: 3v3 default
  document.querySelectorAll('#mode-picker .mode-chip').forEach(ch => {
    ch.addEventListener('click', () => {
      if (ch.disabled) return;
      selectedModeId = ch.dataset.mode;
      document.querySelectorAll('#mode-picker .mode-chip').forEach(c => c.classList.toggle('selected', c === ch));
      sfx.click();
    });
  });''',
    'btn-start-match + mode picker wiring')

# 13. revanche reusa o modo anterior
g = sub1(
    g,
    '  if (btnRematch) btnRematch.onclick = () => { hideMatchResults(); matchEnding = false; start5v5Match(); };',
    '  if (btnRematch) btnRematch.onclick = () => { hideMatchResults(); matchEnding = false; startMatch(lastMatchConfigId); };',
    'rematch')

# 14. exposicao window: API por modo + alias legacy (contrato E2E)
g = sub1(g, 'window.start5v5Match = start5v5Match;',
         '''window.startMatch = startMatch;                           // PV1.1: API por modo
window.start5v5Match = () => startMatch('dm_legacy_5v5'); // alias legacy — contrato E2E (F02/F04)''',
         'window exposure')

wr('public/game.js', g)
ok.append('game.js: MATCH_CONFIGS + startMatch(id) + alias legacy + 3v3 wiring')

# ================= index.html =================
i = rd('public/index.html')
backup('public/index.html', 'pv1a')
assert 'id="mode-picker"' not in i
i = sub1(
    i,
    '        <div class="hero-stage-cta">',
    '''        <!-- PV1.1: seletor de modo (docs/PIVOT_MOBILE.md decisao #1) -->
        <div id="mode-picker" role="tablist" aria-label="Modo de jogo">
          <button type="button" class="mode-chip selected" data-mode="dm_3v3">COMBATE 3v3<small>15 abates · 3 min</small></button>
          <button type="button" class="mode-chip" data-mode="dm_legacy_5v5">CLÁSSICO 5v5<small>30 abates · 5 min</small></button>
          <button type="button" class="mode-chip" data-mode="br_vila" disabled>REALEZA NA VILA<small>em breve · PV2</small></button>
        </div>

        <div class="hero-stage-cta">''',
    'mode picker html')
wr('public/index.html', i)
ok.append('index.html: #mode-picker (3v3 default / 5v5 / BR em breve)')

# ================= styles.css =================
c = rd('public/styles.css')
backup('public/styles.css', 'pv1a')
assert 'MODE PICKER' not in c
c = c.rstrip() + '''

/* ==== PV1.1 MODE PICKER (docs/PIVOT_MOBILE.md §2.2) ==== */
#mode-picker { display: flex; gap: 8px; justify-content: center; margin: 10px 0 12px; flex-wrap: wrap; }
#mode-picker .mode-chip {
  font-family: inherit; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 1px;
  padding: 7px 14px; min-width: 118px;
  background: rgba(10, 14, 20, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.28); border-radius: 8px;
  color: #cbd5e1; font-size: 14px; font-weight: 600; letter-spacing: 0.5px;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
#mode-picker .mode-chip small { font-size: 10.5px; font-weight: 400; color: #64748b; letter-spacing: 0.2px; }
#mode-picker .mode-chip:hover:not(:disabled) { border-color: rgba(249, 115, 22, 0.55); color: #f8fafc; }
#mode-picker .mode-chip.selected {
  border-color: #f97316; color: #fff;
  background: linear-gradient(180deg, rgba(249, 115, 22, 0.16), rgba(10, 14, 20, 0.82));
  box-shadow: 0 0 0 1px rgba(249, 115, 22, 0.35), 0 6px 18px rgba(249, 115, 22, 0.12);
}
#mode-picker .mode-chip.selected small { color: #fdba74; }
#mode-picker .mode-chip:disabled { opacity: 0.45; cursor: default; }
'''
wr('public/styles.css', c)
ok.append('styles.css: bloco MODE PICKER')

print('\n'.join('[ok] ' + s for s in ok))
print('\nPV1-A PATCH APPLIED. Proximo: node --check + probe dm_3v3 + bateria.')
