# NUBA — Menu Inicial + Draft MOBA Mobile (W-MENU) Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Transformar o fluxo "lobby → partida" do NUBA num loop de jogo mobile completo: tela-título com identidade, home com modos e progressão, e um draft pré-partida (pick com timer, lock, reveal dos times) no padrão Wild Rift/MLBB.

**Architecture:** Telas são `<div class="screen">` controladas por `showScreen()` (padrão já usado por lobby/hud/results). O draft é uma nova screen com uma **draft state machine** (`DRAFT.phase: idle → pick → lock → reveal → done`) que monta os times (player + aliados bots + inimigos) e hand-off pro `startMatch(configId, draftResult)` existente — sem reescrever matchmaking.

**Tech Stack:** Vanilla JS/HTML/CSS já do projeto (tema Storm: Poppins + laranja `#f97316`, ícones `assets/ui/`), three.js já no pedestal (reusar o palco 3D no draft), suite E2E CDP existente (`tools/test_e2e_suite.py`).

---

## 1. Diagnóstico — estágio atual como game design (2026-10-24)

**O jogo É hoje:** arena 3D autêntica de altíssimo nível (modelos/coreografias/VFX/vozes do APK Storm, hitstop, câmera cinematográfica, 12 heróis jogáveis completos, 4 modos: 3v3, 5v5, BR vila, Treino). É um **esqueleto de jogo excelente com casca de "ferramenta de teste"**: você abre o index e CAI direto no lobby.

**Forças (manter):**
- Lobby com abas (play/ninjas/arenas/perfil/ajustes) e estética shadcn já refinada (W7)
- Pedestal 3D do herói girável 360° (asset raro — nenhum MOBA mobile tem isso no draft)
- Roster-grid com ficha Databook (stats em barras, kit, altura, dificuldade)
- HUD de partida completo + tela de resultados com revanche

**Lacunas (o que falta pra "jogo"):**
1. **Sem tela-título** — não existe "chegar no jogo" (press start, logo, versão, auto-login de perfil)
2. **Sem ritual de partida** — pick é um clique lateral instantâneo; times são auto-preview (`updateLobbyTeamsPreview` enche slots com os 4 primeiros do roster); não há decisão, tensão, nem posse ("eu escolhi")
3. **Sem progressão/meta** — não há XP, moeda, missão diária, nada que faça voltar amanhã
4. **Draft sem composição** — os bots aliados/rivais não "escolhem": sem reveal, sem surpresa

## 2. Matriz comparativa — referências × NUBA atual × proposta

| Dimensão | Wild Rift | MLBB | HoK/Unite | NUBA hoje | **Proposta NUBA** |
|---|---|---|---|---|---|
| Primeira tela | Login → Home c/ card de modo | Home c/ botão Rank gigante | Home (HoK: popups = anti-pattern) | Lobby direto (tab play) | **Tela-título → Home** (1 popup máx: "novo: draft") |
| Pick flow | Draft pick, sem bans (pool pequena), role pref antes | Blind pick rápido (ranks baixos), draft em altos | Grid pick rápido | Clique instantâneo na sidebar | **Draft 3 fases**: pick(20s) → lock → reveal |
| Grade de heróis | Grid por rota | Grid por role | Grid | Roster-grid 12 ✓ já bom | **Board único 12 cards** (DOTA2 pattern) + filtro por rota |
| Timer de pick | Grande, topo, tick < 5s | Grande | Grande | ✗ nenhum | **Timer 20s topo centro**, tick sonoro < 5s |
| Lock in | Botão óbvio grande | Auto no fim do timer | Auto | ✗ | **Botão "SELAR SELEÇÃO 選定"** + auto no timer |
| Reveal dos times | Cards flip com splash art | Splash + VS | VS rápido | ✗ (preview estático) | **Reveal 2,5s: cards flipam + badge VS + SFX oogi** |
| Bots no draft | — (PvP) | — | — | times pré-montados estáticos | **Bots "pensam"**: picks com delay 0,4–1,2s, sem repetir herói |
| Menu clutter | Limpo | Limpo | **Poluído (anti)** | Limpo ✓ | Manter limpo |

