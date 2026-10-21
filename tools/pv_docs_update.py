"""PV0+PV1 docs update — PROJECT.md (features/milestones) + TEST_READY.md (secao PV) + PIVOT_MOBILE.md (status).
So executa com a bateria pv1b VERDE (checagem previa no runner).
Run: python pv_docs_update.py   (cwd = repo root)
"""
import os
import re


def rd(p):
    with open(p, 'r', encoding='utf-8') as f:
        return f.read()


def wr(p, s):
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(s)


def sub1(text, old, new, what):
    n = text.count(old)
    assert n == 1, f'{what}: esperava 1 ocorrencia, achei {n}'
    return text.replace(old, new, 1)


# ---- gate: bateria tem que estar verde ----
for log, marker in [('pv1b_verify.log', 'VERIFY EXIT: 0'), ('pv1b_suite.log', 'SUITE EXIT: 0')]:
    with open(log) as f:
        content = f.read()
    assert marker in content, f'BATERIA NAO VERDE ({log} sem "{marker}") — ABORTANDO docs update'

# ================= PROJECT.md =================
prj = rd('PROJECT.md')

FEATURE_ROWS = '''| 39 | PV0 Fundação Mobile: viewport-fit + safe-area + rotate overlay + INPUT state | Meta `viewport-fit=cover`, `touch-action:none` no canvas, `overscroll-behavior:none`, CSS vars de safe-area (`--safe-*`), overlay `#rotate-overlay` "GIRE O DISPOSITIVO" (portrait+touch via `@media (orientation: portrait)`), `window.__DEVICE` (isTouch/isMobile/dpr) + `body.touch`, e `window.INPUT` (moveX/moveZ/aim/fire/chakra) — estado único de input consumido pelo loop (teclado E touch escrevem nele; merge aditivo nos pontos de leitura: movimento clampa teclas+joystick, `mouseDown || INPUT.fire`, `keys... || INPUT.chakra`) | PV0 (Mobile) | docs/PIVOT_MOBILE.md §PV0 |
| 40 | PV1-A Modos de Partida: MATCH_CONFIGS + Combate 3v3 | `MATCH_CONFIGS` (dm_3v3: 3+3, 15 abates, 3:00, respawn 5s, prorrogação 30s · dm_legacy_5v5: comportamento anterior byte-a-byte · br_vila: placeholder PV2) + `startMatch(configId)`; `window.start5v5Match` vira ALIAS legacy (contrato E2E preservado: suite chama o alias e continua vendo 5+5/META 30/5:00); roster/círculo de spawn/tempo/prorrogação/respawn/meta dinâmicos por config; `#mode-picker` no lobby (3v3 DEFAULT por decisão do usuário, CLÁSSICO 5v5, REALEZA NA VILA "em breve"); revanche reusa o modo anterior (`lastMatchConfigId`) | PV1 (Mobile MVP) | docs/PIVOT_MOBILE.md §PV1 |
| 41 | PV1-B Controles Touch: joystick + cluster + auto-aim | `#touch-controls` (aditivo no `#hud-screen`, visível SÓ com `body.touch` + partida via CSS gate): joystick flutuante esquerdo (`#touch-joystick`, spawn-on-touch, raio 56px, dead-zone 0.18, escreve `INPUT.moveX/moveZ`) + cluster direito 6 botões (`tbtn-atk/q/w/e/r/c` com os mesmos ícones de skin dos slots desktop; ATK hold = `INPUT.fire`, skills tap = `executeSkill` com auto-aim `findAimTarget` range 46 + facing lock, chakra hold); `pointer-events:auto` explícito na camada (HUD ancestors usam none pass-through); haptics `navigator.vibrate(12)`; câmera MOBA follow-cam mantida (estilo Brawl); `.ability-key` oculto em body.touch | PV1 (Mobile MVP) | docs/PIVOT_MOBILE.md §PV1 |
'''

anchor = '## Milestones'
assert prj.count(anchor) == 1
prj = prj.replace(anchor, FEATURE_ROWS + '\n' + anchor, 1)

MS_ROWS = '''| PV0 | Mobile Foundation | Viewport/safe-area/touch-action + `__DEVICE`/`body.touch` + `window.INPUT` (merge aditivo: zero mudança desktop) | M9 | DONE |
| PV1 | Mobile MVP: Combate 3v3 + Touch | MATCH_CONFIGS + startMatch(id) + alias legacy + mode picker + joystick/cluster/auto-aim; validação: probe_pv1a (3v3 3+3/META 15/180s + legacy 5+5/META 30/300s) + probe_pv1b (touch: joystick move unidade, ATK hold, Q tap cd, chakra hold) + bateria 38/38 + 0 erros | PV0 | DONE |
'''
anchor2 = '## Interface Contracts'
assert prj.count(anchor2) == 1
prj = prj.replace(anchor2, MS_ROWS + '\n' + anchor2, 1)
wr('PROJECT.md', prj)
print('[ok] PROJECT.md: 3 feature rows (39-41) + milestones PV0/PV1 DONE')

