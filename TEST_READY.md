# TEST_READY: NUBA E2E Testing Suite Verification

**Date**: 2026-10-17  
**Re-verified**: 2026-10-18 — P1 Juice Pass (37/37, zero regressions)  
**Test Suite File**: `tools/test_e2e_suite.py`  
**Target Application**: NUBA (Naruto Ultimate Battle Arena 5v5 MOBA) on `http://localhost:8080/index.html`  
**Test Architecture**: Python 3 CDP Runner (`websockets`) via Headless Microsoft Edge (Port 9222)  
**Execution Command**:
```powershell
python tools/test_e2e_suite.py
```

---

## 1. Summary of Test Results

| Tier | Category | Total Tests | Passed | Failed | Pass Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Tier 1** | Feature Coverage (Features 1-23: core M1-M4 + Chunin Arena Expansion) | 23 | 23 | 0 | 100% |
| **Tier 2** | Boundary & Corner Cases | 5 | 5 | 0 | 100% |
| **Tier 3** | Pairwise Combinations | 4 | 4 | 0 | 100% |
| **Tier 4** | Real-World Application Match Scenarios | 5 | 5 | 0 | 100% |
| **TOTAL** | **Full E2E Testing Suite** | **37** | **37** | **0** | **100%** |

**Console Errors**: 0 (Clean Execution verified via CDP `Log.entryAdded` and `Runtime.consoleAPICalled`).  
**Exit Code**: 0

---

## 2. Test Inventory Breakdown

### Tier 1: Feature Coverage (Features 1 to 20)
- [x] **T1_F01**: Top Scoreboard Strip Height strictly under 52px (computed height < 52px).
- [x] **T1_F02**: Mini-Portraits & Pulsing Dots (5 Konoha Azul, 5 Rivais Vermelho, active alive-dots).
- [x] **T1_F03**: Numerical Respawn Countdown on dead ninja avatars in top bar.
- [x] **T1_F04**: Storm VS Crest, match timer clock (`05:00`), and target score goal (`META: 30 ABATES`).
- [x] **T1_F05**: Top-right Kill-Feed with portraits, ability tags, and auto-dismiss.
- [x] **T1_F06**: Sculpted Command Center (circular avatar, Level chip, KDA tracker, HP/Chakra gauges).
- [x] **T1_F07**: Radial Cooldown Sweeps (action slots with countdown text and conic-gradient overlay).
- [x] **T1_F08**: Collapsible Controls Drawer (ninja cheat-sheet toggled with `H` key and buttons).
- [x] **T1_F09**: Free `W` Key for forward movement (no combat skill or chakra consumption on `W`).
- [x] **T1_F10**: Camera-Relative 3rd-Person Movement (`WASD` moves relative to horizontal view vector).
- [x] **T1_F11**: Camera Stage Clamping ($Y \ge 2.2$, $X, Z \in [-92, 92]$ limits to prevent clipping).
- [x] **T1_F12**: Mouse Left Click Basic Combo (3-hit Taijutsu combo cycling `attack` -> `attack2` -> `attack3`).
- [x] **T1_F13**: Ninjutsu Primário `[Q]` (triggers skill, consumes chakra, sets cooldown).
- [x] **T1_F14**: Ninjutsu Secundário `[E]` (triggers skill slot `w`, disentangled from Kawarimi).
- [x] **T1_F15**: Kawarimi / Substituição `[ESPAÇO]` (triggers substitution, leaves log, repositioning).
- [x] **T1_F16**: Ultimate Ougi Secreto & Despertar `[R]` (activates awakening mode, aura mesh).
- [x] **T1_F17**: Concentrar Chakra `[F]` / `[Shift]` (charges chakra at +32 CK/s without firing jutsu).
- [x] **T1_F18**: Synchronized Procedural Web Audio SFX (`hit`, `jutsu`, `kawarimi`, `ultimate`).
- [x] **T1_F19**: Cel-Shaded Hit Sparks & VFX spawned on combat contact.
- [x] **T1_F20**: Awakening Ground Aura Rings & shockwaves active during Awakening mode.
- [x] **T1_F21**: Arena Catalog Loaded (>=8 arenas).
- [x] **T1_F22**: Arena Switch Rebuilds Stage + Rescales Clamps.
- [x] **T1_F23**: Arena Picker UI Reflects Selection.

