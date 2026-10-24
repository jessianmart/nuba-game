"""W6 patcher: música de fundo do APK (bgm.awb — modeslct no lobby,
stage00 leve na batalha) + settings FUNCIONAIS (toggle música, volume
música, volume SFX) persistidos no perfil.
Edições: index.html (2 rows de settings), styles.css (ranges), game.js
(módulo MUSIC + hooks start/lobby + profile render + handlers + schema).
Padrão da casa: âncora única por edição, CRLF/LF por região, backup
.bak_w6, marcadores verificados + node --check.
"""
import re
import shutil
import subprocess


def apply_edits(path, edits):
    shutil.copy2(path, path + '.bak_w6')
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
            raise SystemExit(f'ANCORA FALHOU em {path} (edit {n+1}, count={c}): {old[:70]!r}')
    open(path, 'w', encoding='utf-8', newline='').write(s)
    return n


# ---------- public/index.html ----------
apply_edits('public/index.html', [(
    '''            <div class="pref-row">
              <div><strong>Efeitos sonoros</strong><span>Impactos, jutsus e ougi</span></div>
              <label class="pref-switch"><input type="checkbox" id="pref-sound" checked /><span></span></label>
            </div>''',
    '''            <div class="pref-row">
              <div><strong>Efeitos sonoros</strong><span>Impactos, jutsus e ougi</span></div>
              <label class="pref-switch"><input type="checkbox" id="pref-sound" checked /><span></span></label>
            </div>
            <div class="pref-row">
              <div><strong>Música</strong><span>Lobby e batalha — volume</span></div>
              <div class="pref-audio">
                <input type="range" id="pref-music-vol" min="0" max="100" value="55" aria-label="Volume da música" />
                <label class="pref-switch"><input type="checkbox" id="pref-music" checked /><span></span></label>
              </div>
            </div>
            <div class="pref-row">
              <div><strong>Volume de efeitos</strong><span>Impactos, jutsus e vozes</span></div>
              <input type="range" id="pref-sfx-vol" min="0" max="100" value="85" aria-label="Volume dos efeitos" />
            </div>''')])

# ---------- public/styles.css (uma edicao, ancora real) ----------
apply_edits('public/styles.css', [(
    '/* ==== PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==== */',
    '''/* W6: settings de audio funcionais (musica + volume SFX) */
.pref-audio { display: flex; align-items: center; gap: 10px; }
.pref-audio input[type="range"], .pref-row input[type="range"] { accent-color: #f97316; cursor: pointer; width: 110px; }
/* ==== PV1.3/PV1.4 TOUCH CONTROLS (docs/PIVOT_MOBILE.md §2.4) ==== */''')])

