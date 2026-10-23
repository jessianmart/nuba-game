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

### #0009 — 2026-10-22T13:20:08.696769+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: Deploy PV2+PV-B em producao validado (Tiers 1-4 verdes); T5 novo dos agentes 7/9
- **parents**: 647fc499bffafa09c70dd87915e98c2dde857b7de76ad71d84566e84ee11c456
- **id**: fe070072ec2d8fae837d4c71805a37397204c8a8f8e277728123efbdb3e3c371

**Body**:
Deploy 433d8d7 -> goofy-mendeleev.vercel.app (mapMobile sd03b + roster 12 + 450 webp + gzip). Validacao prod: verify EXIT 0 com Assets Sanity {vfxKeys 11, roster 12, anim 12}; suite Tiers 1-4 100% verdes (23/23+5/5+4/4+6/6), 0 console errors. Tier 5 (mobile, +250 linhas adicionadas HOJE pelos agentes, nao-commitado): 7/9 — falhas T5_M03 (le __matchState.mode, handle a frente do snapshot atual) e T5_M09 (clearUserAgentOverride), ambas em teste novo paralelo, nao regressao do deploy. Primeira run da suite prod morreu porque o prod_proxy caiu (lancado sem log; relancado com log — 2a run fluiu ate o fim, proxy vivo, ConnectionReset 10054 benignos). Licao: proxy sempre com redirect de log; suite via proxy depende do proxy vivo — cascata de FAILs vazios = proxy morto, nao bug do jogo. Dev server local restaurado com gzip (PV-B.5).

<!-- lifeline:end -->

### #0010 — 2026-10-22T13:56:32.960213+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: PV1.6+PV2.6 — Tier 5 E2E mobile formal na suite canonica (38->47)
- **parents**: fe070072ec2d8fae837d4c71805a37397204c8a8f8e277728123efbdb3e3c371
- **id**: a7f8e013c60be8a047c2c0e0d7937d5e09b3f05005f3d3b41d7e38e8317b654b

**Body**:
Fechada a pendencia formal do pivot: os testes mobile deixaram de ser so probes ad-hoc e entraram NA SUITE canonica como Tier 5 (9 testes, M01-M09), com toque REAL via Input.dispatchTouchEvent e emulacao iPhone 844x390 verificada ANTES de navegar (o setUserAgentOverride pode chegar atrasado ao processo e bootar com UA antigo — race medida na fase PV3.2; a suporte agora espera navigator.userAgent conter iPhone antes do Page.navigate). Cobertura: boot mobile+governor, arena variante .mobile.json in-suite, 3v3 (6 units/3 retratos/META 15/cluster), joystick real (vetor INPUT + movimento + reset), ATK hold, tap Q + espelho de CD #cdt-q, chakra hold, Realeza na Vila mobile (zona 65->6, 12 baus, sa00z.mobile.json) e rotate overlay + restauracao desktop no fim. Bateria: 47/47 + verify 0 erros (decima verde). Tres armadilhas CDP descobertas com diag reproduzivel e registradas na skill: (1) returnByValue DESCARTA valores undefined — ler __matchState.mode (campo inexistente) vira KeyError no Python; as chaves reais sao time/br/overtime/suddenDeath/blue/red e o discriminador de modo DM e br===null; (2) startMatch br_vila em MOBILE demora ~32s vs 8.6s desktop e estoura o timeout CDP de 30s com TimeoutError de mensagem VAZIA (FAIL sem texto) — helper _t5_eval_slow(90s); (3) Emulation.clearUserAgentOverride NAO propaga no headless — restaurar via setUserAgentOverride desktop + setDeviceMetricsOverride, nunca via clear. Aprendizado geral: FAIL com mensagem vazia em teste async = suspeitar de TimeoutError de send(); e todo campo JS lido via CDP deve ter fallback explicito porque undefined some do JSON.

<!-- lifeline:end -->

### #0011 — 2026-10-22T21:47:22.242811+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W-ORC + W-VIS-ALL: VFX autenticos do APK em todas as skills dos 12 herois
- **parents**: a7f8e013c60be8a047c2c0e0d7937d5e09b3f05005f3d3b41d7e38e8317b654b
- **id**: d131a4dc9830a1f4d69a8fb504724364226819b72c50500594c10a0ec18e781e

