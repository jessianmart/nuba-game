
## §15 — Validação de Produção (GitHub + Vercel, 2026-10-20)

**Deploy público**: https://goofy-mendeleev.vercel.app
**Repo**: https://github.com/jessianmart/nuba-game (master)

Método: proxy reverso (`tools/prod_proxy.py`, `localhost:8080 → https://goofy-mendeleev.vercel.app`)
permite rodar a bateria determinística INALTERADA, com todos os bytes vindos do deploy público.

| Verificação | Resultado |
|---|---|
| verify_browser_runtime.py contra produção | ALL PASSED, zero console errors |
| test_e2e_suite.py contra produção | 38/38 Passed, Console Errors: 0 |

### Bugs de deploy achados e corrigidos pela bateria
1. **404 texturas de arena (50 arquivos)**: `public/assets/arena` é SYMLINK para
   `public/assets/stage/arena` localmente — o uploader do Vercel não segue symlinks.
   Fix: rewrite `/assets/arena/:path*` → `/assets/stage/arena/:path*` no vercel.json
   (commit e34ed50). Lição: manifest de runtime = o que o BROWSER pede, não o que o
   grep de código vê; refs vivem também dentro de JSONs de cena.
2. **Cache de 404s**: regra ampla `Cache-Control max-age=3600` em `(.*).(json|png|jpg)`
   aplicava-se também a respostas 404, preservando erros na edge. Regra removida;
   mantida apenas `decoded/*.ogg` immutable (arquivos confirmados presentes).
3. **Build cache stale**: `.vercel/build-output` local reusado entre deploys;
   `rm -rf .vercel/build-output` antes de redeploy crítico.
4. `.vercelignore` enxuta o deploy (541MB → ~150MB): fora `ui/raw`, `ui/_sheets`,
   `models/puppets`, banks de áudio brutos (`.xfbin/.acf/.nus3conf`) — todos com
   zero refs em runtime (auditados em código E JSONs).

## §16 — W1.2 Página de Ajustes (2026-10-21)

**5ª aba do lobby (AJUSTES)**: som (toggle sincronizado com perfil + volume das cues autênticas),
gráficos (pixel ratio low 0.75 / med 1.25 / high 1.75), game feel (master gate `JUICE.enabled`
nas 4 funções juice), controles (keymap real: Q/E/Espaço/R, C, H, TAB). Persistência em
`nuba.profile.v1` (campos aditivos: volume, quality, juice). Zero scroll na página.

| Verificação | Resultado |
|---|---|
| Smoke W1.2 (9 asserts, 2 probes c/ reload) | PASS — persistência restaurada após reload |
| verify_browser_runtime | ALL PASSED, zero console errors |
| test_e2e_suite | 38/38, Console Errors: 0 |

### Incidente W1.1 (2026-10-20 20:52): revert silencioso do working tree
Agentes paralelos (Antigravity) reverteram o game.js pós-W1.1: AUTH_SFX/SKILL_SFX_MAP sumiram
JUNTO com `bak_w11` e `tools/w11_*`; produção ficou sem áudio autêntico (a suite 38/38 não
cobre AUTH_SFX — só o smoke W1.1 cobre). Recuperação: patcher reconstituído do transcript
(session_search) + âncora level-up re-grepada (indent 4 espaços). Reaplicado, smoke 9/9,
bateria 38/38. **Lição: commit imediato após verde; checar marcadores de milestone antes de
qualquer trabalho novo no repo paralelo.**

### Addendum W1.2.1→W1.2.3: o saga da flag de readiness (2026-10-21)
O smoke W1.2 falhava só em produção. Forense (probe CDP c/ console hook) provou prod saudável:
game.js?v=34 200, zero erros, click funciona pós-boot (~11s via proxy). Causa: 3 bugs seguidos
NO SINAL de readiness do smoke — (1) flag top-level roda no parse, prova nada; (2) flag no fim
da função de boot (~L1504) ainda é cedo — `initLobbyNav()` só roda em ~L5521; (3) um "smoke
local" rodou contra o proxy de produção (:8080) sem ninguém perceber. Fix final: `__ajustesReady`
setado logo APÓS `initLobbyNav();` — smoke 9/9 local E prod. Lição documentada na skill §6.7.

## §17 — PV1 Touch Controls: mobile jogável end-to-end (2026-10-21)

