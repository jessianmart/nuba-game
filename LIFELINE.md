# LIFELINE — lifeline

> An append-only chain of *whys*. The project records *why* it is what it is, and any mind that
> connects inherits that why instantly — with no one re-explaining.
>
> **This file is GENERATED** from the ledger (in `.lifeline/`), which is the source of truth.
> Do NOT hand-edit — append with `lifeline log` and it regenerates.
>
> **Start at #0001.** It's the whole project in human language.

## Protocol

1. **Append-only.** Never edit entries; a correction is a new entry (`kind: correction`) that
   references in `parents` the `id` it corrects — superseding it in the current truth.
2. **One entry per unit of work with meaning.** Not per file, not per tool call. The *why*
   outweighs the *what* (Law #5).
3. **Content-addressed identity (Law #3):** `id = sha256(kind, author, agent, provider, model,
   summary, body, sorted-parents)`. `ts` and `dedup_key` stay OUT of the hash — the same content
   yields the same `id` on any machine. `parents` form the causal DAG; there is no prev_hash (the
   ledger is a graph, not a list).
4. **Integrity:** `lifeline verify` checks that every `id` matches its content.
5. **Append:** `lifeline log --kind … --summary … --body …`. To see the assembled context an AI
   would receive: `lifeline context`.

## Project laws (the constitution)

1. **No memory without an immutable anchor.** Every context item carries the hash of its source
   event. The anti-hallucination spine.
2. **Append-only.** Corrections are new entries referencing the prior id.
3. **Deterministic content-addressing.** Same content + parents → same id, on any node.
4. **Provider-agnostic storage; deliver in the provider's format.**
5. **The *why* outweighs the *what*.**
6. **Budget is first-class.** Context fits the window; truncation is explicit, never silent.
7. **MCP-native.** The AI's interface is the product surface, not an appendix.

**Non-goals (law by omission):** Lifeline is NOT a cognitive OS, NOT an MMU, NOT an agent
orchestrator/sandbox, NOT a workflow engine, does NOT replace git, is NOT an executor/curator
(self-healing) or a trainer (fine-tuning/DL). It records reasoning.

---

## Entries

### #0001 — 2026-10-21T11:42:33.619673+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: NUBA publicado: GitHub + Vercel validados via proxy (38/38, 0 console errors)
- **parents**: —
- **id**: 93a6692ac04e2937adbae4c6e3707da09826e7e43257c6ab0e476ec0e9ccb89e

**Body**:
Meta do usuário: entregar tudo validado e publicar GitHub+Vercel inicialmente. Executado: repo github.com/jessianmart/nuba-game (master, 1858+ arquivos, ~541MB assets, sem files >100MB); deploy https://goofy-mendeleev.vercel.app com .vercelignore enxuto (541MB->~150MB, exclui ui/raw, ui/_sheets, models/puppets, banks de audio brutos). Validação: tools/prod_proxy.py (reverse proxy localhost:8080 -> URL Vercel) permitiu rodar verify_browser_runtime.py + test_e2e_suite.py INALTERADOS contra bytes de produção: 38/38, zero console errors. Bugs de deploy corrigidos pela bateria: (1) public/assets/arena é symlink -> stage/arena e o uploader Vercel não segue symlinks (50 texturas 404) — fix via rewrites /assets/arena/:path* -> /assets/stage/arena/:path*; (2) regra ampla de Cache-Control cacheava 404s na edge — removida; (3) .vercel/build-output stale entre deploys — rm antes de redeploy. W2.1 discovery (Temari 1tmr model+anims+vfx extraídos e validados estruturalmente) permanece em w21_out/ aguardando integração serial. Próximos passos: W1.2 Settings, W1.3 Tutorial, integração Temari, fan-out roster.

<!-- lifeline:end -->

### #0002 — 2026-10-21T13:44:27.356955+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W1.2 Ajustes + incidente revert W1.1: causas e defesas
- **parents**: 93a6692ac04e2937adbae4c6e3707da09826e7e43257c6ab0e476ec0e9ccb89e
- **id**: 35e52a3f92b0c9d3b4545522c9b5c94c79ea2031e7cda7d9745315854a73ae2a

**Body**:
W1.2 Ajustes shipped (5a aba lobby: som/graficos/game feel/controles, persistencia no perfil, smoke 9/9 c/ reload, bateria 38/38 local+prod, commits a8f7fcd..841c1f2, deploy vercel). Incidente W1.1: agentes paralelos reverteram game.js pos-verde pre-commit; defesas adotadas: commit imediato apos verde, marcadores de milestone grepados antes de trabalhar, smokes de feature obrigatorios. Saga readiness W1.2.1-3: flag top-level roda no parse (prova nada); initLobbyNav roda ~L5521 muito apos a funcao de boot (~L1504); sinal correto = apos a ULTIMA chamada que anexa listeners. ':8080 nao e sempre local' - prod_proxy pode estar servindo. Tudo na skill nuba-development 6.7.

<!-- lifeline:end -->

### #0003 — 2026-10-21T16:32:42.375415+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: PV1 touch controls: mobile jogavel end-to-end, prod validada
- **parents**: 35e52a3f92b0c9d3b4545522c9b5c94c79ea2031e7cda7d9745315854a73ae2a
- **id**: cee78cfb5cf02e95ee4352573d680cb9fd0fa939643a5616b24534b5bde4bf8c

**Body**:
PV1 fechado: joystick + cluster .tbtn (auto-aim, vibrate, chakra hold) adotando o DOM abandonado dos agentes paralelos (colisao de IDs resolvida por adocao em vez de duplicacao); gates PV1.4c/1.5a/1.5b; smoke Tier 5 CDP LANDSCAPE 915x412 PASS local+prod; baterias 38/38 desktop e prod zero console errors; commits e3dd1ed+d1c2354, deploy vercel. W2.2: Orochimaru 1orc extraido e validado (107 arquivos, w22_out/). Licoes na skill 6.8: colisao de IDs paralelos, patcher parcial grava, overlay landscape intercepta Tier 5, timing de roster em prod, subagent fora do working dir.

<!-- lifeline:end -->

### #0004 — 2026-10-21T21:47:27.216604+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: Tsunade ja estava integrada no lugar da Temari (W2 dos agentes); W2 smoke corrigido e PASSA
- **parents**: cee78cfb5cf02e95ee4352573d680cb9fd0fa939643a5616b24534b5bde4bf8c
- **id**: 925cf69ca1a82b5a65d5dbab8c7a8516ce22999dbefe56bdf2cdddfc65127475

**Body**:
Usuario pediu Tsunade no lugar da Temari. Descoberta: os agentes PV0-PV1-W2 ja tinham integrado 12 herois em public (modelo 1tnd.json em public/assets/models, roster_meta.json, HERO_STATS/SKILL_VFX_MAP/SKILL_VFX_ANIM com 1tnd+1orc) — Temari (1tmr) so extraida em w21_out, nunca wireada. Subagente de re-extracao da Tsunade abortado (desnecessario). w2_smoke dos agentes falhava so no nome do probe (u.rig vs u.mesh, rig real = unit.mesh L5032) — corrigido, PASSA: kit Rakanken autentico, cast Q, rig 3D userData.heroId=1tnd.

<!-- lifeline:end -->

### #0005 — 2026-10-21T21:56:40.028820+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: PV4 — Touch HUD V2 (HUD mobile)
- **parents**: 925cf69ca1a82b5a65d5dbab8c7a8516ce22999dbefe56bdf2cdddfc65127475
- **id**: 85598630915b8e965477e2b2ae93fcf316e8f9977548fc3364a939c878de1aa1

**Body**:
Pedido do usuario: minimapa no topo, HP e chakra cada um de um lado, base apenas joystick (esq) + skills (dir) com tempo de CD, banners de streak/oulti discretos no padrao do APK. Decisao de arquitetura: ZERO componente novo no DOM — reaproveitar tudo via gates body.touch em CSS (position:fixed + display:contents no footer para reposicionar minimapa e faixa de vitais) e espelhar o CD dos slots desktop (#cd-*, conic + segundos) nos botoes touch (#cdt-*) pelo updater existente, mantendo fonte unica de verdade. Motivo: 'muito css'/poluicao visual — gates + reposicionamento custam ~45 linhas de CSS aditivo sem duplicar logica. Probe_pv4_hud 13/13 (844x390), probe_responsive 5/5 landscapes (568x320 overflow resolvido, scrollW 568/568), BR OK, bateria verify 0 + suite 38/38.

<!-- lifeline:end -->

### #0006 — 2026-10-21T22:58:26.885295+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: PV3.1+PV3.3 — governor mobile, VFX cap, haptics e PWA
- **parents**: 85598630915b8e965477e2b2ae93fcf316e8f9977548fc3364a939c878de1aa1
- **id**: d4c2ff6c89d6e4e1f6c10172053776f93be7131328c72378824f8f6b172c5720

**Body**:
Entrega do pacote de perf/polimento mobile do pivot. DECISAO: o governor (window.__GOV) e avaliado no BOOT a partir de __DEVICE.isMobile (UA/touch) — mobile recebe dpr cap 1.25 e teto de 24 VFX; desktop segue 1.75/ilimitado; applyQuality da pagina de ajustes foi ajustada para NAO furar o cap mobile. O VFX cap roda no loop de update e descarta o efeito MAIS ANTIGO acima do teto (o frescor do impacto importa). EVIDENCIA FORTE: injecao de 40 impactos gerou pico natural de 273 VFX simultaneos — sem cap, um 3v3 mobile real derrubaria o FPS; com cap 24 o array converge em <1s. Haptics: helper com throttle 60ms + gate de perfil (18ms dano recebido, 12ms acerto, [40,60,40] morte) — so em mobile. PWA: manifest.webmanifest (fullscreen/landscape/theme #f97316) + icones 192/512 quadrados gerados do logo.png via Pillow com o fundo real do body (#0b0d12). PITFALLS registrados no TEST_READY: SPAWN GUARD bloqueia injecao de dano perto da base (zerar target.spawnShield em probes) e o governor lido no boot exige setUserAgentOverride ANTES do Page.navigate. Validado probe_pv3_polish (governor 4/4 + pico 273-><=24 + haptics + PWA 9/9) + bateria verify 0 + suite 38/38.

<!-- lifeline:end -->

### #0007 — 2026-10-22T00:03:08.848205+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: Consolidacao do working tree paralelo + gate de sanidade de assets (PV-B.6/B.7)
- **parents**: d4c2ff6c89d6e4e1f6c10172053776f93be7131328c72378824f8f6b172c5720
- **id**: bc013fbbfecd15f84bc2d7ca1bad331c39418a7569468c4937a26eacb2d66e16

**Body**:
PV2 REALEZA NA VILA provado 8/8 (probe dos agentes) e PV3/PV4 ja commitados por eles. Risco detectado: horas de trabalho paralelo SO' no working tree (450+ webp, roster 12, gzip) + skill_vfx.json CORROMPIDO por pipeline paralelo (sobrescrita em vez de merge, 12 NaN, 536KB vs 1.44MB) — o loader fetch().catch(${}) engolia o parse e matava TODOS os VFX sem console error (suite seguia 38/38 verde). Acoes: (1) skill_vfx restaurado do HEAD + backup forense no scratch; (2) gate novo no verify_browser_runtime.py — assert de sanidade window.skillVfxData>=11 / rosterMeta>=12 / animationsData>=12, provado por teste NEGATIVO (corrompido -> EXIT 1 vfxKeys 0) e POSITIVO (EXIT 0); (3) cache-busters v8->v9 nos fetch de dados; (4) commit consolidado d6e0925 (tudo menos .bak_*); (5) dev server reiniciado com gzip (17813->3208 bytes em roster_meta). Gate: verify EXIT 0 + suite Tiers 1-4 PASSED.

<!-- lifeline:end -->

### #0008 — 2026-10-22T00:31:40.386251+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: PV3.2 — arena merge mobile: sd03b e o mapa real de toda partida
- **parents**: bc013fbbfecd15f84bc2d7ca1bad331c39418a7569468c4937a26eacb2d66e16
- **id**: 647fc499bffafa09c70dd87915e98c2dde857b7de76ad71d84566e84ee11c456

**Body**:
ACHADO QUE MUDOU O ALVO: instrumentando o jogo com window.__ARENA_LOADED (asset + meshes carregados) descobri que a partida 3v3 NAO roda no sd00a (a primeira arena do catalogo) e sim no sd03b com 294 meshes / 8.02MB — porque dm_3v3 nao define 'arena' no MATCH_CONFIGS, entao o modo cai no palco DEFAULT que o lobby carrega no boot. Ou seja: o mapa mais pesado do jogo e o que TODA partida usa; o sd00a e apenas uma arena selecionavel. DECISAO: criar pipeline generico tools/arena_blender_optimize.py -- <arenaId> (join por textura + decimate por classe, classe extraida do basename da TEXTURA porque os nomes das meshes embutem o id da arena: sd00aobj008_sub0), ratios calibrados por censo real, e aplicar nas duas arenas. RESULTADO: sd03b 294->17 meshes (-94%), 93k->49.7k tris, 8.02->5.48MB; sd00a 122->33 (-73%), 3.58->2.53MB. Registro no catalogo via mapMobile + bump do fetch de dados ?v=11 (fetch embutido nao e coberto pelo auto-cache-buster do index.html). Validado em 2 processos Edge INDEPENDENTES (rodar as duas sessoes no mesmo processo invertia os numeros por estado compartilhado): mobile 17 meshes/109 draw calls/128k tris vs desktop 294/390/180k = -72% draw calls; bateria 38/38. LICAO GERAL: nunca assuma qual arena/recurso a partida usa — instrumente e leia; performance.getEntriesByType('resource') estoura o buffer de 250 entradas no boot e descarta as entradas antigas (a arena sai da lista).

<!-- lifeline:end -->
