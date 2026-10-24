# Pivot NUBA → Mobile (estilo T3 Arena / Brawl Stars): Combate 3v3 + Realeza na Vila

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.
> **For agents do repo (Antigravity):** este arquivo é CONTRATO — copiar para `docs/PIVOT_MOBILE.md` e implementar contra ele; docs desatualizados causam regressão (regra PROJECT.md).

**Goal:** Pivotar o NUBA de MOBA 5v5 desktop-first para jogo MOBILE-FIRST no estilo T3 Arena / Brawl Stars — com dois modos: **Combate 3v3** (deathmatch com respawn) e **Realeza na Vila** (battle royale solo em Konoha) — preservando 100% do tema Naruto Storm, visual Storm Cinematic, roster, áudio autêntico, juice e a suite E2E 38/38.

**Architecture:** Camada de input abstraída (`InputState` único consumido pelo update loop) como fundação; formato de partida virando config (`MATCH_CONFIGS` + `startMatch(id)` com alias legacy `window.start5v5Match`); modo BR encaixado como variante do match core existente (spawn/endMatch/results). Zero mexida no combate real: touch apenas ESCREVE no mesmo estado que teclado já escreve. Controles novos são 100% aditivos no DOM (`#touch-*`); IDs existentes intactos.

**Tech Stack:** Three.js r169 (já no repo), Web Audio (SFX autênticos já wireados), CDP + Edge headless para testes (já no repo), provider registry local para provider dev; sem engine nova, sem dependência nova.

---

## 1. Contexto atual e reuso

| Sistema | Estado hoje | Reuso na pivotagem |
|---|---|---|
| Match core | `start5v5Match()` game.js:1526 — 5:00 (L220), 30 kills (L217 `TARGET_KILLS`), respawn, prorrogação 60s + morte súbita (T5) | **Parametrizar via `MATCH_CONFIGS`** — prorrogação/sudden death reaproveitados nos 2 modos; `start5v5Match` vira alias legacy para E2E |
| Input | keydown game.js:5541 + pointerdown 5431 (mouse). **Zero código touch** | **`InputState` abstraction** — teclado escreve no estado novo; F08–F17 E2E intactos |
| Câmera | `cameraMode = 'moba' | 'thirdperson'` (L180), `clampCamera` (L209, invariante dos testes F11) | Perfil `thirdperson` vira **câmera mobile padrão**; clamp preservado byte-a-byte |
| Slots HUD | `#slot-atk/q/w/e/r/c` já são `<button>` (index.html:399–454), cooldown sweep, custo | Viram **alvos touch reais** (CSS escala + handlers chamam `executeSkill`, L5541 como fonte); NOMES/ids inalterados |
| Arenas | 5 arena: sd00a Konoha (±88, 122 meshes, 63k verts), sd03b Coliseu, sd01b Torre, sd01a Vale, sd05a Planície | **sd00a = "A Vila"** do BR; demais viram pools do DM 3v3 |
| Roster | 10 ninjas + pipeline 11-20 rodando (W2.1) | DM 3v3 usa pool livre (6 heróis aleatórios distintos por partida); BR = 1 por herói |
| Combate | `HERO_STATS` (hp 850–1250), 40 kits únicos, TTK ×1.67 (T5), chakra CK, awakening | **Intacto** — TTK longo já é ideal pra touch |
| VFX/áudio | `SKILL_VFX_MAP`, 30 modelos autênticos, AUTH_SFX (494 cues) | Intactos; ring VFX reusado na zona 結界 |
| Juice | hitstop/slow-mo/shake em `dt` real (contrato E2E), `window.JUICE` | **Intacto** — shake gateado por envolvimento continua |
| E2E | 38/38 via CDP, DOM inviolável (`UI_SKIN_CONTRACT.md`) | Ganha **Tier 5 Mobile** (touch dispatch); legado segue verde |
| Deploy | Vercel estático, <15MB (P6) | Mobile web MVP cabe; PWA manifest depois (PV3.3) |

## 2. Design da pivotagem

### 2.1 Matriz de referência (proposta)

| Dimensão | T3 Arena | Brawl Stars | NUBA hoje | NUBA mobile (proposta) |
|---|---|---|---|---|
| Formato | 3v3 hero shooter | 3v3 top-down | **5v5 MOBA** | **3v3 DM (respawn) + BR solo 10** |
| Duração típica | ~3–4 min | ~2,5 min | 5:00 + prorrogação | **3:00 DM · ~4:00 BR** |
| Câmera | 3ª pessoa sobre ombro | top-down travada | MOBA livre + 3ª pessoa | **3ª pessoa travada no player (perfil já existe)** |
| Controles | dual stick + assist | stick + tap | teclado + mouse | **joystick esq. + cluster botões dir.** |
| Mira | assist | auto / drag-aim | 100% manual | **auto-aim + drag-aim indicador** |
| Vitória | kills / pontos | por modo | 30 kills / tempo | **15 kills / 3min · BR último vivo** |
| Respawn | sim | por modo | sim | **DM sim (5s) · BR NUNCA** |
| Meta | heróis + passe | brawlers + passe | perfil local | perfil local (aba Perfil já existe) |