# ================= TEST_READY.md =================
tr = rd('TEST_READY.md')
assert '## PV — Pivot Mobile (PV0+PV1)' not in tr
PV_SECTION = '''

---

## PV — Pivot Mobile (PV0 + PV1) — 2026-10-21

**Escopo**: fundação mobile (input/viewport/device) + Combate 3v3 + controles touch, conforme `docs/PIVOT_MOBILE.md`.

**Baseline pré-PV** (regra do repo: verde antes de editar): verify 0 erros + suite 38/38 (`baseline_verify_pv.log` / `baseline_suite_pv.log`).

**Baterias por fase** (logs no repo):
- PV0: `pv0_verify.log` / `pv0_suite.log` — verify 0 erros + SUITE EXIT: 0.
- PV1-A (configs+3v3+picker): `pv1a_verify.log` / `pv1a_suite.log` — idem.
- PV1-B (touch): `pv1b_verify.log` / `pv1b_suite.log` — idem (3 baterias consecutivas verdes).

**Probes dedicados** (fora da suite, CDP próprio, porta livre):
- `probe_pv1a.py`: dm_3v3 → 6 unidades, retratos 3+3, `META: 15 ABATES`, tempo 180s; `start5v5Match()` (alias legacy) → 10 unidades, 5+5, `META: 30 ABATES`, 300s; `#mode-picker` 3 chips com dm_3v3 default e BR desabilitado; 0 erros de console.
- `probe_pv1b.py`: com `body.touch` + dm_3v3 — gate CSS (`#touch-controls` visível só com touch), joystick sintético via `Input.dispatchTouchEvent` gera `INPUT.moveX/moveZ` (0.75/0.66) e desloca a unidade (+X real), release zera; ATK hold seta/limpa `INPUT.fire` e executa `cds.atk`; tap em Q dispara `executeSkill` (cd.q 0→5.7); chakra hold carrega (79→100); 0 erros de console.
- **Pitfall registrado**: HUD overlays usam `pointer-events:none` (pass-through) e a herança matava a zona do joystick — fix `#touch-controls, #touch-joystick, #touch-cluster, .tbtn { pointer-events: auto; }` (bak `styles.css.bak_pv1b2`). Qualquer nova camada de input DOM dentro do HUD precisa reativar pointer-events explicitamente.
- **Pitfall registrado**: `#match-timer` usa skin-digits PNG — `textContent` só contém ':'; asserts de tempo devem ler `window.__matchState.time`.

**Contratos preservados**: nenhum ID removido/renomeado (só aditivos: `#rotate-overlay`, `#mode-picker`, `#touch-controls/*`, `.tbtn*`); `window.start5v5Match`/`__matchState`/`JUICE`/`units` intactos; teclado/mouse intocados (F08–F17 verdes); timers em dt real; câmera clamp intacto.

**Pendências Tier 5 (PV1.6)**: integrar probes como testes formais da suite (Tier 5 Mobile) + `Emulation.setDeviceMetricsOverride` mobile + testes de drag-aim.
'''
tr = tr.rstrip() + PV_SECTION
wr('TEST_READY.md', tr)
print('[ok] TEST_READY.md: secao PV adicionada')

# ================= docs/PIVOT_MOBILE.md (status das tasks) =================
pv = rd('docs/PIVOT_MOBILE.md')
pv = pv.replace('### Fase PV0 — Fundação Mobile (nada existente quebra)',
                '### Fase PV0 — Fundação Mobile (nada existente quebra) — **STATUS: DONE (2026-10-21, bateria verde)**', 1)
pv = pv.replace('### Fase PV1 — Combate 3v3 mobile MVP',
                '### Fase PV1 — Combate 3v3 mobile MVP — **STATUS: DONE via probes (2026-10-21); PV1.6 Tier 5 formal pendente**', 1)
pv = pv.replace('**Câmera mobile**\n- `cameraMode=\'thirdperson\'` quando `body.touch` auto-select (default do config mobile).',
                '**Câmera mobile** (DECISÃO PV1: simplificada)\n- Câmera MOBA follow-cam mantida no touch (targetX/Z seguem o player com clamp — estilo Brawl Stars); thirdperson segue disponível via botão CAM. Zero mudança de código de câmera no MVP.', 1)
wr('docs/PIVOT_MOBILE.md', pv)
print('[ok] docs/PIVOT_MOBILE.md: status PV0/PV1 + decisao camera registrados')
print('\nDOCS UPDATE DONE')