# ---------- public/game.js ----------
GJS = [
    # E3: modulo MUSIC apos o export do SKILL_SFX_MAP (mesma ancora do W5-F2)
    ('window.SKILL_SFX_MAP = SKILL_SFX_MAP;',
     '''window.SKILL_SFX_MAP = SKILL_SFX_MAP;
// W6: música de fundo autêntica (bgm.awb do APK — modeslct no lobby, stage00
// leve na batalha). Settings FUNCIONAIS no painel PREFERÊNCIAS (toggle música,
// volume música, volume SFX) persistidos no perfil. Autoplay policy: o play()
// sem gesto é engolido; o unlock no primeiro pointerdown/keydown retoma.
const MUSIC = {
  el: null, track: null,
  baseVol: { menu: 0.7, battle: 0.38 },
  settings() {
    try {
      const d = loadProfileData();
      return { on: d.music !== false, vol: d.musicVol != null ? d.musicVol : 0.55 };
    } catch (e) { return { on: true, vol: 0.55 }; }
  },
  file(track) { return 'assets/audio/music/' + (track === 'battle' ? 'battle_stage00' : 'menu_modeslct') + '.ogg'; },
  play(track) {
    this.track = track;
    const s = this.settings();
    if (!s.on) { this.stop(); return false; }
    if (!this.el) { this.el = new Audio(); this.el.loop = true; }
    if (this.el.dataset.track !== track) { this.el.src = this.file(track); this.el.dataset.track = track; }
    const base = this.baseVol[track] != null ? this.baseVol[track] : 0.6;
    this.el.volume = Math.max(0, Math.min(1, base * s.vol));
    const p = this.el.play(); if (p && p.catch) p.catch(function () {});
    return true;
  },
  applySettings() {
    const s = this.settings();
    if (!s.on) { this.stop(); return; }
    if (!this.track) return;
    if (!this.el) { this.play(this.track); return; }
    const base = this.baseVol[this.track] != null ? this.baseVol[this.track] : 0.6;
    this.el.volume = Math.max(0, Math.min(1, base * s.vol));
    if (this.el.paused) { const p = this.el.play(); if (p && p.catch) p.catch(function () {}); }
  },
  stop() { if (this.el) { try { this.el.pause(); } catch (e) {} } }
};
window.MUSIC = MUSIC;
(function () { // W6: unlock da autoplay policy — retoma a música no 1º gesto
  const unlock = () => { MUSIC.applySettings(); window.removeEventListener('pointerdown', unlock); window.removeEventListener('keydown', unlock); };
  window.addEventListener('pointerdown', unlock);
  window.addEventListener('keydown', unlock);
})();
MUSIC.play('menu'); // W6: trilha do lobby (modeslct)'''),
    # E4: startMatch -> battle
    ('  matchEnding = false; // M5.2: nova partida libera a guarda do fim (fim natural nao pode matar partidas futuras)',
     '''  matchEnding = false; // M5.2: nova partida libera a guarda do fim (fim natural nao pode matar partidas futuras)
  MUSIC.play('battle'); // W6: trilha leve de batalha (stage00)'''),
    # E5: returnToLobby -> menu
    ('''  arenaGroup.visible = false;
  lobbyPedestalGroup.visible = true;
  setLobbyPage('play');''',
     '''  arenaGroup.visible = false;
  lobbyPedestalGroup.visible = true;
  setLobbyPage('play');
  MUSIC.play('menu'); // W6: volta a trilha do lobby'''),
    # E6: profile render (checkbox + sliders + volumes)
    ('''  const sound = document.getElementById('pref-sound');
  if (sound) sound.checked = data.sound !== false;
  sfx.enabled = data.sound !== false;''',
     '''  const sound = document.getElementById('pref-sound');
  if (sound) sound.checked = data.sound !== false;
  sfx.enabled = data.sound !== false;
  const _pm = document.getElementById('pref-music'); // W6
  if (_pm) _pm.checked = data.music !== false;
  const _pmv = document.getElementById('pref-music-vol');
  if (_pmv) _pmv.value = Math.round((data.musicVol != null ? data.musicVol : 0.55) * 100);
  const _psv = document.getElementById('pref-sfx-vol');
  if (_psv) _psv.value = Math.round((data.sfxVol != null ? data.sfxVol : 0.85) * 100);
  AUTH_SFX.volume = data.sfxVol != null ? data.sfxVol : 0.85;
  MUSIC.applySettings();'''),
    # E7: profile schema fallback
    ('sound: true, volume: 0.85, quality: \'high\', juice: true };',
     'sound: true, volume: 0.85, quality: \'high\', juice: true, music: true, musicVol: 0.55, sfxVol: 0.85 };'),
    # E8: handlers dos settings (apos o prefSound)
    ('''      sfx.enabled = prefSound.checked;
      if (prefSound.checked) { sfx.init(); sfx.clink(); }
    });
  }''',
     '''      sfx.enabled = prefSound.checked;
      if (prefSound.checked) { sfx.init(); sfx.clink(); }
    });
  }

  const prefMusic = document.getElementById('pref-music'); // W6: settings funcionais
  if (prefMusic) prefMusic.addEventListener('change', () => {
    const d = loadProfileData(); d.music = prefMusic.checked; saveProfileData(d);
    MUSIC.applySettings();
  });
  const prefMusicVol = document.getElementById('pref-music-vol');
  if (prefMusicVol) prefMusicVol.addEventListener('input', () => {
    const d = loadProfileData(); d.musicVol = prefMusicVol.value / 100; saveProfileData(d);
    MUSIC.applySettings();
  });
  const prefSfxVol = document.getElementById('pref-sfx-vol');
  if (prefSfxVol) prefSfxVol.addEventListener('input', () => {
    const d = loadProfileData(); d.sfxVol = prefSfxVol.value / 100; saveProfileData(d);
    AUTH_SFX.volume = d.sfxVol;
  });'''),
]
n = apply_edits('public/game.js', GJS)
print(f'game.js: {n}/{len(GJS)} edições')

# ---------- cache-buster (auto pode ter bumpado; regex-bump robusto) ----------
for fname, pat in (('public/index.html', r'(game\.js\?v=)(\d+)'), ('public/index.html', r'(styles\.css\?v=)(\d+)')):
    s = open(fname, encoding='utf-8', newline='').read()
    m = re.search(pat, s)
    if not m:
        print(f'cache-buster: padrao {pat} ausente em {fname}')
        continue
    cur = m.group(2)
    s2 = re.sub(pat, lambda mm: mm.group(1) + str(int(mm.group(2)) + 1), s, count=1)
    open(fname, 'w', encoding='utf-8', newline='').write(s2)
    print(f'cache-buster {pat}: v{cur} -> v{int(cur)+1}')

# verificacoes
chk = open('public/game.js', encoding='utf-8', newline='').read()
assert chk.count('W6') >= 8, f'marcadores W6: {chk.count("W6")}'
assert 'MUSIC.play(\'battle\')' in chk and 'MUSIC.play(\'menu\')' in chk
html = open('public/index.html', encoding='utf-8', newline='').read()
for eid in ('pref-music', 'pref-music-vol', 'pref-sfx-vol'):
    assert f'id="{eid}"' in html, eid
r = subprocess.run(['node', '--check', 'public/game.js'], capture_output=True, text=True)
assert r.returncode == 0, r.stderr[:400]
print('node --check OK — W6 PATCHER COMPLETO')
