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

### Fase PV0 — Fundação Mobile (nada existente quebra)

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV0.1 | Meta viewport/visualViewport + `touch-action:none` canvas/HUD + `overscroll-behavior:none` + safe-area CSS vars + overlay "gire o dispositivo" | `index.html:5`, `styles.css` (bloco "MOBILE FOUNDATION") | verify 0 erros; suite 38/38 |
| PV0.2 | Detector: `window.__DEVICE` (isTouch, isMobile, dpr) + `body.classList.toggle('touch')` | `game.js` (novo bloco, topo) | unit probe via CDP `typeof __DEVICE` |
| PV0.3 | **`InputState` abstraction**: estado único (§2.4) consumido onde hoje se lê `keys` (L5541+) / `mouseDown`; teclado/pont continuam escrevendo — ZERO mudança de comportamento desktop | `game.js` update loop, input listeners | F08–F17 legado verde (prova: suite) |
| PV0.4 | **Baseline obrigatória** antes da PV1 (regra repo: repo tem dev paralelo) | — | 38/38 + baseline_suite.log renovado |

### Fase PV1 — Combate 3v3 mobile MVP

| # | Task | Arquivos | Verificação |
|---|---|---|---|
| PV1.1 | `MATCH_CONFIGS` + `startMatch(id)` + alias `window.start5v5Match` (legacy) | `game.js:1526` região | legado 5v5: 38/38 intactos |
| PV1.2 | `dm_3v3`: teamSize 3, killTarget 15, time 180, respawn 5; `renderTeamPortraits(3)`; `#score-goal` dinâmico | `game.js` (match start, HUD sync) | novo Tier 5 assert 3 retratos/time + META 15 |
| PV1.3 | `#touch-joystick` (especificação §2.4) escreve `INPUT.moveX/Z` | `index.html` (aditivo), `styles.css`, `game.js` | T5: dispatchTouchEvent drag → unidade move (ler `u.x/u.z` delta) |
| PV1.4 | `#touch-cluster`: botões alvos ≥64px sobre os slots existentes (handlers espelham keydown L5541 → `executeSkill`) + `findAimTarget` + drag-aim indicador | `index.html`, `game.js`, `styles.css` | T5: tap ATK → `__matchState`/unit executou `atk`; auto-aim lock |
| PV1.5 | Câmera mobile: thirdperson auto + look-ahead joystick; pan off touch; clamp invariante | `game.js` §camera | F11 clamp + T5 snap-behind |
| PV1.6 | **Tier 5 E2E Mobile**: CDP `Input.dispatchTouchEvent` (joystick/ATK/Q/kawarimi/chakra) + `Emulation.setDeviceMetricsOverride(412×915)`; updates `PROJECT.md`/`TEST_READY.md` §Tier 5 | `tools/test_e2e_suite.py`, docs | 38/38 + novos testes verdes |

### Fase PV2 — Realeza na Vila (BR)

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

## 6. Open questions (respostas mudam tasks)

1. **3v3 substitui 5v5 como padrão também em desktop?** Recomendo sim (gameplay + custo de manutenção): `dm_3v3` fica default do lobby, `dm_legacy_5v5` vira card "Clássico 5v5" no seletor de modo — é puro config. Se quiser manter 5v5 como principal, tarefa = 1 linha no lobby.
2. **BR com 10 agora ou esperar roster 20 (W2.1)?** Recomendo 10 agora (roster = 10, custo já é budget do 5v5); config sobe para 20 quando W2.1 entregar.
3. **Squad/duo BR?** Recomendo solo puro no MVP (Brawl Showdown solo); duo entra como variação de config em fase futura.
4. **Landscape-only?** Recomendo sim no MVP (T3/Brawl são landscape) — overlay "gire" cobre o portrait.

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