### Tier 2: Boundary & Corner Cases
- [x] **T2_B01**: Screen Resize Boundary (1920x1080 -> 1280x720 -> 800x600 maintains top bar < 52px).
- [x] **T2_B02**: Camera Clamping Boundary Stress (corners at $(\pm 92, \pm 92)$ clamp cleanly above $Y \ge 2.2$).
- [x] **T2_B03**: Zero Chakra Corner Case (attempting jutsu at 0 chakra does not deduct chakra or trigger skills).
- [x] **T2_B04**: Rapid Combo Cycling Stress (rapid consecutive inputs maintain clean 1-2-3-1 cycle).
- [x] **T2_B05**: Player Stage Perimeter Clamping (movement blocked at arena perimeter $[-94, 94]$).

### Tier 3: Pairwise Combinations
- [x] **T3_P01**: WASD Movement while casting jutsu transitions state smoothly and resumes movement.
- [x] **T3_P02**: Toggling camera mode (`KeyC`) during combat combo maintains finite non-NaN coordinates.
- [x] **T3_P03**: Controls drawer toggle (`KeyH`) during unit respawn operates without conflict.
- [x] **T3_P04**: Rapid transition from Chakra Charge `[F]` to Kawarimi `[ESPAÇO]` executes cleanly.

### Tier 4: Real-World Match Scenarios
- [x] **T4_S01**: Full Match Initiation & HUD Verification (10 ninjas, HUD initialized, top bar < 52px).
- [x] **T4_S02**: 3rd-Person Boundary & Navigation Run (full circuit navigation with camera clamping).
- [x] **T4_S03**: Combat Combo & Ability Cycling (3-hit combo -> Q -> E -> Space -> F charge).
- [x] **T4_S04**: Kill & Respawn Cycle Verification (lethal attack -> kill feed -> countdown -> respawn).
- [x] **T4_S05**: Awakening & Ultimate Clash (100% chakra -> Ultimate -> Awakening mode -> aura rings -> SFX).

---

## 3. Artifacts Generated
- `tools/test_e2e_suite.py`: Complete opaque-box CDP automated test suite.
- Scratch Screenshot: `C:\Users\jessi\.gemini\antigravity\brain\66ffd025-8f38-48b2-8db5-931d3fd40c66\scratch\nuba_e2e_suite_pass.png`.

---

## 4. Verdict
The E2E Testing Suite is fully implemented, verified, and passing 100% with zero console errors. The testing infrastructure is **READY** for integration and validation across all milestones.


---

## 5. Re-Verification 2026-10-18 — P1 Juice Pass (Hitstop / Slow-Mo / Shake / FOV Punch)

The P1 Juice System was added to `public/game.js` as a purely additive layer:
damage-weighted hitstop, kill slow-mo, trauma-decay camera shake (re-clamped
to stage safety bounds even mid-shake), cinematic FOV punch and upgraded hit
VFX (procedural radial flash sprite + intensity-scaled sparks). Match clock,
cooldowns and respawn timers intentionally keep real dt, so no E2E timing
contract changed.

- `python tools/verify_browser_runtime.py` → **PASS, 0 console errors** (exit 0)
- `python tools/test_e2e_suite.py` → **37/37 PASS** (T1 23/23 · T2 5/5 · T3 4/4 · T4 5/5), **0 console errors** (exit 0)
- Runtime telemetry captured via `window.JUICE` (CDP):
  - Player kill with dmg >= 300: `hitstop 0.13s · slow-mo 0.22x / 0.75s · trauma 0.945 · fovPunch 5.5`
  - Ultimate cast: `hitstop 0.09s · slow-mo 0.55x / 0.35s · trauma 0.30 · fovPunch 4.0`
  - Full decay back to `timeScale 1.0` after each window (no residual state)
- Visual proof frames: `.gemini/antigravity/brain/66ffd025-8f38-48b2-8db5-931d3fd40c66/scratch/p1_juice/`
  (`p1_juice_ko_impact.png`, `p1_juice_ko_slowmo.png`, `p1_juice_ult_cast.png`)
- Patcher provenance: `tools/p1_juice_patch.py` (one-shot, aborts if re-run) · Rollback: `public/game.js.bak_p1juice`