### 2.2 Modo A — Combate 3v3 (DM mobile-first)

- **`MATCH_CONFIGS`** (única fonte de verdade por modo):

```js
const MATCH_CONFIGS = {
  dm_3v3:        { label:'COMBATE 3v3',      teamSize:3, killTarget:15, time:180, respawn:5,
                   overtime:30, suddenDeath:true, mode:'dm' },   // prorrogação reusa T5
  dm_legacy_5v5: { label:'COMBATE 5v5',      teamSize:5, killTarget:30, time:300, respawn:5,
                   overtime:60, suddenDeath:true, mode:'dm' },   // = comportamento atual (E2E legado)
  br_vila:       { label:'REALEZA NA VILA',  arena:'sd00a',  players:10, squad:1,
                   time:0, respawn:0, mode:'br' }                // tempo governado pela ZONA
};
window.startMatch = async (id) => startMatch(id);
window.start5v5Match = () => startMatch('dm_legacy_5v5'); // alias LEGACY — 38 testes em paz
```

- Regras herdadas do T5 que continuam valendo: empate em 5:00→aqui 3:00 (config) → prorrogação 30s → morte súbita (próximo abate vence, timer vermelho pulsante).
- `spawnShield` 4s pós-spawn continua (já mitiga spawn trap — ainda mais importante com 3 jogadores por lado).
- HUD: retratos 3+3 (`renderTeamPortraits` param `teamSize`), `#score-goal` "META: 15 ABATES" (dinâmico).

### 2.3 Modo B — Realeza na Vila (BR solo, sd00a)

- **10 ninjas, solo puro**: `teamId` único por unit; 9 bots preenchem 1 herói distinto cada (`roster_meta`).
- Sem score de time — win = último de pé; empate impossível; **Vitória FFA**.
- **Zona 結界 (kekkai — barreira de chakra)**: tabela canônica (raios em unidades de arena, fase 0 = formação):

| Fase | Raio (sf00a) | Duração | Dano fora/s | Efeito |
|---|---|---|---|---|
| 0 · Formação | 88 estático | 30s | 0 | toca cue `S_battleStart` |
| 1 | 88 → 64 | 40s | 12 | ring fica visível (contração) |
| 2 | 64 → 42 | 35s | 25 | — |
| 3 | 42 → 24 | 30s | 45 | — |
| 4 | 24 → 10 | 25s | 70 | — |
| Final | 10 → 2 | 20s | 100 | ring dourado → vermelho pulsante (kanji 結界 no HUD) |

  HUD BR: contador de vivos, timer da fase atual, ring minimapa (diverge da lógica DM — implementar overlay `#zone-*`). Dano do BR escalado por `HERO_HP_SCALE` ( médias ~1400 HP com T5 1.5×).
- **Pergaminhos de chakra** (pickup, ~10 espalhados): `+8% HP máx` e `+5% dano` por stack, máx 6; dropam metade dos stacks ao morrer; baú = caixa com poof VFX (reuso `kawarimi` smoke) e clone-safe TTL.
- Resultados: overlay `#match-results-overlay` (M5 já existe) em modo placement — 1º destino em destaque ("覇者"), linhas 1º–10º com abates; REVANCHE repopula o mesmo modo (recordMatchResult marca `mode:'br'` + placement).

### 2.4 Controles touch (núcleo da pivotagem)

**Contrato:** `InputState` única, consumida pelo update loop de movimento/câmera/combate (onde hoje lê `keys`/`mouseDown`). Teclado e touch ESCREVEM no mesmo estado; nada de código novo de combate.

```js
// abstração (novo)
window.INPUT = {
  moveX: 0, moveZ: 0,          // -1..1, camera-relative no consumo
  aimX: 0, aimZ: 0,            // direção manual (drag-aim); 0 = auto-aim
  aimLocked: false,            // true = mira no alvo, facing trava
  firePressed: false,          // edge one-shot consumido pelo update
  slots: {}                    // { q:false, w:false, e:false, r:false, c:false }
};
```

Componentes DOM aditivos:

| Componente | Especificação |
|---|---|
| `#touch-joystick` | Zona esq. 42% da tela: spawn flutuante no toque, r 64px, dead-zone 0.18, pointerId exclusivo, anel visual |
| `#touch-cluster` | Botões direita: ATK grande (80px) + Q/W/R (64px) + kawarimi ūnico (64px) + chakra hold (64px) |
| Drag-aim | `#touch-cluster` arrasto ≥24px mostra indicador no chão (decal reuso VFX common); solta = `aimX/aimZ` na direção |
| Auto-aim | `findAimTarget(unit, range)`: inimigo mais próximo em alcance, preferindo cone frontal 120°; ATK tap = melee lock; skills travam `rotY` no alvo |
| `body.touch` | CSS troca layout: esconde badges de tecla (M1/Q/E/R) e drawer TECLAS; alvos ≥64px; safe-area `env()` |
| Touch details | `touch-action:none` em canvas/HUD; multi-touch por `pointerId`; `navigator.vibrate(15)` hit / `(40)` abate |
| Orientação | **Landscape** (manifest orientation lock); portrait = overlay "gire o dispositivo" |

### 2.5 Câmera mobile

- `cameraMode='thirdperson'` quando `body.touch` auto-select (default do config mobile).
- FOV 58, distância atrás 9–11u (knobs já existentes `camHorizDist`), pitch fixo ~35°, look-ahead 4u na direção do joystick, clamp preservado (F11).
- Pan do mouse (drag-look L5451) desligado com `body.touch`.

### 2.6 Perf mobile (budget verificável)

| Métrica | Alvo | Medição |
|---|---|---|
| FPS sustentado | ≥30 mid-range (Adreno 6xx) | `window.__PERF` — avg/min, media de 2 min em partida |
| Cold load | <10s em 4G | teste E2E mede até `¡partida iniciada` |
| RAM | <400 MB | E2E lê `performance.memory` (heurístico) |
| Pixel ratio | cap 1,25 mobile | inspeção `renderer.getPixelRatio()` |
| VFX simultâneos | ≤24 | `vfxList.length` máximo durante stress probe (10 clones + skills) |
| Draw calls | <180 | probe CDP `renderer.info.render.calls` — arena merge PV3.2 |
| Skinned units | 10 (já é budget 5v5) | BR 10 = mesmo custo de hoje |

---

## 3. Fases e tasks (bite-sized; DoD do repo por task: `node --check` → `verify_browser_runtime.py` 0 erros → `test_e2e_suite.py` verde → docs atualizados)

### Fase PV0 — Fundação Mobile (nada existente quebra) — **STATUS: DONE (2026-10-21, bateria verde)**

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV0.1 | Meta viewport/visualViewport + `touch-action:none` canvas/HUD + `overscroll-behavior:none` + safe-area CSS vars + overlay "gire o dispositivo" | `index.html:5`, `styles.css` (bloco "MOBILE FOUNDATION") | verify 0 erros; suite 38/38 |
| PV0.2 | Detector: `window.__DEVICE` (isTouch, isMobile, dpr) + `body.classList.toggle('touch')` | `game.js` (novo bloco, topo) | unit probe via CDP `typeof __DEVICE` |
| PV0.3 | **`InputState` abstraction**: estado único (§2.4) consumido onde hoje se lê `keys` (L5541+) / `mouseDown`; teclado/pont continuam escrevendo — ZERO mudança de comportamento desktop | `game.js` update loop, input listeners | F08–F17 legado verde (prova: suite) |
| PV0.4 | **Baseline obrigatória** antes da PV1 (regra repo: repo tem dev paralelo) | — | 38/38 + baseline_suite.log renovado |

### Fase PV1 — Combate 3v3 mobile MVP — **STATUS: DONE TOTAL (probes 2026-10-21 + PV1.6 Tier 5 FORMAL na suite 2026-10-22: 47/47)**

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV1.1 | `MATCH_CONFIGS` + `startMatch(id)` + alias `window.start5v5Match` (legacy) | `game.js:1526` região | legado 5v5: 38/38 intactos |
| PV1.2 | `dm_3v3`: teamSize 3, killTarget 15, time 180, respawn 5; `renderTeamPortraits(3)`; `#score-goal` dinâmico | `game.js` (match start, HUD sync) | novo Tier 5 assert 3 retratos/time + META 15 |
| PV1.3 | `#touch-joystick` (especificação §2.4) escreve `INPUT.moveX/Z` | `index.html` (aditivo), `styles.css`, `game.js` | T5: dispatchTouchEvent drag → unidade move (ler `u.x/u.z` delta) |
| PV1.4 | `#touch-cluster`: botões alvos ≥64px sobre os slots existentes (handlers espelham keydown L5541 → `executeSkill`) + `findAimTarget` + drag-aim indicador | `index.html`, `game.js`, `styles.css` | T5: tap ATK → `__matchState`/unit executou `atk`; auto-aim lock |
| PV1.5 | Câmera mobile: thirdperson auto + look-ahead joystick; pan off touch; clamp invariante | `game.js` §camera | F11 clamp + T5 snap-behind |
| PV1.6 | **Tier 5 E2E Mobile**: CDP `Input.dispatchTouchEvent` (joystick/ATK/Q/kawarimi/chakra) + `Emulation.setDeviceMetricsOverride(412×915)`; updates `PROJECT.md`/`TEST_READY.md` §Tier 5 | `tools/test_e2e_suite.py`, docs | 38/38 + novos testes verdes |