**Decisões de design derivadas das fontes:** pool de 12 → **sem bans** (Wild Rift fez igual com pool pequena); **velocidade > estratégia** (MLBB: filas rápidas; nosso público é casual); lock e pick order sempre visíveis (crítica ao redesign do champ select do LoL: dead space/diagonais; timer em destaque).

## 3. Design — TELA-TÍTULO (`#title-screen`)

```
┌────────────────────────────────────────────────┐
│              (fundo: arena 3D com blur         │
│               + partículas de chakra laranja)  │
│                                                │
│                  鈴 N U B A 鈴                 │
│         NINJA ULTIMATE BATTLE ARENA            │
│         ─ shinobi mobile MOBA ─                │
│                                                │
│            ┌──────────────────┐                │
│            │   忍 TOCAR PARA   │                │
│            │   INICIAR 開始    │  (pulsa 1Hz)  │
│            └──────────────────┘                │
│                                                │
│   v0.9.0-menu    • perfil convidado • PT-BR    │
└────────────────────────────────────────────┘
```
- Qualquer clique/touch/Enter → `showScreen('lobby')` + `MUSIC.play('menu')` (loop menu já existe no W6? senão `bgm menu01`) + logo SFX
- Partículas: reusar `1efc_chakra05` do skill_vfx.json em canvas 2D leve (20 sprites, 60fps)
- Reaparece só no reload (não volta do lobby — lobby tem o "menu" completo)

## 4. Design — DRAFT (`#draft-screen`), o coração do plano

Layout mobile-first (mesma grid 3 colunas do lobby, adaptada):

```
┌───────────────┬──────────────────────┬───────────────┐
│ SEU TIME      │   ⏱ 00:17  (timer)   │ RIVAIS        │
│ ┌─┐┌─┐┌─┐    │  ┌────────────────┐  │ ┌─┐┌─┐┌─┐    │
│ │N││S││S│     │  │ PEDESTAL 3D    │  │ │?││?││?│    │
│ └─┘└─┘└─┘     │  │ herói hover    │  │ └─┘└─┘└─┘    │
│ (aliados      │  │ girável 360°   │  │ (interroga-  │
│  flipam ao    │  └────────────────┘  │  dos até o   │
│  "pensar")    │   nome + role + kit  │  reveal)     │
│               │                      │               │
│ ══════════════╡ 12 CARDS (board)     │               │
│               │ [N][S][K][K][R][I]…  │               │
│ [SELAR 選定]  │ [G][H][N][J][T][O]   │               │
│  (verde)      │ (filter: TODOS/role) │               │
└───────────────┴──────────────────────┴───────────────┘
```

**Fases da draft state machine (`DRAFT` global):**
1. **`pick` (20s)**: board de 12 cards (portraits `assets/portraits/*.png`); hover/preview atualiza o pedestal 3D (o herói em pessoa!) + ficha; aliados bots "pensam" (delay aleatório 0,4–1,2s cada) e flipam o card no slot azul; **rival nunca visível** (cards `?` vermelhos). Filtro por rota (Lutador/Assassino/Tanque/Suporte — campo `role` do rosterMeta).
2. **`lock`**: player clica SELAR (ou timer zera → auto-lock do hover/último selecionado). Timer < 5s: tick SFX + timer vermelho pulsando.
3. **`reveal` (2,5s)**: inimigos vermelhos flipam um a um (0,3s entre cada) com SFX `sword_hit`; badge VS cresce; fim → SFX `oogi` + blackout 400ms → `startMatch`.
4. **`done`**: screens transitam; `DRAFT.teams = { blue: [heroIds], red: [heroIds] }` passado ao `startMatch`.

**Regras de composição (fiel ao jogo atual):** 3v3 → 3 slots/time; 5v5 → 5; `br_vila` → 10 solo (player + 9 bots, sem times no draft — pula pro reveal direto); `training` → sem draft (mantém fluxo direto). Bots nunca repetem herói entre os dois times (12 heróis ≤ 10 slots — sempre dá). Hand-off: `startMatch(configId, { blue, red })` — o spawn atual usa `updateLobbyTeamsPreview`; estender pra aceitar a lista explícita (default = comportamento atual, compat com 47 testes E2E).

## 5. Tasks (bite-sized, TDD via suite CDP)