**Verdict: P1 Juice Pass is DONE — full suite green, zero regressions.**


---

## 6. Re-Verification — M4.2 HUD Pass (Storm Cinematic V1 + Kanji)

- `python tools/verify_browser_runtime.py` → **PASS, 0 console errors** (exit 0)
- `python tools/test_e2e_suite.py` → **37/37 PASS** (T1 23/23 · T2 5/5 · T3 4/4 · T4 5/5), **0 console errors** (exit 0)
- Scope: 43 surgical patches (index.html 12 · game.js 3 · styles.css 28) — all DOM IDs intact; no E2E selector touched
- Key fix: skin digit PNGs (64×80) had no CSS sizing — timer/score/CD digits were clipped by the 46px top bar; now sized per-context (`.skin-digit` suite)
- New flavor: JP kanji kill-feed (43 skills mapped in `KILL_FEED_JP`), 木ノ葉/敵 team tags, 覚醒 awake chip, 倒 death icon, spinning avatar ring, compact 58px ability slots, Storm palette on death/scoreboard (9-slice `panel_red`/`panel_silver` frames), single UI font (Barlow Condensed)
- Visual proof: `nuba_sketches/shots/hudpass_{01_lobby..06_death_overlay}.png` (6 states)
- Rollback: `public/index.html.bak_hudpass`, `public/game.js.bak_hudpass`, `public/styles.css.bak_hudpass`
- Design mockups kept for reference: `public/sketches/` (3 variants, CDP-audited, zero broken assets)

**Verdict: M4.2 HUD Pass DONE — suite green, zero regressions, HUD redesigned per user's pick (Variante 1 + V3 touches).**


---

## 7. Re-Verification — M5 Match End + M6 Arena Viva (38-test suite)

### M5 — Fim de Partida: Vitória + Quadro Final + MVP
- `#match-results-overlay` (z-140) em 5 fases animadas: banner slam autêntico (`banner_win/lose/tie.png`)
  + kanji 勝利/敗北/引き分け → placar final via `renderSkinDigits` → card MVP flip-in (anel girando,
  selo 最優秀選手) → quadro K/D/A/KDA com linhas em cascata → botões 再戦 REVANCHE / ロビー LOBBY
  (9-slice `result_frame`/`result_btn_red` reais do APK)
- MVP: `K×100 + A×50 + Lv×20 − D×15`, time vencedor primeiro, fallback global no empate
- Bugs reais achos e corrigidos no caminho:
  - winner decidido no TRIGGER do fim (não t+1.5s — bots podiam virar o placar durante o slow-mo)
  - `matchEnding` agora reseta em `start5v5Match` (fim natural matava fins futuros para sempre)
  - cache-bust disciplinado (v22→v25)
  - emojis residuais gerados em JS limpos (☠️🟢⭐; ⏳ → 蘇生 nos respawn timers)

### M6 — Movimentação e Arena Viva
- M6.1: hook de estado `run` por deslocamento real por frame (idle↔run; nunca sobrescreve
  attack/jutsu/ult/down/charge) — player já setava run via input; hook cobre TODAS as fontes
- M6.2 **(o grande)**: `updateAIBotUnit` buscava inimigos num raio de 90u com bases a ~209u
  (sanctuaries ±74,±74) — **a arena era cidade-fantasma: bots nunca se engajavam organicamente**
  (só havia combate quando tests teleportavam unidades). Busca agora cobre o mapa inteiro.
  Validação: 0/10 → **9/10 unidades em `run`** em plena batalha, com `dash` (despertos), `ult`
  (casting) e `down` (mortes orgânicas) coexistindo
- readiness de probes corrigido: `window.HERO_KITS` **nunca existiu** (const module-scoped);
  sinal correto = `typeof window.start5v5Match === 'function'`

### Suite E2E: 38 testes (novo `test_s06_match_results_mvp_flow`)
- S06 valida: cadeia real `endMatch` (guarda liberada → overlay) + UI forçada blue/red/tie
  (kanji, banner, 5+5 linhas, MVP) + revanche restaura partida
- Fix de teste: IIFE async exigia `await_promise=True` no `eval_js` — sem isso TODAS as versões
  do S06 falhavam na primeira chave (res era uma Promise não resolvida)