### Tier 5 E2E — PV1.6 entregue (2026-10-22): touch real na suite canonica

9 testes "Tier 5" em `tools/test_e2e_suite.py` (38 → **47**), touch de verdade via
`Input.dispatchTouchEvent` (mesma pipeline de um dedo: pointerdown/up com pointerType
touch) — nao mais so probes ad-hoc:

| Teste | O que prova |
|---|---|
| T5_M01 | Emulacao iPhone 844x390 no boot: `__DEVICE.isMobile`, overlay oculto em landscape, governor dprCap 1.25 + vfxCap 24 |
| T5_M02 | Arena DEFAULT do lobby carrega a **variante `.mobile.json`** (17 meshes) — PV3.2 dentro da suite |
| T5_M03 | 3v3 mobile: 6 units, 3 retratos/time, META 15, touch-cluster grid, `__matchState.br === null` |
| T5_M04 | **Joystick real**: touchStart/move/end → vetor `INPUT` + unidade anda +X + reset ao soltar |
| T5_M05 | **ATK hold**: `INPUT.fire` true/false, `.pressed`, ataque dispara (cd/estado) |
| T5_M06 | **Tap Q**: `executeSkill` + espelho de CD vivo em `#cdt-q` (conic/segundos) |
| T5_M07 | **Hold chakra**: `INPUT.chakra` true/false |
| T5_M08 | **Realeza na Vila mobile** (PV2.6): 10 ninjas, zona 65→6 encolhendo, 12 baus, `sa00z.mobile.json`, HUD BR |
| T5_M09 | Portrait → overlay "gire o dispositivo"; restaura desktop no fim (UA set + reload) |

Bateria: **47/47 + verify 0 erros** (decima verde). Pitfalls reais da rodada:
CDP **descarta valores `undefined`** do `returnByValue` (KeyError no Python — `__matchState`
nao tem `mode`; o discriminador e `br === null`); `startMatch('br_vila')` em MOBILE leva
**~32s** (desktop 8.6s) e estoura o timeout CDP de 30s com `TimeoutError` de mensagem VAZIA;
`Emulation.clearUserAgentOverride` **nao propaga no headless** — restaurar via SET desktop.

### Fase PV2 — Realeza na Vila — **STATUS: MODO BR JOGÁVEL (probe 8/8 + Tier 5 M08 formal na suite 47/47)**
- `MATCH_CONFIGS.br_vila`: solo 10, sem respawn, zona 65→6 em 6 fases, 180s, layout real via `br_vila_layout.json`
- `startBRMatch` (game.js): spawn solo no anel real, zona 結界 (cilindro roxo translúcido escala=raio), 12 baús âmbar (+35 HP/+50 chakra), `playMatchIntro([playerHero], roster.slice(1))`
- `updateBR(dt)` no `updateMatch`: fases a cada 25s, raio contínuo entre fases, drain `2+fase` HP/s fora do raio (+1.5 tolerância), coleta por proximidade (2.6u), last-standing → `brEndMatch` reusa `endMatch` (scoreBlue/Red 1/0)
- Morte permanente no rebirth (PV2) + timeout sem prorrogação decide por HP (PV2); `killTarget != null` blindado (PV2-C)
- Loader webp-first com placeholder 1×1 no fallback (PV2-E) + filtros de ruído nos coletores (PV2-D/F)
- Pendente fino: squad 2v2 quando W2.1 (roster 20) chegar; chest loot variado

