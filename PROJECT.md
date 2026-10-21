# Project: NUBA (Naruto Ultimate Battle Arena)

## Architecture
NUBA is a 5v5 3D WebGL MOBA Deathmatch built on Three.js (v0.169.0), Web Audio API, and reverse-engineered Storm assets (3D models, stages sd00a/sd01b/sd03b/sd04a, animations, textures, and HUD).
- **Presentation Layer**: `public/index.html` (Lobby character select, In-Game HUD overlay, map selector chip picker, and Canvas viewport).
- **Visual Styling Layer**: `public/styles.css` (Glassmorphic dark MOBA HUD, scoreboard strip, mini-portraits, vitals command deck, skill ribbons, kill-feed, controls drawer, map selector).
- **Client Engine Layer**: `public/game.js` (WebGL renderer, stage loader, scene graph, skeletal FK animation interpolation, 5v5 AI bot and player updates, camera controller, combat physics, authentic Storm 3D VFX generators, input listeners, and DOM HUD synchronizer).
- **Asset Directory**: `public/assets/` (Stage JSON submeshes and textures for sd00a, sd01b, sd03b, sd04a; 10 ninja models and 100 animation clips; 106 Storm VFX textures and 3D skill submeshes; audio SFX and portraits).
- **Testing & Verification Suite**: `tools/` (CDP headless Edge runner `verify_browser_runtime.py`, photographic visual validation `capture_visual_validation.py`, multi-threaded HTTP server `server.py`, stage builders `build_arena.py`, and opaque-box E2E test suite `test_e2e_suite.py`).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Top Scoreboard Strip Height | Sleek centered 5v5 scoreboard strip strictly under 52px (target ~46px) with no overlap | M1 (HUD) | R1 / Survey 1 |
| 2 | Mini-Portraits & Pulsing Dots | 10 ninja mini-portraits with pulsing alive indicators for active units | M1 (HUD) | R1 / Survey 1 |
| 3 | Numerical Respawn Countdown | Numerical respawn countdown overlay on dead ninja avatars in top bar | M1 (HUD) | R1 / Survey 1 |
| 4 | Storm VS Crest & Timer | Centered Storm VS crest, match clock, and target score goal | M1 (HUD) | R1 / Survey 1 |
| 5 | Kill-Feed with Portraits & Auto-Dismiss | Top-right kill-feed with killer/victim portraits, ability tags, and smooth auto-dismiss fade out | M1 (HUD) | R1 / Survey 1 |
| 6 | Sculpted Command Center & Avatar | Circular player avatar with gold cel-shaded ring, Level chip, KDA tracker, layered HP/Chakra gauges | M1 (HUD) | R1 / Survey 1 |
| 7 | Radial Cooldown Sweeps | Action slots with authentic radial conic-gradient cooldown sweeps and countdown text | M1 (HUD) | R1 / Survey 1 |
| 8 | Collapsible Controls Drawer | Ninja controls cheat-sheet drawer toggled with `H` key or top-bar button | M1 (HUD) | R1 / Survey 1 |
| 9 | Free 'W' Key for Movement | `W` freed strictly for forward movement; no combat skill on `W` (remove Alt+W, fix Lobby badge) | M2 | R2 / Survey 2 |
| 10 | Camera-Relative 3rd-Person Movement | In 3rd-person mode, `WASD` moves relative to camera horizontal view vector | M2 | R2 / Survey 2 |
| 11 | Camera Stage Boundary Clamping | Clamp 3rd-person camera position and target with `Math.max(2.2, ...)` and `[-92, 92]` limits | M2 | R2 / Survey 2 |
| 12 | Mouse Left Click Basic Combo | 3-hit Taijutsu combo mapped strictly to Left Click (`e.button === 0`) | M2 | R3 / Survey 3 |
| 13 | Ninjutsu Primário [Q] | Primary Ninjutsu mapped to `[Q]` (or `[1]`) | M2 | R3 / Survey 3 |
| 14 | Ninjutsu Secundário [E] | Secondary Ninjutsu mapped to `[E]` (or `[2]`), disentangled from Kawarimi | M2 | R3 / Survey 3 |
| 15 | Kawarimi / Substituição [ESPAÇO] | Kawarimi substitute mapped to `[ESPAÇO]` (or `[3]`), disentangled from basic attack | M2 | R3 / Survey 3 |
| 16 | Ultimate Ougi & Awakening [R] | Secret Ultimate + Awakening mapped to `[R]` (or `[4]`) | M2 | R3 / Survey 3 |
| 17 | Concentrar Chakra [F] / [Shift] | Chakra charge mapped to `[F]` or `[Shift]`, without firing any jutsu | M2 | R3 / Survey 3 |
| 18 | Combat Audio & SFX Synchronization | Procedural Web Audio SFX triggered on skill casts and damage impacts | M2 | R3 / Survey 3 |
| 19 | Cel-Shaded Hit Sparks & VFX | Stylized cel-shaded impact sparks on attacks | M2 | R3 / Survey 3 |
| 20 | Awakening Ground Aura Rings | Animated expanding ground aura shockwave rings during Awakening mode | M2 | R3 / Survey 3 |
| 21 | E2E Testing Suite (Tiers 1-4) | Comprehensive opaque-box test suite validating all features via CDP | E2E Track | ORIGINAL_REQUEST §Acceptance Criteria |
| 22 | Browser Runtime Verification | `tools/verify_browser_runtime.py` runs with 0 console errors | M3 (Final) | ORIGINAL_REQUEST §Acceptance Criteria |
| 23 | Skin de UI autêntica Storm (border-image + sliced atlas) | HUD MOBA retexturizado com recortes reais do APK | M4 (UI Skin) | `docs/UI_SKIN_CONTRACT.md` |
| 24 | P1 Juice System (Hitstop + Kill Slow-Mo + Camera Shake + FOV Punch) | Camada aditiva de game feel em `game.js`: hitstop por peso de dano (18–82ms, gated por envolvimento do player e distância), slow-mo de abate (0.22x/0.75s em ultkill, 0.34x/0.45s normal), camera shake com decaimento de trauma re-clampado aos limites do palco, FOV punch cinematográfico em Ougi/KO, flash radial procedural + sparks turbinados (intensidade 0.7–1.7); relógio/CDs/respawn seguem em dt real (contratos E2E preservados). Estado exposto como `window.JUICE` | P1 (Juice) | TEST_READY.md §5 |
| 25 | M4.2 HUD Pass: Storm Cinematic + Kanji (Variante 1) | 43 patches cirúrgicos: bugfix de sizing dos skin-digits PNG 64×80 (clipavam a top bar de 46px), slots compactos 58px com ícone central + key badge + custo micro, zero emojis no HUD (CAM/TAB/TECLAS/✕), kanji autêntico nos pontos de drama (木ノ葉/敵 nas tags, 覚醒 no chip de despertar, 倒 no death overlay + 43 skills JP no kill-feed via `KILL_FEED_JP`), anel do avatar girando (spin 16s), paleta Storm unificada no death/scoreboard (frames 9-slice `panel_red`/`panel_silver`), fonte única de UI (Barlow Condensed). IDs DOM intocados — nenhum seletor E2E afetado | M4.2 (HUD Pass) | TEST_READY.md §6 |
| 26 | M5 Fim de Partida: Vitória + Quadro Final + MVP | Overlay `#match-results-overlay` em 5 fases animadas com assets reais do APK (banners win/lose/tie, `result_frame` 9-slice, `result_btn_red`): banner slam + kanji 勝利/敗北/引き分け, placar final com skin digits, card MVP flip-in (fórmula `K×100+A×50+Lv×20−D×15`), quadro K/D/A/KDA com subtotais e linhas em cascata, REVANCHE/LOBBY. `endMatch` com guarda `matchEnding` (reset no start), winner decidido no trigger | M5 (Match End) | TEST_READY.md §7 |
| 27 | M6 Arena Viva: Movimentação Autêntica + Engajamento Orgânico | Hook `run` por deslocamento real por frame (idle↔run sem sobrescrever ações) + **fix do bug cidade-fantasma**: busca de inimigos dos bots era 90u com bases a ~209u — ninguém nunca se engajava; agora cobre o mapa (0/10 → 9/10 em `run`, com dash/ult/down orgânicos). Clips `run0`/`dsh0l` autênticos do APK por herói | M6 (Arena Viva) | TEST_READY.md §7 |
| 28 | M7 Identidade de VFX por Skill | `SKILL_VFX_MAP` (10×4) liga cada Q/W/E/R ao mesh extraído autêntico do APK (Rasengan, Chidori, Amaterasu, areia do Gaara, Kaiten do Neji, dragão d'água do Kakashi…) via `activeSkillVfxModel` → `spawnVFX` → `buildExtractedVfxMeshGroup(modelName)` — zero branches editados; kawarimi usa o tronco `1efc_log01` real. Validado por 4 agentes paralelos: 40/40 casts, 40 frames, bateria 38/38 + 0 erros de console | M7 (VFX Identity) | TEST_READY.md §8 |
| 29 | P2 Kits Únicos: Identidade de Combate | `HERO_STATS` por herói (hp 850-1250, spd ×0.90-1.18, dr 0.82-1.18, reg ×0.95-1.30) wired na criação/`dealDamage`/regen + 40 números de kit reescritos (dmg/cd/cost únicos) — Gaara tanque, Itachi frágil, Lee veloz, Sakura sustain, sem tocar branches; validação por agentes: stats+DR+ kits por herói + bateria | P2 (Unicidade) | TEST_READY.md §9 |
| 30 | Lobby Fit: herói 3D visível + zero rolagem | Camada opaca do `#lobby-screen` removida (herói/palco 3D no centro — prova pixel 1.6→28.5); 6x `overflow-y:auto`->`hidden` + `.screen{overflow:hidden}` + compactação do painel + `.lobby-main` flex — audit: `scrollEls: []` na viewport 1883x851 | Lobby UX | TEST_READY.md §10 |
| 31 | Spawn Guard: imortalidade pós-respawn | `spawnShield` 4s no spawn/respawn, ativo só perto da base própria (raio 16u), quebra ao atacar, anel dourado + glow no rótulo; mitiga spawn trap; smoke 6/6; suite isolada 38/38 | Game Balance | TEST_READY.md §10 |
| 32 | Boot-Guard: race de cold-load extinta | Guard no topo de `start5v5Match` esperando `rosterMeta` (janela de até 10s) — `window.start5v5Match` era exposto antes do fetch do boot popular o roster; call cedo = `TypeError reading 'id'` + spawn incompleto (flake desde o P2); smoke de race 3/3 cold-starts dentro da janela; cache-bust v30 | Stability | TEST_READY.md §11 |
| 33 | T5 Match Pace: TTK longo + prorrogação | `HERO_HP_SCALE` 1.5 + `HERO_DMG_SCALE` 0.9 (TTK ×1.67, identidades P2 intactas); aos 5:00 empatados → prorrogação 60s (timer laranja) → ainda empatado → morte súbita (próximo abate vence, timer vermelho pulsante); antes empate dava vitória silenciosa ao azul; `window.__matchState` para debug | Game Balance | TEST_READY.md §12 |
| 34 | SPP: clones 3D + anim por skill + facing | **Kage Bunshin real**: `spawnShadowClones` invoca 3 clones 3D com o modelo extraído do Naruto (rig 20 bones, poof de fumaça, perseguição em arena aberta, dano em contato, TTL com poof); `SKILL_VFX_ANIM` 10×4 (spin/thrust/pulse/rise) no update do `vfxList`; VFX extraído nasce virado para o `rotY` do caster; smoke 9/9; REA desnecessário (chunks já decodizados pelo toolchain do repo); Blender 5.2 headless p/ auditoria de direções (`tools/spp_blender_audit.py`) | Presentation | TEST_READY.md §13 |
| 32 | Navegação de Cliente: Jogar / Ninjas / Arenas / Perfil | Lobby vira cliente de 4 abas: `<nav class="lobby-nav" role="tablist">` com 4 `button.nav-tab[data-page]` (`play \| ninjas \| arenas \| perfil`); `#page-play` é o `main.lobby-main` existente e as novas páginas são `<section class="lobby-page" id="page-ninjas\|page-arenas\|page-perfil">` (`.active` = visível). `game.js`: `PROFILE_KEY='nuba.profile.v1'`, `LOBBY_PAGES`, `lobbyPage`, `collectionFilter`, `matchRecorded`; `setLobbyPage()` alterna abas/ARIA e esconde o pedestal 3D fora de `play`; `renderCollectionPage()` (filtros + 5 grupos canônicos LUTADOR/ASSASSINO/NINJUTSU/TANQUE/SUPORTE via `heroRoleKey`), `renderArenaPage()` (`ARENA_AREA_LABELS`, aplica arena via `applyArena`), `renderProfilePage()` (stats, streak, ninja favorito, histórico, 6 conquistas, barra de XP), `initLobbyNav()` e `loadProfileData/saveProfileData/recordMatchResult`. `recordMatchResult` é chamado em `showMatchResults` sob guarda `matchActive` + `matchRecorded` (reset em `start5v5Match`); `returnToLobby()` chama `setLobbyPage('play')`. Hooks: `window.setLobbyPage`, `window.__lobbyPage()`, `window.__pedestalVisible()`, `window.__profileData()`. Áudio: `SoundFX.enabled` + tom `sfx.click()`. CSS: bloco "CLIENT NAV PAGES" (`.lobby-page`, `.page-head`, `.filter-chip`, `.collection-grid`/`.collection-card`, `.arena-page-grid`/`.arena-card`/`.arena-shape`, `.page-footer-bar`, `.btn-page-primary`/`.btn-page-ghost`, `.profile-layout`/`.profile-stat`/`.profile-history`/`.pref-switch`/`.achievement-grid`); `@media (max-width:1400px)` não oculta mais `.lobby-nav` (apenas compacta; header em 3 colunas). Persistência: `localStorage['nuba.profile.v1'] = {matches,wins,losses,ties,kills,deaths,assists,history[6],arenas[],sound}`. Validação: `python tools\test_e2e_suite.py` 38/38, 0 erros de console, contrato DOM intocado (nenhum teste referencia nav/lobby-page) | M8 (Nav Cliente) | Sessão 2026-10-20 |
| 38 | Localização PT-BR + Resultados 720p | Tradução integral da interface: papéis e títulos do roster (`roster_meta.json`), HUD (`VIDA`, `Nv.`, `ABATES/MORTES`), slots (`CLIQUE`, `Ougi Supremo`), placar (`NV/AB/MT/AS`), tela de resultado, guia de teclas e atributos `alt`/`title`; `heroRoleKey` aceita tokens PT-BR (LUTADOR/CORPO A CORPO/BRIGÃO/MAGO/TANQUE/SUPORTE). Tela de resultados vira grid de 2 colunas em `@media (max-height:830px) and (min-width:900px)` (banner+placar+MVP à esquerda, tabelas+botões à direita): `scrollHeight == clientHeight` e stage 1120x413 na viewport 1254x627; `returnToLobby` esconde o overlay. Testes: asserções de HUD/placar aceitam os novos rótulos. Cache-bust v26/v34 | M8 (Localização) | Sessão 2026-10-20 |
| 24 | Torre Preliminar (sd01b) High-Fidelity Extraction | Indoor environment with Giant Hands Statue (>15k verts), authentic diffuse textures (scrolls, wood, tatami), 1024px resolution, warm indoor lighting | M5 (Arenas) | Follow-up R1 / Arenas Survey |
| 25 | Coliseu das Finais (sd03b) No Spikes & Circular Wall | Stone wall perimeter (r=92m), central trees, mottled floor, zero degenerate 3-vertex screen spikes | M5 (Arenas) | Follow-up R1 / Arenas Survey |
| 26 | Estádio / Platô Selvagem (sd04a) Rock Walls & Foliage | Right cliff wall (+X), plateau floor, billboard foliage with alphaTest: 0.28, drop dummy collision boxes | M5 (Arenas) | Follow-up R1 / Arenas Survey |
| 27 | Interactive Map Selector & Sanctuary Sync | Lobby map chips & in-game HUD sync, explicit sanctuary coordinates (prevent floating/embedded bases) | M5 (Arenas) | Follow-up R1 / Arenas Survey |
| 28 | Camera Clamping Profiles per Arena | Circular clamping for sd03b, ceiling clamp (y<=26m) for sd01b, asymmetric bounds for sd04a | M5 (Arenas) | Follow-up R1 / Arenas Survey |
| 29 | Elimination of Wireframe VFX Primitives | Remove wireframe: true primitives in spawnVFX, Rasengan, Chidori, Kaiten, Amaterasu, Ougi pillar | M6 (VFX & Anims) | Follow-up R2 / VFX Survey |
| 30 | Authentic Naruto Rasengan & Kyuubi VFX | 3D Rasengan with multi-axis gyroscopic chakra rings + core, Kyuubi chakra eruption shockwave disc | M6 (VFX & Anims) | Follow-up R2 / VFX Survey |
| 31 | Authentic Sasuke Chidori, Fireball & Kirin | Chidori lightning dome with procedural zigzag discharge arcs, Goukakyuu fireball, Kirin celestial bolt | M6 (VFX & Anims) | Follow-up R2 / VFX Survey |
| 32 | Authentic Signature VFX for All 10 Ninjas | Neji 360° Kaiten wind dome, Gaara giant sand hand (1gareff1_hnd01_body) & shield, Hinata twin lion fists, Itachi Amaterasu black flames, Lee Konoha cyclone | M6 (VFX & Anims) | Follow-up R2 / VFX Survey |
| 33 | 10 Ninjas 3D Rig Animation Sync for 5 Slots | Visible active animations on 3D rig for Taijutsu, Q, E, Space, R; dash action normalization & spk0 charge stance | M6 (VFX & Anims) | Follow-up R2 / Anims Survey |
| 34 | Hand Bone Attachment & FK Alignment | Hand-held jutsus (Rasengan, Chidori, Lion Fists) dynamically attached to bones[13] or bones[9] | M6 (VFX & Anims) | Follow-up R2 / VFX Survey |
| 35 | Photographic Headless Edge Visual Suite | Systematic 1600x900 screenshot capture of all 3 arenas and all signature jutsus for visual audit | M7 (Validation) | Follow-up R3 / Testing Survey |
| 36 | 0 Console Errors & Async Loading Contract | 100% async loading of meshes/textures, 0 console errors, 0 runtime exceptions, no NaN coordinates | M7 (Validation) | Follow-up R3 / Testing Survey |
| 37 | Comprehensive E2E Verification & Forensic Audit | Full automated E2E test suite pass on localhost:8080 and clean forensic integrity audit | M7 (Validation) | Follow-up R3 / Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| E2E | E2E Testing Track | Design and implement opaque-box test runner and test cases (Tiers 1-4) in `tools/`, publish `TEST_READY.md` | Survey complete | DONE |
| M1 | MOBA HUD & Non-Obstructive Layout | R1: Top bar <52px, respawn countdowns, pulsing dots, kill-feed with portraits & fade-out, radial cooldown sweeps, circular avatar, controls drawer | Survey complete | DONE |
| M2 | Responsive Movement, Camera & Combat Controls | R2 & R3: Free `W` strictly for movement, camera-relative 3rd-person movement vector, camera stage clamping, mouse click combo, Q/E/Space/R/F bindings, hit sparks, awakening aura rings, SFX | M1 | DONE |
| M3 | Final Milestone: 100% E2E Pass & Acceptance | Pass 100% of E2E test suite (Tiers 1-4), verify 0 console errors on `verify_browser_runtime.py`, forensic integrity audit | E2E, M1, M2 | DONE |
| M4 | UI Skin: Storm Atlas → HUD | R4: extrair atlas Battle do APK, segmentar por alpha, montar skin e aplicar via `border-image` | M1, APK_REVERSE §3 | DONE |
| M4.2 | HUD Pass: Storm Cinematic V1 + Kanji | 43 patches (index 12 · game 3 · styles 28), cache-bust v15/v21; verificação: verify 0 erros + suite 37/37 + 6 capturas de estado; rollback `public/*.bak_hudpass`; mockups de design em `public/sketches/` (3 variantes) | M4, P1 | DONE |
| M5 | Match End: Vitória + Quadro + MVP | overlay z-140, MVP por fórmula, REVANCHE via `start5v5Match`; fixes: winner-no-trigger, guarda reseta no start, cache-bust v22+; teste E2E `s06` (37→38, com `await_promise=True`); verificação: probe standalone + capturas win/lose/tie validadas via DOM | M4.2, P1 | DONE |
| M6 | Arena Viva: Run + Engajamento | M6.1 hook idle↔run (cache-bust v23) + M6.2 busca 90→999 (bases a ~209u; v25); emojis JS residuais limpos (⏳→蘇生); validação: 9/10 units em `run` com dash/ult/down orgânicos; rollback `public/*.bak_m61|m62` | M5 | DONE |
| M7 | VFX Identity por Skill | `SKILL_VFX_MAP` + modelo ambiente (v26); 4 agentes paralelos: 3 lotes de captura (40/40 casts ok, 40 shots) + bateria (38/38, 0 erros); padrão de validação: cast+leitura atômicos (global sobrescrito pela IA); rollback `public/*.bak_m7` | M6 | DONE |
| P2 | Kits Únicos | `HERO_STATS` (hp/spd/dr/reg) + kits reescritos (v27); smoke central PASS + agentes paralelos (stats/DR/kits por herói + bateria); rollback `public/*.bak_p2` | M7 | DONE |
| P1 | Juice Pass: Game Feel de Elite | Hitstop + slow-mo de abate + trauma shake + FOV punch + upgrade de hit VFX (`tools/p1_juice_patch.py`); verificação: `verify_browser_runtime.py` 0 erros + suite 37/37 | M3 | DONE |
| M8 | Nav Cliente: Jogar / Ninjas / Arenas / Perfil | 4 abas funcionais: coleção com filtros por função + seleção no palco 3D, arenas com blueprint e troca via `applyArena`, perfil com stats/histórico/conquistas em `localStorage`; fundo do lobby recortado no centro para expor o pedestal (câmera z 9.6→11.6); validação 38/38 + 0 erros | M4.2 | DONE |
| M9 | Localização PT-BR + Resultado sem rolagem | Interface 100% em pt-BR (roster, HUD, kit, placar, guia de teclas), `heroRoleKey` com tokens PT-BR e layout de resultados em 2 colunas para alturas <=830px; validação 38/38 (asserções de HUD/placar atualizadas) + 0 erros de console + captura `nuba_results_fit.png` | M8 | DONE |
| M5 | Chunin Arenas Extraction & Map Selector Sync | F24, F25, F26, F27, F28: High-fidelity sd01b (Giant Hands Statue + authentic diffuse textures), sd03b (zero spikes + stone wall), sd04a (rock cliff + foliage alphaTest), arenas.json sanctuary coords, camera clamping profiles, map selector | Survey complete | DONE |
| M6 | 3D Animations & Storm VFX for 10 Ninjas | F29, F30, F31, F32, F33, F34: Eliminate wireframes, gyroscopic Rasengan, Chidori lightning arcs, Kirin, Kaiten, Sand Hand, Lion Fists, Amaterasu, Lee cyclone; 5 action slots animated on 20-bone rigs, hand bone binding | M5 | IN_PROGRESS |
| M7 | Final Milestone: Photographic Validation & 0 Console Errors | F35, F36, F37: Headless Edge high-res screenshots of 3 arenas and signature VFX, 0 console errors, 100% async loading, full E2E pass, Forensic Integrity Audit | M5, M6 | PLANNED |

## Interface Contracts
### DOM HUD & Map Selector ↔ Client Engine (`index.html` / `styles.css` ↔ `game.js`)
- Arena picker chips `.arena-chip[data-arena="{arenaId}"]` update `ARENA` object and trigger `applyArena(arenaId)`.
- `#arena-name` and `#minimap-arena-name` reflect current arena label.
- Minimap and sanctuary boundaries dynamically derived from `ARENA.sanctuaryBlue`, `ARENA.sanctuaryRed`, and `ARENA.bounds` / `ARENA.radius`.

### Arena Data Specification (`public/assets/data/arenas.json`)
- Each arena entry defines:
  ```json
  {
    "id": "sd01b",
    "label": "Torre Preliminar (Exame Chūnin)",
    "mesh": "assets/stage/arena/sd01b.json",
    "shape": "box",
    "radius": 62,
    "cameraMaxY": 26.0,
    "sanctuaryBlue": { "x": 0, "z": -52 },
    "sanctuaryRed": { "x": 0, "z": 52 },
    "bounds": { "minX": -58, "maxX": 58, "minZ": -58, "maxZ": 58 },
    "lighting": { "ambient": "0xfff0dd", "ambientIntensity": 1.15, "directional": "0xffe8c0", "dirIntensity": 1.45 }
  }
  ```

### VFX & Animation Controller Specification (`public/game.js`)
- All 10 characters evaluate 20 canonical bones (`bones[0]` root through `bones[19]` r_foot).
- Hand-held jutsus bind their mesh groups to `unit.bones[13]` (right hand) or `unit.bones[9]` (left hand).
- Compound VFX meshes use `userData.rotSpeed = new THREE.Vector3(x, y, z)` for multi-axis gyroscopic rotation.
- Visual materials use additive blending (`THREE.AdditiveBlending`), `transparent: true`, `depthWrite: false`, and authentic textures from `public/assets/skills/`.

## Code Layout
- `public/index.html`: DOM structure for HUD top bar, kill feed, command deck, controls drawer, and map selector.
- `public/styles.css`: CSS styling for MOBA HUD, arena chips, and glassmorphic UI.
- `public/game.js`: Core client engine, stage loader, skeletal animation evaluation, VFX generators, camera controller, and combat physics.
- `public/assets/stage/arena/`: Extracted arena JSON submeshes and texture assets (`sd00a`, `sd01b`, `sd03b`, `sd04a`).
- `public/assets/data/arenas.json`: Authoritative arena catalog with boundaries, sanctuaries, and lighting profiles.
- `public/assets/data/animations.json`: 100 authentic Storm animation clips for the 10 ninjas.
- `public/assets/skills/`: 106 authentic Storm VFX textures and `skill_vfx.json`.
- `tools/build_arena.py`: Stage extraction pipeline from APK CPK archives.
- `tools/capture_visual_validation.py`: Headless Edge CDP photographic validation script.
- `tools/verify_browser_runtime.py`: CDP headless runtime test enforcing 0 console errors and async loading.
- `tools/test_e2e_suite.py`: 34-test opaque-box E2E testing suite.
- `.agents/teamwork/`: Multi-agent coordination metadata only.
36. **Deploy público validado (GitHub + Vercel)** — https://goofy-mendeleev.vercel.app;
    bateria determinística 38/38 + zero console errors rodando CONTRA o deploy via
    proxy reverso; repo espelhado em github.com/jessianmart/nuba-game.