- `python tools/test_e2e_suite.py` → **38/38 PASS, 0 console errors**
- Visual: `nuba_sketches/shots/m5_{07,08,09}_results_*.png` + `m6_10_units_running.png`
- Rollback: `public/*.bak_m5result|m51|m52|m61|m62` · `tools/test_e2e_suite.py.bak_m5test`

**Verdict: M5 + M6 DONE — fim de partida completo e a arena finalmente viva.**


---

## 8. Re-Verification — M7 Identidade de VFX por Skill (40/40 casts, agentes paralelos)

- `SKILL_VFX_MAP` (10 heróis × 4 slots, `public/game.js`) mapeia cada cast ao mesh extraído autêntico
  do APK (`assets/skills/skill_vfx.json`): Rasengan/`giant_rasengan` (Naruto), `chidori_spark`/`fireball`
  + sharingan effs (Sasuke), `shatter`/`heal_chakra` (Sakura), `raikiri_spark`/`water_dragon` + Kamui
  sharingan (Kakashi), `whirlwind`/`air_tornado`/`leaf_flurry` (Rock Lee), `amaterasu_flame`/`crow_smoke`
  (Itachi), meshes de areia `1gareff1_*`/`sand_dust` (Gaara), `palms_rotation`/`lion_chakra` (Hinata),
  `kaiten_dome`/`air_palm` (Neji), `toad_fire`/`chou_rasengan` (Jiraiya); kawarimi e-slots usam o
  `1efc_log01` autêntico (tronco de substituição) via `common`
- Mecânica: `executeSkill` seta `activeSkillVfxModel` no topo (self-cleaning por cast); `spawnVFX`
  o repassa a `buildExtractedVfxMeshGroup(heroId, …, modelName)` — nenhum branch de skill foi editado
- **Validação: 40/40 casts `active === expected`** por 3 agentes paralelos (16+12+12; `m7_results_{A,B,C}.json`),
  zero `Runtime.exceptionThrown`; `extractedDelta > 0` em ~21/40 (mesh extraído spawna no ponto);
  e-slots kawarimi trocam posição/log sem mesh extraído (comportamento do branch, não defeito)
- Metodologia (achado dos agentes): leitura de `window.__activeVfxModel()` pós-350ms é corrida perdida
  (a IA casta sem parar e sobrescreve o global) — cast+leitura ATÔMICOS na mesma expressão
  `Runtime.evaluate`, ou silenciar os 9 bots (cds=9999, chakra=0)
- Bateria (4º agente, logs verificados no repo): `verify` **PASS 0 console errors** ·
  `test_e2e_suite.py` **38/38 (T1 23 · T2 5 · T3 4 · T4 6), 0 console errors, exit 0**
- Prova visual: 40 frames `nuba_sketches/shots/m7_<herói>_<slot>.png` (1280×720, render validado
  programaticamente — backend de visão do ambiente indisponível/404)
- Rollback: `public/{index.html,game.js}.bak_m7` · cache-bust v26

**Verdict: M7 DONE — cada skill tem identidade visual autêntica; suite verde, zero regressões.**


---

## 9. Re-Verification — P2 Kits Únicos: Identidade de Combate (10 heróis, agentes paralelos)

- **HERO_STATS** (módulo, `public/game.js`): hp/spd/dr/reg por herói — Gaara tanque absoluto
  (1250 HP, dr 0.82 — areia absorve 18% do dano bruto), Itachi nuker frágil (850 HP, dr 1.18),
  Rock Lee o mais veloz (spd ×1.18), Sakura sustain (reg ×1.30 no santuário), Jiraiya bruiser
  (1150/0.90/1.10) etc. Wired na criação (`hs`), no `dealDamage` (DR: `max(1, round(bruto×dr))`)
  e no regen — sem tocar num único branch de skill
- **Kits reescritos** (40 linhas q/w/e/r + atk): cadências e custos com identidade —
  Amaterasu 300/7.0s/30 chakra (burst caro), Konoha Senpuu 135/3.8s (metralhadora de pernas),
  Cura 300/11s/30 (Sakura médica), 8 Gates 500/24s, Kirin 470/20s (assassino veloz)