### Task 1: Tela-título estática
**Files:** Modify `public/index.html` (inserir `#title-screen` antes de `#lobby-screen`, `class="screen active"` vai pro título e lobby perde `active`), `public/styles.css` (bloco `#title-screen`), `public/game.js` (`window.__bootScreen = 'title'` + listener 1 clique → `showScreen('lobby')`).
**Steps:** 1) HTML/CSS/JS; 2) `node --check`; 3) probe CDP: abrir página → `document.querySelector('#title-screen').classList.contains('active')` === true → click → lobby `active` ✓.
**Verificação:** `python tools/probe_title.py` → PASS.

### Task 2: HTML/CSS do draft-screen
**Files:** Modify `public/index.html` (`#draft-screen.screen` com colunas time-esquerda/pedestal-centro/board+time-direita/botão SELAR), `public/styles.css` (grid, cards `?` vermelhos, timer anim `@keyframes pulse-red`).
**Verificação:** `node --check` + suite existente 47/47 segue verde (draft invisível por padrão).

### Task 3: Draft state machine (pick → lock)
**Files:** Modify `public/game.js`: `const DRAFT = { phase: 'idle', timer: 20, sel: '1nrt', blue: [], red: [] }`; `openDraft(modeId)` (monta slots por teamSize, inicia timer no rAF loop existente); `draftPick(heroId)` (preview pedestal via `selectHero` já existente L1259); `draftLock()` (fixa player, agenda picks dos bots); botão SELAR wire; auto-lock no timer 0.
**Steps:** cada sub-passo testável via CDP: `window.DRAFT.phase`, `window.__draftTimer()`.

### Task 4: Bots pensam + reveal
**Files:** Modify `public/game.js`: `draftBotThink()` (setTimeouts 0,4–1,2s, flip visual do slot); `draftReveal()` (flip vermelhos 1-a-1, badge VS, blackout, chama `startMatch`).
**Verificação:** probe: `openDraft('dm_3v3')` → fast-forward → `DRAFT.blue.length === 3`, `DRAFT.red.length === 3`, sem repetidos, `matchActive === true`.

### Task 5: Hand-off no startMatch + wire do lobby
**Files:** Modify `public/game.js:2242` (`startMatch(configId, draft)` — se `draft.blue/red`, usar essas listas no spawn dos units em vez do preview; senão comportamento atual), lobby `btn-start-match` → `openDraft(selectedModeId)` (training pula draft).
**Verificação:** `python tools/test_e2e_suite.py` → 47/47 (compat: chamadas sem draft idênticas).

### Task 6: Testes E2E novos (S06 draft, S07 título)
**Files:** Modify `tools/test_e2e_suite.py`: `test_s06_draft_flow` (abre draft 3v3, lock, espera reveal+spawn, asserts: player hero = pick, bots distintos, 6 units), `test_s07_title_to_match` (title → lobby → draft → partida).
**Verificação:** suite → 49/49.

### Task 7: SFX/voice do draft + polimento
**Files:** Modify `public/game.js` (tick <5s `AUTH_SFX.pick('kunai_swing')`, flip `sword_hit`, reveal `oogi`, lock `chakura_use`), `public/styles.css` (transições flip 3D `rotateY`).
**Verificação:** probe console errors = 0.

### Task 8: Docs, commit, deploy
**Files:** `docs/PLAN_MENU_DRAFT.md` (cópia deste plano), `docs/TEST_READY.md` §27, bump `game.js?v=44`, commit seletivo, push, deploy verify (`?v=44`), Lifeline.

## 6. Riscos / trade-offs

- **Flake de timing E2E**: bots com setTimeout podem atrasar sob carga → asserts com poll-deadline (padrão S04 fix), nunca sleep fixo.
- **Regressão dos 47 testes**: `startMatch(configId)` sem 2º arg mantém signature atual — todos os testes existentes passam intocados.
- **Performance mobile do pedestal no draft**: já renderiza no lobby (mesma cena) — só mudar container; sem custo novo.
- **Escopo**: NÃO incluir bans (pool 12), NÃO incluir meta/XP agora (fase 2 futura), NÃO redesenhar lobby (W7 fresh).

## 7. Fora de escopo (fase 2 — não implementar agora)

Persistência de perfil, XP/moedas/missões diárias, ranked, skins selecionáveis por herói, chat real de squad, matchmaking online — tudo depende do loop base ficar gostoso primeiro.