Controles touch completos (docs/PIVOT_MOBILE.md PV1.3/PV1.4/PV1.5), retomando o trabalho
parado dos agentes paralelos: joystick flutuante (44vw×52vh, r56, dead-zone .18 → INPUT.moveX/Z),
cluster .tbtn com ícones do skin (ATK hold → INPUT.fire, Q/W/R com auto-aim via findAimTarget
+ rotação do mesh, kawarimi, chakra hold → INPUT.chakra consumido no charging), vibrate(12),
.pressed, câmera thirdperson auto em touch (PV1.5a), pan de câmera off em touch (PV1.5b),
gate de touch fantasma no pointerdown global (PV1.4c — touch nunca simula mouseDown).

| Verificação | Resultado |
|---|---|
| Smoke PV1 Tier 5 (CDP touch 915×412 landscape, 8 grupos de asserts) | PASS — player ANDA via joystick, Q gasta chakra + cooldown |
| verify + suite desktop | (ver bateria abaixo) |

**Lições duras desta integração**: (1) os agentes paralelos deixaram DOM/CSS touch órfãos
( #touch-controls com .tbtn) que COLIDIAM de ID com meu bloco (#touch-joystick/#touch-cluster) —
meu JS wireou no DOM deles (estrutura filha diferente) e abortou; auditoria de colisão de IDs
antes de inserir DOM paralelo. (2) overlay "gire o dispositivo" (@media portrait + body.touch)
intercepta TODOS os toques em portrait — emular LANDSCAPE (915×412) no Tier 5; probe forense
com event-log global (tgt=rotate-overlay) encontrou em 1 rodada. (3) meu initTouchControls
duplicado foi REMOVIDO (a IIFE L~5911 deles é superior — auto-aim com rotação + vibrate);
window.__cameraMode preservado como leitura E2E.

## §18 — PV2 provado + PV-B (perf) e gate de sanidade de assets (2026-10-21)

Consolidacao do trabalho paralelo (commit d6e0925) + blindagens novas.

| Verificacao | Resultado |
|---|---|
| probe PV2 REALEZA NA VILA (`tools/probe_pv2.py`, 8 grupos) | PASS — 10 solo spawns no layout real (arena sa00z), zona 65->6 em 6 fases, dano fora da zona, bau +35 HP, last-standing, 0 console errors |
| verify_browser_runtime (isolado, apos PV-B.6/B.7) | EXIT 0 — zero console errors; Assets Sanity `{vfxKeys: 11, rosterLen: 12, animKeys: 12}` |
| test_e2e_suite Tiers 1-4 | PASSED, zero console errors |
| W2 smoke (`tools/w2_smoke.py`) | PASS — roster 12 herois, Tsunade 1tnd (Rakanken) + Orochimaru 1orc (Sen'nejashu), rig `userData` confirmado |
| boot payload (`perf_reports/`) | 26.44 MB baseline -> 4.43 MB com gzip (alvo do contrato PV-B: < 14 MB) |
| gzip no dev server (curl) | `Content-Encoding: gzip` + `Vary: Accept-Encoding` (roster_meta 17813 -> 3208 bytes) |

### Incidente: skill_vfx.json corrompido por pipeline paralelo (silencioso)

`assets/skills/skill_vfx.json` foi REGRAVADO (nao mergeado) por um pipeline paralelo com
apenas o heroi novo (1.44 MB/43 modelos -> 536 KB/7) e 12 `NaN` nos normals (`json.dump`
padrao). O loader `fetch(...).then(r => r.json()).catch(() => ({}))` engoliu o parse
invalido: TODOS os VFX extraidos morreram e a bateria 38/38 continuou VERDE com 0 console
errors (mesmo padrao do revert W1.1). Restaurado do HEAD; backup forense no scratch
(`skill_vfx_1tnd_broken_backup.json`).

### Blindagem nova (PV-B.6 / PV-B.7)

- `verify_browser_runtime.py` agora asserta SANIDADE DE ASSETS carregados
  (`window.skillVfxData`/`rosterMeta`/`animationsData` >= 11/12/12), com log
  `Assets Sanity Result`. Provado por teste NEGATIVO: injetar o arquivo corrompido
  -> EXIT 1 com `{"vfxKeys": 0, ...}`; restaurar -> EXIT 0.
- Cache-buster dos fetch de DADOS bumpado v8->v9 (roster_meta/animations/skill_vfx
  mudaram mantendo `?v=8` = cache envenenado no browser; o auto-bump cobre so o index.html).

**Nota de flake**: verify com EXIT 1 por 4x `net::ERR_INSUFFICIENT_RESOURCES` (audio .ogg)
com a suite/probes concorrentes — re-run ISOLADO deu EXIT 0. Bateria roda sozinha.


## 19. W-HS hitstun do APK + W-VIS VFX de mão + fix verify EXIT 1 (2026-10-22)

### W-HS — engine de hitstun decodificado do APK e aplicado

Forense do `data_spc_1nrtprm.bin.xfbin` (`parse_nucc_chunks`: mot/skl/etc/spl) +
frame data real via `parse_full_anm` no bod1c (7 heróis): **FACE_DAMAGE_NORMAL
(dmg0f) = hitstun 11–31f (média 21f = 0.35s)**; hsta0 = 36f = 0.60s (pesado,
dano>=180); dow 16–31f; get00 51f; rxn0 11f. FPS = 60. Engine do Storm: levar hit
PRENDE a vítima na anim de reação; hit novo REINICIA o timer (juggle);
**kawarimi é a única saída** (custa chakra). Movimento livre — kiting é core MOBA.

Aplicado via `tools/whs_hitstun_patcher.py` (5 pontos idempotentes): `dealDamage`
aplica 0.35s/0.60s conforme dano; guard em `executeSkill` bloqueia cast no hitstun
EXCETO kawarimi; telemetria `window.__HITSTUN`; decaimento em dt de parede;
spawns com `hitstun: 0`. Smoke `tools/whs_hitstun_smoke.py` **10/10 PASS**
(juggle, kawarimi livre, hit letal mata, monotonia em dt real, 0 console errors).

### W-VIS — VFX autêntico do APK visível na mão durante o cast

Probe provou: rig FK anima (boneHash muda frame a frame), `state='jutsu'` segura
o clip 0.75s, mas os VFX extraídos morriam em ~0.5s LONGE do corpo e o
procedural era sliver de 104×8 px (câmera MOBA ~50u vs modelos 207×253u raw).
`tools/wvis_patcher.py`: Q 1nrt binda o modelo `rasengan` extraído no bone 13
(mão direita) por todo o cast (escala 0.0105); R 1nrt binda `giant_rasengan`
(escala 0.019, 1.25s); `duration * 1.7` no path extracted; telemetria
`window.__HAND_VFX`. A/B pós-patch (jogo vivo): câmera segue o dash em lerp,
mão world anatômica (1.3u do corpo), handVfx=2, pixels ciano-brilhante
**Q 29→616 / R 545→2425**. Lição de flake: o PRIMEIRO browser-run pós-write em
game.js novo congela (Defender escaneia) — a "câmera morta na origem" do
primeiro forense era isso; runs aquecidos fluem normais.

### Fix verify EXIT 1 (2 sessões de mistério)

Causa raiz: o hitstun NOVO bloqueava os casts sequenciais do verify numa
partida viva (bots acertam o player entre casts → `w_state: 'idle'` stale →
compositor silencioso EXIT 1; o print "ZERO CONSOLE ERRORS" do banner confundiu
o diagnóstico). Fix em `verify_browser_runtime.py` (backup `.bak_wvis`):
setup de cast zera `hitstun` do caster (player q/w/e/r + loop de bots) e o
compositor virou dict `_checks` que imprime `VERIFY FAILURE DETAIL` com o que
falhou — a classe de falha silenciosa morre aqui. Verify: **EXIT 0**,
Assets Sanity 11/12/12, zero console errors.

## 20. W-ORC + W-VIS-ALL — VFX do APK em TODAS as skills dos 12 heróis (2026-10-22)

### Estado prévio

`SKILL_VFX_MAP` (12 heróis × 4 slots) + `activeSkillVfxModel` já existiam (M7):
toda skill tenta spawnar o modelo extraído via `spawnVFX`. Furos: `skill_vfx_data['1orc']`
NÃO existia (ROSTER do pipeline tinha só 10 — Tsunade/Orochimaru fora), o nome no MAP
(`1orc_1orceff1_01`) não bateria com o nome de chunk, e a escala fixa
`radius * 0.022` com bbox raw de 17–472u deixava um efeito gigante e outro invisível.

### W-ORC — extração autêntica de Orochimaru

`tools/extract_orc_vfx.py`: decodifica `data_spc_1orceff1.xfbin` direto do repo
(sem abrir APK): textura `1orc_1orceff1_01.png` (256×256) + 3 modelos
(`1orceff1_01` 68v plano no chão — Sen'nejashu; `_02` 74v blob; `_03` 8v).
MERGE cirúrgico no `skill_vfx.json` (11 → 12 heróis + common), `allow_nan=False`,
sem regressão. MAP fix: `q: '1orceff1_01'` (nome de chunk limpo).
Tsunade: `eff1` dela é VAZIO (422B, 5 chunks sem modelos) — skills dela apontam
commons autênticos (chakra04/log01/nor_dst01) que resolvem via lookup common ✓.

### W-VIS-ALL — calibração global

1. `buildExtractedVfxMeshGroup` agora NORMALIZA o tamanho aparente: computa a
   bbox do grupo no build e ajusta a escala para extent final ≈ `targetScale × 250u`
   (chakra médio). Uma correção → as 48 skills ficam proporcionais.
2. `spawnVFX` extraído: multiplicador `0.022 → 0.006` (extent ≈ radius × 1.5u).
3. Binds de mão (padrão W-VIS) nas skills icônicas: 1ssk Q `chidori_spark` (bone 9),
   1kks Q `raikiri_spark` (13), 1hnt W `lion_chakra` (9+13), 1jry R `chou_rasengan` (13).
4. `skill_vfx.json?v=10`, `game.js?v=37`.

### Probes (jogo vivo, 0 console errors)

`tools/wvis_all_probe.py` (bots, 10 heróis) + `tools/wvis_player_probe.py`
(seleção de lobby → player, 1tnd/1orc): 12/12 heróis castando Q/W/R com grupos
extraídos spawnando (extents world 2.5–8u; Sen'nejashu 16×23u de chão — área
grande temática), `__HAND_VFX` nos binds (chidori hand=2, raikiri hand=2,
lion fists hand=4, chou hand=1). Frame do kaiten: +4.297 px ciano / +4.3k brilho
vs baseline das outras shots. `node --check` OK.

## 21. W-SKL — coreografias FK completas das skills (2026-10-22)

### Diagnóstico

Os clips `jutsu`/`jutsu2`/`ult` vinham do pipeline com **concatenação de segs
misturados** (`cha10`+`cha11`+cuts) e truncagem — resultado: 32 frames com
canais congelados em identidade (frames 12–19 dos bones 7–19), tocados a
`numFrames/24` (FPS errado; os Anm do Storm são 60fps) e percorridos a ~56%
da janela de cast. A execução aparecia como "um pedaço de pose + freeze".

### W-SKL — execução autêntica por skill

`tools/extract_skill_choreo.py`: por herói, **clip limpo** (um único Anm, sem
concatenação) e **completo** (frames reais, sem truncagem):

| slot | Anm | conteúdo |
|---|---|---|
| `jutsu` (Q) | `{cid}cha10` (skl1) | coreografia da skill 1 |
| `jutsu2` (W) | `{cid}cha20` (skl2) | coreografia da skill 2 |
| `ult` (R) | `{cid}cha14` ou fallback pesado | ult cinematográfico |

Fallbacks de ult (Anm mais pesado dos skl, ≥100KB, coreografia de corpo):
1roc→cha24 (167f/2,78s), 1gar→cha24 (REJEITADO — <12 canais de corpo: é anim
da areia/câmera, Gaara fica parado no ult mesmo), 1hnt→cha21 (101f/1,68s),
1tnd→cha24 (81f/1,35s), 1orc→cha11 (146f/2,43s, com Camera chunk).
1ssk/1itc: sem candidato claro — mantêm clip anterior.

Bind pose (Clump/Coords/parents) do `{cid}bod1.xfbin` no data.awb do APK;
Anm dos `data_spc_{cid}skl{1,2}.xfbin` do repo (cada xfbin com sci/smaps
próprios). 39 clips re-bakeados com `fps: 60` no JSON.

### Patches de runtime

- `game.js` L708: `numFrames / 24` → `numFrames / (clip.fps || 24)` — clips
  antigos (idle/run/attack, sem fps) continuam a 24fps: zero regressão;
  clips de skill a 60fps reais.
- `animations.json?v=10`, `game.js?v=38`.

### Probe (`tools/wskl_probe.py`)

Player 1nrt casta Q/W/R; troca pra 1orc via lobby, casta W (119f/2s) e R.
Amostra de quats dos braços (bones 13/9) em 3 instantes do animTimer:
**anima=SIM nos 5 casts**, 0 console errors. (Nos ults a 2ª amostra tardia
congela legitimamente: o dash de impacto muda o state.)

## 22. W-TRAIL + janelas de ult calibradas (2026-10-22)

### W-SKL+ TRAIL — rastros autênticos de mão/lâmina

O `nuccChunkTrail` dos `skl2` do APK é REFERÊNCIA (cmap -> bone animado):
o ribbon é procedural no engine Storm, e o APK só marca qual bone rastreia.
Implementação fiel: ribbon procedural bound ao bone, buffer de 14 pontos da
worldPos da mão, trianglestripe com largura decrescente e fade por idade,
additive + depthWrite false — congela com o mundo no juice (simDt).

| skill | bones | cor | fonte |
|---|---|---|---|
| 1hnt W (Twin Lion) | 9 + 13 (ambas as mãos) | 0x8b5cf6 roxo-leão | Trail chunk 1hntskl2 cha20 |
| 1orc W (Kusanagi dash) | 13 (mão direita) | 0xc7d2fe prateado | Trail chunk 1orcskl2 cha20 |

Auto-cleanup por idade (age >= dur -> remove/dispose).

### W-SKL+ janelas de ult — velocidade real por clip

O ponto único de ult (`unit.state = 'ult'`, L4563) agora casa a janela ao clip:
`clamp(clip.numFrames / clip.fps, 1.15, 1.8)`. Efeito: ults curtos (1nrt 1.05s,
1kks 0.93s, 1nej 1.1s, 1jry) mantêm 1.15s; médios (1hnt 1.68s, 1tnd 1.35s)
tocam em velocidade real; longos (1skr 2.52s, 1roc 2.78s, 1orc 2.43s) sobem
1.15 -> 1.8s (~1.4x em vez de ~2.4x). game.js?v=39.

### Probe (`tools/wtrail_probe.py`)

1nrt r: animDuration = 1.15 (clamp baixo) ✓. 1orc W: ribbon vivo na cena com
588 vértices não-nulos; frame com 87px prateados do Kusanagi + ciano do VFX no
centro ✓. 1orc r: animDuration = 1.8 (clamp alto) ✓. 0 console errors.

## 23. W-CINE — cut cinematográfico do ult (2026-10-22)

O `nuccChunkCamera` dos skl é **stub de 8 bytes** (referência — os keyframes
reais vivem nos pacotes de cutscene, fora do repo). O cut reproduz o sabor
Storm proceduralmente: aproximação baixa atrás do caster durante o windup,
tele punch, retorno suave.

- **Só player com coreografia autêntica** (clip `ult` com `fps=60` — 10/12;
  1ssk/1itc sem ult coreografado ficam sem cut, fiel ao APK).
- Escritor único de FOV: o delta entra no próprio `updateJuice`
  (`48 - fovPunch - ultCineBlend()*6`) — sem conflito com o juice punch;
  autorrestaura quando o blend → 0.
- Posição/lookAt: blend no `updateCameraAndHUD` pós-shake
  (`lerpVectors` até `cinePos` = atrás do caster, y 2.7; lookAt torso).
- Blend: sobe em 0–24% da janela, hold até 62%, decai suave até 100% —
  janela = `animDuration` do ult (1.15–1.8s), nunca além.
- Avança com `simDt` (congela no hitstop); corta se o state sair de 'ult'.
- `window.__CINE` debug hook. game.js?v=40.

### Probe (`tools/wcine_probe.py`)

1nrt r: camY 38 → 25,65 (descendo) → 3,06 (hold baixo), FOV 48 → 47,16 → 42;
após o ult: active=false, FOV 48, camY voltando ao MOBA. Frame do meio com
câmera baixa e composição de perto (paredes verticais). 0 console errors.

## 24. W-VIS-FULL — validação visual 12 heróis × 4 slots = 48 casts (2026-10-23)

`tools/wvis_full_probe.py` (+ `wvis_fix_probe.py`, `wvis_shot_analyze.py`):
bots de partida 5v5 cobrem 10 heróis; 1tnd/1orc/1nrt via lobby player.
Por cast: kids delta (VFX spawnou), grupos extraídos vivos (Box3), rig
animando (quats bone 13 vs idle), trail verts, `__CINE` no ult do player,
screenshot por slot icônico + todos os R (20 frames).

**Resultado: 48/48 células com VFX 3D extraído + coreografia ativa, 0 console
errors.** Rig: 46/48 com movimento confirmado na amostra de 0,30s — 1nrt w
(Kage Bunshin: o selo de mão é sutil sob 42 VFX de clones) e 1skr r (ult de
151f tem windup estático: braço só move a partir de ~0,5s — confirmado em
amostra tardia rig@0.65=R). Trails: 1hnt w e 1orc w com ribbon de 84 vértices.
Cine: Y nos ults do player (1tnd, 1orc, 1nrt), n nos bots (por design).

Pixels de efeito nos 20 frames: ults 4.5k-10.6k px (1gar Shukaku 10.596;
1nej kaiten azul/ciano; 1tnd 3.647 ciano), icônicos 1ssk q Chidori 4.743,
trails 1hnt w 6.436 / 1orc w 4.661.