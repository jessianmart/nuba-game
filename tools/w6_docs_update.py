"""W6 docs: PIVOT_MOBILE §8.6, TEST_READY §W6, PROJECT row 52, LIFELINE append."""
ok = []


def patch(path, anchor, insert_after=True, text=''):
    s = open(path, encoding='utf-8', newline='').read()
    nl = '\r\n' if '\r\n' in s[:2000] else '\n'
    a = anchor.replace('\n', nl)
    assert s.count(a) == 1, f'ancora != 1 em {path}: {anchor[:60]!r}'
    t = text.replace('\n', nl)
    s = s.replace(a, a + (t if insert_after else '') if insert_after else t + a, 1)
    open(path, 'w', encoding='utf-8', newline='').write(s)
    ok.append(path)


# ---- PIVOT_MOBILE: §8.6 após a 8.5.1 (frase final da subseção)
patch('docs/PIVOT_MOBILE.md',
      'Probe `tools/probe_w5f2.py` **8/8** (oggs 200, voz da vítima posicionada,\ngate, defensivo, 0 console errors).',
      True, """

### 8.6 W6 — Música de fundo + settings de áudio funcionais (2026-10-23)

O APK tem o banco `bgm.awb` (84 MB, 45 trilhas HCA stereo 48 kHz com **loop
points nativos e nomes por wave**) dentro do `adx2.awb` — `tools/list_bgm_tracks.py`
inventaria tudo (`modeslct`, `charaslct`, `stage00-13`, `titleJP`, `staff`,
`mini_win`...). Decodificadas: **`modeslct`** (loop 44,8 s — a autêntica de
seleção de modo) pro lobby e **`stage00`** (loop 78,7 s) leve na batalha —
`tools/extract_bgm_tracks.py` (vgmstream `-l 0` = 1 passada + `Audio.loop`
no browser cobre a repetição) -> `public/assets/audio/music/*.ogg` (1,7 MB).

`MUSIC` (game.js): `play('menu'|'battle')` com volume-base por contexto
(menu 0,70 · batalha **0,38 — leve de propósito, não briga com SFX/vozes**)
× `musicVol` do perfil; autoplay policy tratada com unlock no primeiro
pointerdown/keydown. Hooks: boot (menu), `startMatch` (battle, L2003),
`returnToLobby` (menu, L5020).

**Settings FUNCIONAIS** no painel PREFERÊNCIAS (DOM aditivo): toggle
`#pref-music` + slider `#pref-music-vol` (0-100) + slider `#pref-sfx-vol`
(0-100) — aplicam LIVE (`MUSIC.applySettings()` / `AUTH_SFX.volume`) e
persistem no perfil (`music`, `musicVol`, `sfxVol` no schema do
loadProfileData). Probe `tools/probe_w6_music.py` **7/7**.""")

# ---- TEST_READY
patch('TEST_READY.md',
      '### W5-F2 — VOZES DE BATALHA POR HERÓI (PL_1XXX) — validado 2026-10-23',
      False,
      """### W6 — MÚSICA DE FUNDO + SETTINGS FUNCIONAIS — validado 2026-10-23
- `python tools/probe_w6_music.py` -> **7/7** (C1 2 trilhas HEAD 200; C2 boot
  menu vol 0.385=0.70x0.55 loop=true; C3 battle vol 0.209=0.38x0.55 LEVE;
  C4 toggle off->paused; C5 sliders live musicVol 100 -> 0.38 e sfxVol 20 ->
  AUTH_SFX.volume 0.2; C6 persistência em `nuba.profile.v1`
  {music, musicVol 1.0, sfxVol 0.2}; C7 zero console errors).
- C6 do probe lê `localStorage` DIRETO — `loadProfileData` é module-scoped
  (não está em window; lição §6.13 da skill).
- Trilhas: `bgm.awb` (84 MB, 45 faixas com loop nativo) extraído de
  `adx2.awb` via TOC CPK; decode `vgmstream -l 0` + ffmpeg q2 stereo.
""")

# ---- PROJECT row 52
patch('PROJECT.md',
      '| 51 | W5-F2 — Vozes de batalha POR HERÓI (bancos PL_1XXX do sound.awb)',
      False,
      """| 52 | W6 — Música de fundo (bgm.awb) + settings de áudio funcionais | bgm.awb (84MB, 45 trilhas HCA stereo com loop nativo e nome por wave) extraído do adx2.awb via TOC CPK; decodificadas modeslct (menu, loop 44.8s) e stage00 (batalha, loop 78.7s) -> music/*.ogg 1.7MB; modulo MUSIC com play('menu'|'battle'), volume-base por contexto (menu 0.70, battle 0.38 LEVE) x musicVol do perfil, unlock de autoplay no 1o gesto; settings DOM aditivo no painel PREFERÊNCIAS: toggle #pref-music + slider #pref-music-vol + slider #pref-sfx-vol aplicando LIVE (MUSIC.applySettings / AUTH_SFX.volume) e persistindo {music, musicVol, sfxVol} no loadProfileData; probe_w6_music 7/7 | W6 (áudio/música) | TEST_READY.md §W6 |
""")

# ---- LIFELINE append
s = open('LIFELINE.md', encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in s[:2000] else '\n'
entry = """
### [2026-10-23] W6 — Música de fundo + settings funcionais
**Agente:** human · **Provider:** none · **Model:** human

**O quê:** trilhas autênticas do APK (`bgm.awb`, 45 faixas com loop nativo)
no jogo — `modeslct` no lobby, `stage00` LEVE na batalha — e painel de
PREFERÊNCIAS com toggle de música + sliders de volume (música e SFX)
aplicando live e persistindo no perfil.

**Por quê:** pedido direto do usuário pós-W5-F2 ("extrai musica de fundo e
adiciona, nos menus, e uma de leve na batalha, com settings funcionais").
Batalha "de leve" para não competir com SFX/vozes (0,38 vs 0,70 do menu).

**Como:** TOC CPK do adx2.awb -> bgm.awb (AFS2) -> vgmstream -l 0 ->
ogg q2; modulo MUSIC com unlock de autoplay (primeiro gesto); DOM aditivo
pref-music/pref-music-vol/pref-sfx-vol; schema do perfil ganha
music/musicVol/sfxVol; probe 7/7.
""".replace('\n', nl)
open('LIFELINE.md', 'w', encoding='utf-8', newline='').write(s + entry)
ok.append('LIFELINE.md')
print('DOCS OK:', ok)