**Mapa (evidência, não estimativa)**: contorno polar raycast 72 ângulos (tools/br_vila_layout_map2.py) — núcleo contíguo r45-80 + braço leste até r130; `zoneRadiusStart=65`. Layout gravado em `public/assets/data/br_vila_layout.json`:
- `spawnRing`: 10 spawns solo no anel REAL da vila (r 35-55): (55,0) (44,32) (15,48) (-17,52) (-44,32) (-55,0) (-44,-32) (-17,-52) (14,-43) (44,-32)
- `zoneCenter (-10,0)`, zona 結界 65 → 6 em 6 fases
- `chests`: 12 baús no núcleo denso (±40)
- Santuários DM corrigidos para DENTRO da vila: blue (-40,-30) / red (45,30) (±95 originais caíam no vazio — player spawnava fora do visual) (BR)

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV2.1 | `MODES` registry + seletor de modo no lobby (cards em `#page-play`: COMBATE 3v3 · CLÁSSICO 5v5 · REALEZA NA VILA) | `index.html`, `styles.css`, `game.js` | T5: clique no card inicia modo certo (`__matchState.mode`) |
| PV2.2 | BR match core: 10 spawns espalhados (anel r≈70 + jitter espaçado ≥18u), `teamId` único, sem respawn, `matchRecorded` com placement | `game.js` (spawn/endMatch) | T5: `br_vila` = 10 units, 0 teamIds compartilhados |
| PV2.3 | **Zona 結界**: fases da tabela §2.3, ring VFX (cilindro aditivo reuso aura), dano por tick fora da zona, HUD `#zone-*` (vivos/timer/ring minimapa) | `game.js` (novo módulo ZONE + HUD aditivo) | T5: simular fase → raio decresce; unit fora perde HP |
| PV2.4 | Baús + pergaminhos: stacks +8%HP/+5%dmg (máx 6), drop 50% no abate, poof | `game.js` (pickups) | T5: stack aplica delta em `HERO_STATS` efetivo; drop existe |
| PV2.5 | BR results: overlay placement 1º–10º ("覇者" 1º), REVANCHE repseta BR, `recordMatchResult({mode:'br',place})` | `game.js` showMatchResults, `styles.css` | T5: overlay placement visível; profile grava |
| PV2.6 | Tier 5 BR tests + docs (`PROJECT.md` milestones BR, `TEST_READY.md` §BR) | `tools/`, docs | bateria completa verde |

