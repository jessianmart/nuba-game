
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