- Segurança E2E comprovada ANTES do patch: a suite usa asserts relativos (`hp=5`→kill,
  `cd>0`, `hp===maxHp`, formatos de texto) — nenhum número absoluto é testado
- **Validação: 40 campos/herói × 10 heróis** por 3 agentes paralelos (maxHp, speed aplicado,
  DR probe com perda exata `round(100×dr)`, reg, kits completos) + bateria por 4º agente
- Smoke central (antes do fan-out): player 1050 / Gaara 1250 / Itachi 850; Lee 23.01 vs Gaara
  17.55; perdas 82/118 de 100 brutos; kits 250/6.0, 135/3.8, 500/24 — tudo PASS
- Cache-bust v27 · Rollback: `public/{index.html,game.js}.bak_p2`
- Prova visual: `nuba_sketches/shots/p2_<herói>.png` (10 frames)

- Flake conhecido (fora do escopo P2, registrado por 2 agentes): no PRIMEIRO carregamento a frio, `start5v5Match` resolve antes das unidades entrarem em `units` — pode dar `unit-not-found` ou `TypeError reading 'id'` em `spawnTeam` (game.js:1164); retry passa limpo. Probes devem pollar `window.units.length === 10` antes de sondar. Candidato a fix futuro (guard de spawn).

**Verdict: P2 DONE — heróis deixam de ser clones: tanque/frágil/veloz/sustentado jogam diferente.**


---

## 10. Re-Verification — Lobby Fit (herói 3D + zero rolagem) + Spawn Guard (2026-10-20)

### Lobby Fit — pedido do usuário com screenshot
- **Herói invisível no lobby**: causa raiz = `#lobby-screen` tinha um `linear-gradient`
  **opaco** por cima do canvas 3D — palco (294 meshes) e herói renderizavam atrás, invisíveis
  (`visible=true` no grafo ≠ pixels). Camada opaca removida (radiais translúcidas mantidas);
  prova pixel: variância do centro 1.6 (vazio) → **28.5** (herói renderizando)
- **Zero rolagem em TODA tela** (regra do usuário): todos os 6 `overflow-y: auto` → `hidden`
  (roster-grid, hero-details, anm-tags, modal-body, scoreboard-wrap, mr-stage) + `.screen
  { overflow: hidden }` como garantia + compactação do painel de detalhes (skill-desc 2 linhas
  via line-clamp, paddings 16→10, portrait 68→54, anm tags 16→6 via JS) + `.lobby-main` flexível
  (`calc(100vh-120px)` → flex) — audit CDP: `scrollEls: []`, `#lobby-screen` 851/851 exato
  na viewport do usuário (1883×851)
- Cache-bust: styles v16→**17** · game.js v27→**29**

### Spawn Guard — mitigação de spawn trap
- `spawnShield: 4.0s` no spawn inicial e no respawn; **imortalidade só perto da base própria**
  (raio 16u) — mitiga camping sem proteger quem avança; **atacar quebra a própria proteção**
  (`attacker.spawnShield = 0`); decay em dt real; anel dourado no respawn + brilho no rótulo
  (`.unit-label.shielded`)
- Smoke determinístico: 6/6 PASS (bloqueia na base / libera longe / quebra ao atacar /
  respawn restaura 4.0 / label glow / 10 units)
- Design suite-safe por construção: testes E2E teleportam alvos mid-arena (fora do raio da
  base) — nenhum assert absoluto de HP/dano afetado

### Bateria (após ambos os patches)
- Rodada 1 (com probe WebGL concorrente): 35/38 — F08/F17/F22 falharam por timing (carga
  de chakra parcial "20.275", teclado, troca de arena) — **flakes de carga**, não regressão
- Rodada 2 ISOLADA: `test_e2e_suite.py` → **38/38 Passed, 0 console errors, exit 0**
  (`fit_suite2.log`); `verify_browser_runtime.py` → PASS, 0 console errors
- Rollbacks: `public/*.bak_lobbyfit` + `public/*.bak_spawnguard`

**Verdict: Lobby Fit + Spawn Guard DONE — herói no centro, nenhuma tela rola, respawn protegido.**


---

## 11. Re-Verification — Boot-Guard: race de primeiro carregamento morta (2026-10-20)