### Fase PV3 — Perf e polimento mobile

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV3.1 | Quality governor (dpr cap 1.25, sombras off mobile, VFX cap 24) + `window.__PERF` + teste de budget probes | `game.js`, `tools/` | T5: ratio/FPS asserts |
| PV3.2 | Arena merge (sd00a 122 meshes → ~20 grupos), load order (arena → heróis lazy VFX) | `tools/build_arena.py` pipeline + `game.js` loader | T5: calls <180, cold load <10s alvo |
| PV3.3 | Hapticas (`navigator.vibrate`) + audio unlock no 1º toque + PWA manifest (orientation landscape, theme #f97316-ish do Storm) | `game.js`, `index.html`, `public/manifest.webmanifest` | instala manual no Chrome Android |
| PV3.4 | Smoke dispositivo real (user): LAN `http://<ip>:8080` (ou tunnel) — checklist | — | evidência do usuário (screenshot) |

### Fase PV3 — status de entrega (2026-10-21)

| Item | Status | Evidencia |
|---|---|---|
| PV3.1 Quality governor (dpr cap 1.25 + VFX cap 24 em mobile) | ENTREGUE | `window.__GOV` no boot; `probe_pv3_polish` 4/4 (pixelRatio real = 1.25) |
| PV3.1 VFX cap no loop | ENTREGUE | pico natural de **273 VFX** na injecao de 40 impactos → **≤24** apos o cap |
| PV3.2 Arena merge mobile | **ENTREGUE** | `tools/arena_blender_optimize.py -- <id>`: **sd03b 294→17 meshes (-94%)**, sd00a 122→33 (-73%); `mapMobile` + `?v=11`; probe 9/9 — mobile **109 draw calls** vs desktop **390** (-72%) |
| PV3.3 Haptics + audio unlock + PWA manifest | ENTREGUE (haptics + PWA) | `haptic()` throttle 60ms + gate de perfil; `manifest.webmanifest` + icones 192/512; `probe_pv3_polish` PWA 9/9 |
| PV3.4 Smoke em device real (LAN/tunnel) | PENDENTE (depende do usuario) | checklist no probe responsivo |

### Fase PV4 — Touch HUD V2 (entregue 2026-10-21, pedido do usuario)

| # | Tarefa | Implementacao | Validacao |
|---|---|---|---|
| PV4.1 | HUD touch enxuto: mapa no topo, HP/chakra cada um de um lado, base so joystick+skills | Gates `body.touch #hud-screen.active` em styles.css (reposiciona via `position:fixed`/`display:contents`, esconde o que nao faz sentido) + 5 divs `.tbtn-cd` nos tbtns + espelho de CD no updater de `game.js` | probe_pv4_hud 13/13 + probe_responsive 5/5 |


---

## 4. Contratos preservados (regras de ouro da pivotagem)

1. **DOM inviolável** (`UI_SKIN_CONTRACT.md`): nada de remover/renomear IDs; aditivos apenas (`#touch-joystick`, `#touch-cluster`, `#zone-*`, `.ctx-*`); esconder com CSS, nunca deletar elementos que o JS popula.
2. `window.start5v5Match`, `window.__matchState`, `window.JUICE`, `window.units` — preservados (E2E legado leitor).
3. Timers/CDs/respawn/awakening em **dt real**; só cadência de sim escala (`simDt`) — contrato juice + asserts de parede.
4. Câmera: `clampCamera` (±`cameraLimit`) invariante em qualquer modo, mesmo em shake.
5. Cache-buster automático — NUNCA escrever patch de cache-bust manual; `.bak_pv*` rollback por fase; reparos cirúrgicos (`patch` re-ancored, âncoras re-buscadas antes de cada patcher — dev paralelo mexe os arquivos).
6. **Docs antes de código**: este plano copiado para `docs/PIVOT_MOBILE.md` do repo; cada task verificada atualiza `PROJECT.md` (feature row) + `TEST_READY.md` (seção) — agentes implementam CONTRA os docs.
7. Suite legada 38/38 verde durante TODA a transição; regressão no legado = rollback da task, não "consertar depois".

## 5. Riscos e mitigação

| Risco | Impacto | Mitigação |
|---|---|---|
| E2E legado assume 5v5 (T1_F02: 5 retratos/time; F04: "META: 30 ABATES") | Vermelho na transição | Tasks PV1.1/PV1.2 atualizam SÓ asserts afetados e roteiam para `dm_legacy_5v5` default; novas asserts Tier 5 cobrem 3v3 |
| Perf WebGL em Android baixo (arena 63k verts + 10 skinned + VFX) | Frame drops, quente | Budget table §2.6 + governor PV3.1/merge PV3.2; BR cap 10 = custo do 5v5 atual |
| Auto-aim desbalanceia TTK | Partidas decididas por toque errado | Knobs em config (autoAimCone/range por herói), não hardcode; sanity: `findAimTarget` só considera alvos em range do skill |
| Dev paralelo Antigravity sobrescreve docs/código | Conflito de âncoras | Plano no repo como contrato; re-`git stash`/re-leitura antes de cada patcher; backups `.bak` |
| Sem device real no CI | Falso "funciona" | CDP emula touch em viewport 412×915 + smoke manual PV3.4 obrigatório antes de declarar mobile pronto |
| Portrait usabilidade ruim | Retenção | Overlay "gire"; manifest lock landscape |
| Skill stack (Q/W/E/R/c + ATK + joystick + kawarimi) em dedo | Erro de input | Cluster direito espelhado do HUD (contagem igual ao teclado); sem slots novos no mobile; ATK em zona de polegar confortável |

## 6. Decisões (2026-10-21 — aprovadas pelo usuário, viram contrato)

1. **3v3 substitui 5v5 como padrão TAMBÉM em desktop.** `dm_3v3` é o default do lobby em qualquer dispositivo; `dm_legacy_5v5` permanece como card "CLÁSSICO 5v5" no seletor de modo (config pura, mantém caminho dos testes legados).
2. **BR = solo puro, 10 ninjas padrão** (player + 9 bots, 1 por herói). Sem duo no MVP; quando W2.1 entregar roster 20, `players` sobe por config.
3. **Landscape-only**: manifest lock + overlay "gire o dispositivo" em portrait.
4. **Execução autorizada desta rodada: PV0 + PV1** (MVP mobile jogável). PV2 (BR) na sequência.
5. **Escopo adicional autorizado — Mapeamento da vila para o BR**: inventariar os 9 stages do APK (8 extraídos, falta `sd05b`), mapear sd00a (spawn ring, baús, cover) e **investigar/extrair a Konoha real do modo aventura** (`KonohaAct`: chunks `data_stage_MAP/CAM/DMY/FLY/GIMKonohaAct` + 10 `GIMKonohaActPerson_XX` encontrados no APK) — se a geometria da vila real for extraível, ela vira o mapa do BR em vez do campo de treinamento.

## 7. Fora de escopo (explícito)

- Netcode P5/P6 (modo registry já nasce preparado para `mode` server-authoritative).
- Monetização, skins (variantes `bod1c/bod1l/bod1s` existem no APK — fila futura independente).
- Wrapper nativo (Capacitor/TWA) — mobile web MVP primeiro; empacotamento é fase posterior de 1 comando quando P6 chegar.
- Novos heróis W2.1 (segue em paralelo e naturalmente alimenta o BR quando expandir para 20).
- Retrabalho estético: **tema, HUD Storm Cinematic, kanji, áudio e juice permanecem EXATAMENTE como estão** — a pivotagem é de formato/controle, não de identidade.

---

## Ordem de execução e esforço

| Fase | Conteúdo | Tasks | Dependência | Esforço relativo |
|---|---|---|---|---|
| PV0 | Fundação mobile (input+viewport+device) | 4 | nada | 1× |
| PV1 | DM 3v3 + controles touch completos | 6 | PV0 | 2× |
| PV2 | Realeza na Vila (BR) | 6 | PV1 | 2,5× |
| PV3 | Perf + polish + device smoke | 4 | PV1/PV2 | 1× |

**MVP jogável no celular = PV0 + PV1** (deathmatch 3v3 tocável, sem quebrar o desktop). BR é a camada seguinte que reusa tudo.

---

## 8. Plano v2 (PV-A..PV-F) — 2026-10-21 — contrato vigente

> Este apendice substitui as estimativas de §2.6 e §PV3 (que a medição refutou) e
> incorpora as decisões do usuário: **Brawl Stars puro (arena 3v3 + Realeza na Vila,
> sem lane/torre/minion)**, **netcode mobile entra no roadmap (3v3 online + ranking)**,
> **piso de dispositivo moderno (Android 8+/iOS 15+) com WebP**, **assets atuais mantidos**.

### 8.0 Estado real no início do v2 (medido, não estimado)

| Item | Estado | Evidência |
|---|---|---|
| PV0.1/0.2 viewport + __DEVICE | ✅ | game.js:5-14 |
| PV0.3 InputState | ✅ | window.INPUT (game.js:16), consumo em 5068/5090/5091/5163 |
| PV1.1/1.2 MATCH_CONFIGS + startMatch | ✅ | game.js:282-291, 5815 |
| PV1.3-1.5 joystick + cluster + câmera mobile | ✅ | index.html:534-535, styles.css:4878-4899, game.js:5851+ |
| PV1.6 Tier 5 E2E mobile | ✅ | commits e3dd1ed, d1c2354 |
| PV2 (BR) | 🟡 mapa pronto, modo pendente | r_vila_layout.json, sa00z.mobile.json |
| **Instrumentação de perf** | ❌ (agora entregue no PV-A) | window.__PERF, 	ools/measure_perf.py |
| **Higiene de payload** | ❌ | 0 arquivos .webp; stage_3d.json (7,29 MB) baixado no boot (game.js:5528); 	extureCache (:225) nunca purgado; ssets/arena é Junction com .gitignore inconsistente |
| **Perf mobile** | ❌ | ver baseline abaixo |
| **Netcode / release mobile** | ❌ | nada de ws; sem dist/ |

### 8.1 Baseline medido (PV-A) — Edge headless 1254x627, modo dm_3v3

| Métrica | Valor medido | Alvo v2 | Gap |
|---|---|---|---|
| Payload de boot | **26,44 MB** | < 12 MB (3v3) | -14 MB |
| stage_3d.json (inútil, substituído 2 linhas depois) | 7,29 MB | 0 | -7,29 MB |
| Draw calls (partida 3v3) | **478 avg / 650 max** | < 180 | -300 |
| Triângulos | 170,8k avg | < 120k | -50k |
| **Geometrias vivas** | **1.091 avg / 1.746 max** | < 250 | -840 (churn de spawnVFX) |
| Texturas | 51 | < 40 | -11 |
| CPU frame (p95) | 100 ms | < 33 ms (30 fps) | -67 ms |
| **VFX simultâneos** | **163** | ≤ 24 | -139 |
| Unidades | 6 (3v3 ✅) | 6 | ok |

> Nota de método: o headless usa rasterização por software (--disable-gpu), então **FPS
> não representa device real**. A métrica confiável de device é **CPU frame time** +
> draw calls + geometrias vivas. 	ools/measure_perf.py reporta ambos.

### 8.2 Fases restantes (execução fase a fase, 38/38 + verify 0 erros ao fim de cada)

| Fase | Tasks | Conteúdo | Aceite |
|---|---|---|---|
| **PV-A** | 2 | window.__PERF (fps/cpuFrame/drawCalls/triangles/geometries/textures/programs/payload) + 	ools/measure_perf.py (lobby + partida, JSON + screenshot) + baseline | ✅ 38/38, 0 erros, baseline em perf_reports/ |
| **PV-B** | 5 | (1) matar o fetch de stage_3d.json; (2) WebP: arena q80, UI/VFX q90, com QA visual por diff; (3) purge de 	extureCache na troca de arena; (4) canonicalizar ssets/arena (Junction → 1 caminho, repo+server+deploy coerentes); (5) dist/ build com gzip/brotli | payload boot < 14 MB; nenhum 404; 38/38 |
| **PV-C** | 6 | quality governor (dpr 1,0-1,25, sem MSAA, FrontSide onde validado, cap de VFX 24) + merge de arena por textura + InstancedMesh (folhas/grama) + reuso de geometria de herói (SkeletonUtils.clone) + skin quantizada (Uint8) + throttles de CPU (labels/minimap/scoreboard) | draw calls < 180, geometrias < 250, cpuFrame p95 < 33 ms |
| **PV-D** | 5 | modo BR: zona 結界 (6 fases, 65→6), dano fora da zona, 12 baús/pergaminhos (+8% HP / +5% dano, máx 6, drop 50%), placement 1º-10º, HUD de vivos/fase | Tier 5 BR verde; 38/38 |
| **PV-E** | 7 | online 3v3 + ranking: server/ (Node+ws+sqlite), host-authoritative com **placar/kill/MMR no servidor**, snapshot binário delta 15-20 Hz, predição+interpolação 100 ms, reconexão, contas/MMR/temporada, Tier 5 online (2 browsers) | 2 contas → fila → sala → partida → MMR atualizado |
| **PV-F** | 5 | release mobile: PWA landscape + offline do shell, TLS/VPS, QA multi-device, observabilidade, docs de operação | instalável, 30+ fps em device, 38/38 + Tier 5 no CI |

### 8.3 Fora de escopo (decisão do usuário)

Lane, torre, minions, itens/loja, monetização, skins, wrapper nativo, novos heróis.
**Tema, skin Storm, VFX, áudio, kanji e juice permanecem exatamente como estão.**

### 8.5 W5 — Áudio autêntico do APK na batalha (pedido direto do usuário 2026-10-22)
#### 8.5.1 W5-F2 — Vozes de batalha POR HERÓI (bancos PL_1XXX) — 2026-10-23

Descoberta-chave: o APK carrega **um voice bank por ninja** no `sound.awb`
(CPK interno): `PL_1nrt.xfbin` ... `PL_1tyo.xfbin` (30 ninjas, ~78 cues de
batalha cada — `S_PL_DmgS1-3`, `DmgM1-2`, `DmgL1-2`, `AtkS1-3`, `AtkM1-2`,
`AtkL1-2`, `Combo1-3`, `Awake`, `Catch`, `GrdBrk1-2`...). Extração: ACB
embutido no xfbin (`tools/extract_pl_banks.py` @UTF 8+tsize) ->
`tools/extract_voices_nuba.py` (vgmstream 56 subsongs + ffmpeg mono q2) ->
**252 oggs (21 cues × 12 heróis do NUBA, 2,6 MB)** em
`public/assets/audio/decoded/voice/<heroId>/S_PL_*.ogg`.

Wiring (`tools/w5f2_voice_patcher.py`, 5 edições): `HERO_VOICE_MAP` +
`window.unitVoice(u, kind, opts)` com **gate por unidade** (1 voz/1,7 s
padrão; bots 45% mais esparsos; `min:0` para KO/awake, `min:4200` para
cast), volume pelo `playAt` falloff existente. Momentos: dano leve/pesado
na vítima (`DmgS`/`DmgM`), KO (`DmgL` — gemido de queda), cast
(`AtkS` básico / `AtkM` skills / `AtkL` ult), despertar (`Awake`).
Probe `tools/probe_w5f2.py` **8/8** (oggs 200, voz da vítima posicionada,
gate, defensivo, 0 console errors).

Fora do escopo original das fases 8.2 (o escopo dizia "áudio permanece como
está") — o usuário pediu explicitamente as **vozes originais do APK** no momento
da batalha de cada ninja, **com volume obedecendo à distância** e os **sons
corretos de combate, sem nada genérico**. Entregue em W5:

- 70 cues autênticas de Naruto Ultimate Ninja Storm em
  `public/assets/audio/decoded/` (+22 novas, pipeline em
  `tools/extract_battle_sfx.py` + vgmstream em `tools/audiobanks/`).
- `AUTH_SFX.playAt` posiciona cada som pela distância câmera→fonte
  (falloff suave, silêncio além de ~60u): a luta dos bots atravessando a vila
  toca nos volumes certos, o que acontece perto do jogador é claro.
- Cada momento de batalha tem o som correto do jogo original: impacto, queda
  pesada, soco/chute (com variação), kunai/shuriken, impacto metálico
  (substituindo o som de menu que tocava no impacto de arma), KO, ressurreição,
  fim de awakening, ult pronto, baús do BR; vozes de jutsu por herói no cast.
- ZERO áudio sintetizado em batalha (os bleeps de `SoundFX` saíram de todos os
  caminhos de combate; sobram apenas na UI, onde cues autênticas os cobrem).
- Validação: `tools/probe_w_sfx.py` 13/13 + bateria 47/47 + verify 0 erros.

### 8.4 Regras de execução

1. Docs antes de código: cada fase atualiza PROJECT.md (feature row) + TEST_READY.md + LIFELINE.md.
2. window.start5v5Match/window.units/window.JUICE/contrato DOM preservados; regressão no legado = rollback da task.
3. Patchers re-ancorados (dev paralelo mexe nos mesmos arquivos): .bak_pv* + re-leitura antes de cada patch.
4. Telas 5e2 offline: nunca rodar a suite com outro headless Edge concorrente (regra de CPU).