**Body**:
Causa raiz do gap: ROSTER do pipeline extract tinha so 10 herois (1tnd/1orc fora) e escala fixa radius*0.022 sobre bbox raw 17-472u. Fix: extrator dedicado 1orceff1 (3 modelos + textura, merge cirurgico allow_nan=False), normalizacao de tamanho no buildExtractedVfxMeshGroup (extent ~ targetScale*250u), multiplicador 0.006, binds de mao em chidori/raikiri/lion/chou_rasengan. Alinhamento 100% analitico (centroid + bbox + facing) — Blender nao foi necessario; probes runtime validam antes de patchear. Commit 2ea4267, suite 47/47 + verify + smoke 10/10, 0 console errors. Deploy verificado: game.js?v=37 + skill_vfx.json 12 chaves live.

<!-- lifeline:end -->

### #0012 — 2026-10-22T22:34:00.296289+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W-SKL: coreografias FK completas por skill executadas a 60fps
- **parents**: d131a4dc9830a1f4d69a8fb504724364226819b72c50500594c10a0ec18e781e
- **id**: 9631e1aefd9f49cc227b058b4ec4f92a4f5bdb32482a4a943910d77deda078db

**Body**:
Causa raiz do 'falta o formato da execucao': clips de skill vinham com concatenacao de segs misturados (cha10+cha11+cuts) truncados em ~32 frames com canais identity congelados, tocados a numFrames/24 (Anm do Storm é 60fps) e percorridos a 56% da janela. Fix: extract_skill_choreo.py — clip LIMPO (Anm unico) e COMPLETO (frames reais) por slot: Q=cha10, W=cha20, R=cha14 ou fallback Anm pesado de corpo (1orc cha24 167f, 1hnt cha21, 1tnd cha24, 1orc cha11 146f c/ camera; 1gar rejeitado — cha24 dele é anim da areia <12 canais, Gaara parado é fiel). game.js: fps-aware duration (clip.fps||24) — zero regressao pros clips de locomocao. 39 clips, animations.json v10. Commit 943611d, bateria verde (verify+47/47+smoke), deploy verificado. Nota: frames congelados nos canais 7-19 eram artefato do bake concatenado, nao do Anm original — os Anm de skill tem 82-105 canais completos.

<!-- lifeline:end -->

### #0013 — 2026-10-23T12:09:48.787527+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W-TRAIL + janelas de ult em velocidade real (W-SKL+)
- **parents**: 9631e1aefd9f49cc227b058b4ec4f92a4f5bdb32482a4a943910d77deda078db
- **id**: d4051c954322bc7a627eeb8f7309464cac3b431af716eeaef2287c44c7bae8ec

**Body**:
Trail chunk do APK é referência de bone (ribbon procedural no engine Storm): ribbon de 14 pts na worldPos da mão, fade+largura decrescente, additive, congela no juice. Mapeado fiel aos chunks: 1hnt W Twin Lion (9+13 roxo), 1orc W Kusanagi (13 prateado). Janela do ult agora casada ao clip real: clamp(60fps-frames, 1.15, 1.8) — 1skr/1roc/1orc 2.4-2.8s agora 1.8s (~1.4x em vez de 2.4x); 1nrt/1kks/1nej/1jry mantêm 1.15. Câmera cinematográfica descartada de propósito: cutscene quebraria o fluxo MOBA (cuts do Storm são de single-player). Commit 02a2702, bateria verde, deploy verificado.

<!-- lifeline:end -->

### #0014 — 2026-10-23T12:54:19.537061+00:00 — decision

- **author**: unknown
- **agent**: human
- **provider**: none
- **model**: human
- **kind**: decision
- **summary**: W-CINE: cut cinematico do ult + fix anti-race T4_S04
- **parents**: d4051c954322bc7a627eeb8f7309464cac3b431af716eeaef2287c44c7bae8ec
- **id**: 15c25097a7fa1c9fb01158fa0b9338082eb79069bfa409f0944910be1104fd29

**Body**:
Camera chunk do APK é stub de 8B (keyframes em pacotes de cutscene fora do repo) — cut procedural fiel ao sabor Storm: aproximação baixa atrás do caster, tele punch 6 graus via escritor único de FOV (delta dentro do updateJuice, autorrestaura), blend 0-24%/hold-62%/decai, janela = animDuration do ult, congela no hitstop, player-only com coreografia fps=60 (1ssk/1itc fora, fiel). Probe: camY 38->3.06, fov 48->42, retorno limpo. Suite: T4_S04 flake por cast lock vazando do S03 (rerun 47/47 confirmou) — fix anti-race igual ao S05 (reset animTimer/state/awakenedTimer). Commit 89fe988, deploy verificado.

<!-- lifeline:end -->