- **Causa raiz do flake P2**: `window.start5v5Match` é exposto no topo do módulo, mas
  `rosterMeta` só é populado pelo fetch do boot (~linha 4698) — num cold start, um call cedo
  executava `rosterMeta.find(...)` com array vazio → `playerHero = undefined` →
  `TypeError reading 'id'` + spawn incompleto (2 agentes bateram nisso no P2)
- **Fix**: guard no topo de `start5v5Match` — espera `rosterMeta` popular (até 10s, 100×100ms),
  aborta com `console.warn` se o roster nunca carregar; cache-bust v30
- **Smoke de race**: 3/3 cold-starts com Edge fresco + profile temp novo, chamando
  `start5v5Match` no PRIMEIRO tick de readiness (poll de 50ms — dentro da janela da race):
  10 units + `spawnShield` ativo + `matchActive`, zero exceções (leitura do `exceptionDetails`
  do CDP, não só `result.value`)
- Stress de cold-load + bateria: agente dedicado (dono único do WebGL do ciclo — probes
  concorrentes já produziram flakes de carga falsos antes), resultados em `boot_*.log`
- Rollback: `public/game.js.bak_bootguard`

**Verdict: Boot-Guard DONE — o flake mais antigo da sessão (desde o P2) foi extinto na raiz.**


---

## 12. Re-Verification — T5 Match Pace: HP global + partida 5:00 + prorrogação (2026-10-20)

### Pedido do usuário
- "Aumentar a resistência geral, quantidade de HP, para demorar mais a matar, e a partida
  completa durar próximo de 5 min, com prorrogação de 1 min em caso de empate"

### Implementação
- **Resistência global**: `HERO_HP_SCALE = 1.5` no wiring do `HERO_STATS` (Gaara 1250→1875,
  Itachi 850→1275, baseline 1000→1500 — identidades P2 preservadas, só a escala muda) +
  `HERO_DMG_SCALE = 0.9` no `dealDamage` → TTK efetivo ×1.67
- **Partida ~5 min**: timer de 5:00 já existia; com TTK ×1.67 a meta de `TARGET_KILLS = 30`
  raramente termina antes do tempo — a maioria das partidas agora decide no cronômetro
- **Prorrogação**: aos 5:00 com placar EMPATADO → +60s ("PRORROGAÇÃO! 1 MINUTO PARA
  DESEMPATAR", timer laranja `#f97316`); antes o empate dava vitória ao azul silenciosamente
  (`scoreBlue >= scoreRed`)
- **Morte súbita**: prorrogação encerrada empatada → "MORTE SÚBITA! O PRÓXIMO ABATE VENCE",
  timer vermelho pulsante, cronômetro congela — o próximo abate encerra a partida na hora
- Reset de flags/classes no `start5v5Match` (rematch limpo) + `window.__matchState`
  (getter/setter de tempo + flags + placar) para debug/testes determinísticos
- Cache-bust: game v30→**31** · styles v17→**18**

### Suite-safety (por construção)
- Asserts da suite são relativos/simbólicos (decisão P2): nenhum HP/dano absoluto quebrado
- Scores seguem atualizando via `score-blue`/`score-red` (F-SMOKE) e o `match-timer` segue
  renderizando `MM:SS` (F4); prorrogação só dispara em t=0 com empate — testes nunca
  chegam lá organicamente

### Boot Hardening (auditoria estática de races — delegada a agente)
- **P0**: fetch do `roster_meta.json` era o único dos 5 do boot sem `.catch` (404/timeout =
  boot morto silencioso) → `.catch(() => ({}))` + `rosterMeta = (metaRes && metaRes.roster) || []`
- **P0**: `init()` bare → `init().catch(err => console.error('[NUBA] BOOT FALHOU:', err))`
  (rastro claro em vez de tela preta)
- **P0**: spawn do `start5v5Match` sem proteção → try/catch no `Promise.all` dos `spawnTeam`:
  falha de modelo = `matchActive=false` + banner, **sem partida zumbi** (antes: HUD ativo + units vazio)
- **P1**: `updateLobbyTeamsPreview` deref `blueHeroes[0]` sem guard (crash com heroId fora do roster) → early-return + fallback
- **P2**: arg guards em `executeSkill`/`dealDamage` (robustez para E2E/cold)
- Auditoria: 45 hooks `window.*` mapeados, 42 já guardados, 3 riscos corrigidos aqui;
  `boot_race_audit.json` no workspace (agente interrompido gravou o JSON completo antes)

### Validação
- Smoke determinístico T5: HP ×1.5 em 10/10 units, dano `round(raw×0.9×dr)` exato,
  prorrogação aos 5:00 empatados (flag+classe laranja+60s), morte súbita após prorrogação
  (flag+classe vermelha, partida viva), abate encerra na morte súbita, e vitória por tempo
  com placar desempatado (sem prorrogação)
- Bateria: `verify` + `test_e2e_suite.py` 38/38 isolado (dono único do WebGL)
- Rollback: `public/*.bak_t5`

**Verdict: T5 DONE — partida respira nos 5 minutos pedidos, empate tem prorrogação dramática, e o time-to-kill ficou mais longo.**


---

## 13. Re-Verification — SPP: Skill Presentation Pass (2026-10-20)

### Pedido do usuário
- "Usar o REA pra extrair os visuais e direções das skills corretamente... clones das sombras
  parecer os clones 3D do Naruto, o rasengan com casting e visual... assim como todos" +
  "se necessário usar o Blender, MCP, para alinear as animações de skills e efeitos"

### Nota de ferramentas
- **REA**: não está instalado na máquina — e é desnecessário: os chunks que importam
  (`nuccChunkAnm` skl1/skl2, `eff1`/spc, `bod1`) JÁ foram decodificados pelo toolchain Python
  próprio do repo (APK_REVERSE.md §3) — castings 19-bone por herói em `animations.json`,
  VFX em `skill_vfx.json`, modelos com rig em `models/*.json`
- **Blender**: 5.2 instalado; não existe MCP de Blender no catálogo Hermes — headless via CLI
  (`blender -b --python`), o mesmo fluxo já comprovado do `tools/blender_validate_all.py`

### Implementação (SPP v1)
- **Kage Bunshin REAL (Naruto W)**: `spawnShadowClones` — 3 clones 3D com o modelo extraído
  do próprio Naruto (`cloneCharacterModel` + rig de 20 bones), opacidade 0.85, **poof de
  fumaça na invocação**, perseguição pela arena (busca 999 — lição M6.2), anim `run` real,
  dano em contato (60% do kit) + poof; TTL 4.5s com poof de saída; reset no rematch
- **Anim procedural por skill**: `SKILL_VFX_ANIM` (10 heróis × 4 slots): spin (rasengan,
  chidori, kaiten, palms), thrust (fireball, water dragon, toad fire, air palm), pulse
  (selos, areia, auras), rise (fumacas, amaterasu) — engine no update do `vfxList`
- **Facing**: VFX extraído nasce com `rotation.y = rotY` do caster (extGrp encara a direção
  do cast) + `faceDir` para thrust
- Exposição E2E: `window.SKILL_VFX_ANIM` + `window.__shadowClones()` (padrão M7)
- Aditivo por design: nenhum dano/cooldown existente mudou — suite-safe

### Como o SPP se encaixa no que já existia
- O rasengan do Naruto Q JÁ tinha bind no osso da mão (13) e o chidori no 9 (P1 JUICE);
  o SPP adiciona a camada de anim + facing que faltava nos casts que usam `spawnVFX` puro

### Validação
- Smoke determinístico SPP: 9/9 PASS — 3 clones spawnam rigados, perseguem (delta pos real),
  dano em contato + poof, TTL limpa, Q com anim spin, reset no rematch
- Bugs de smoke achados e corrigidos no caminho: (1) W do Naruto tem branch específico que
  nunca chega no genérico `clone_burst` — clones wired no branch certo; (2) busca de alvo
  dos clones tinha raio 45 (cidade-fantasma M6.2 de novo) → 999
- Bateria: verify + suite 38/38 isolado (`spp_*.log`)
- Auditoria Blender (direções): `tools/spp_blender_audit.py` → `spp_blender_report.json`
  (bbox/eixo principal/yaw sugerido por modelo; directionais ganham bake)
- Rollbacks: `public/*.bak_spp` + `public/*.bak_sppexp`

**Verdict: SPP v1 DONE — Kage Bunshin invoca clones 3D de verdade e as 40 skills têm anim + direção.**