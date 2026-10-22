"""Docs PV1.6 + PV2.6 (Tier 5 formal na suite canonica).
Run: python tools/pv1_6_docs_update.py   (cwd = repo root)
"""
PIV = 'docs/PIVOT_MOBILE.md'
PRJ = 'PROJECT.md'
TRD = 'TEST_READY.md'

d = open(PIV, encoding='utf-8', newline='').read()
sep = '\r\n' if '\r\n' in d else '\n'

old1 = '### Fase PV1 — Combate 3v3 mobile MVP — **STATUS: DONE via probes (2026-10-21); PV1.6 Tier 5 formal pendente**'
new1 = '### Fase PV1 — Combate 3v3 mobile MVP — **STATUS: DONE TOTAL (probes 2026-10-21 + PV1.6 Tier 5 FORMAL na suite 2026-10-22: 47/47)**'
assert d.count(old1) == 1, f'ancora PV1: {d.count(old1)}'
d = d.replace(old1, new1, 1)

block = (
    '### Tier 5 E2E — PV1.6 entregue (2026-10-22): touch real na suite canonica' + sep +
    '' + sep +
    '9 testes "Tier 5" em `tools/test_e2e_suite.py` (38 → **47**), touch de verdade via' + sep +
    '`Input.dispatchTouchEvent` (mesma pipeline de um dedo: pointerdown/up com pointerType' + sep +
    'touch) — nao mais so probes ad-hoc:' + sep +
    '' + sep +
    '| Teste | O que prova |' + sep +
    '|---|---|' + sep +
    '| T5_M01 | Emulacao iPhone 844x390 no boot: `__DEVICE.isMobile`, overlay oculto em landscape, governor dprCap 1.25 + vfxCap 24 |' + sep +
    '| T5_M02 | Arena DEFAULT do lobby carrega a **variante `.mobile.json`** (17 meshes) — PV3.2 dentro da suite |' + sep +
    '| T5_M03 | 3v3 mobile: 6 units, 3 retratos/time, META 15, touch-cluster grid, `__matchState.br === null` |' + sep +
    '| T5_M04 | **Joystick real**: touchStart/move/end → vetor `INPUT` + unidade anda +X + reset ao soltar |' + sep +
    '| T5_M05 | **ATK hold**: `INPUT.fire` true/false, `.pressed`, ataque dispara (cd/estado) |' + sep +
    '| T5_M06 | **Tap Q**: `executeSkill` + espelho de CD vivo em `#cdt-q` (conic/segundos) |' + sep +
    '| T5_M07 | **Hold chakra**: `INPUT.chakra` true/false |' + sep +
    '| T5_M08 | **Realeza na Vila mobile** (PV2.6): 10 ninjas, zona 65→6 encolhendo, 12 baus, `sa00z.mobile.json`, HUD BR |' + sep +
    '| T5_M09 | Portrait → overlay "gire o dispositivo"; restaura desktop no fim (UA set + reload) |' + sep +
    '' + sep +
    'Bateria: **47/47 + verify 0 erros** (decima verde). Pitfalls reais da rodada:' + sep +
    'CDP **descarta valores `undefined`** do `returnByValue` (KeyError no Python — `__matchState`' + sep +
    'nao tem `mode`; o discriminador e `br === null`); `startMatch(\'br_vila\')` em MOBILE leva' + sep +
    '**~32s** (desktop 8.6s) e estoura o timeout CDP de 30s com `TimeoutError` de mensagem VAZIA;' + sep +
    '`Emulation.clearUserAgentOverride` **nao propaga no headless** — restaurar via SET desktop.' + sep +
    '' + sep
)
anchor2 = '### Fase PV2 — Realeza na Vila — **STATUS: MODO BR JOGÁVEL (probe 8/8 + bateria 38/38)**'
assert d.count(anchor2) == 1, f'ancora PV2: {d.count(anchor2)}'
d = d.replace(anchor2, block + anchor2, 1)

old2 = '### Fase PV2 — Realeza na Vila — **STATUS: MODO BR JOGÁVEL (probe 8/8 + bateria 38/38)**'
new2 = '### Fase PV2 — Realeza na Vila — **STATUS: MODO BR JOGÁVEL (probe 8/8 + Tier 5 M08 formal na suite 47/47)**'
assert d.count(old2) == 1
d = d.replace(old2, new2, 1)

open(PIV, 'w', encoding='utf-8', newline='').write(d)
print('[ok] PIVOT_MOBILE: PV1 DONE TOTAL + bloco Tier 5 + PV2 status')

F48 = ('| 48 | PV1.6 + PV2.6 — Tier 5 E2E Mobile FORMAL na suite canonica | 9 testes "Tier 5" em `tools/test_e2e_suite.py` (38→**47**, bateria 47/47 + verify 0): '
       'M01 emulacao iPhone no boot (UA override VERIFICADO antes de navegar — o override pode chegar atrasado e bootar com UA antigo; `__DEVICE.isMobile`, overlay oculto, governor dprCap 1.25/vfxCap 24); '
       'M02 arena default `.mobile.json` (PV3.2 in-suite); M03 3v3 mobile (6 units, 3 retratos/time, META 15, cluster grid, `__matchState.br === null`); '
       'M04 joystick REAL via `Input.dispatchTouchEvent` (vetor INPUT + unidade anda + reset); M05 ATK hold (`INPUT.fire`, `.pressed`, ataque dispara); '
       'M06 tap Q + espelho de CD `#cdt-q` (PV4); M07 chakra hold; M08 Realeza na Vila mobile (10 ninjas, zona 65→6, 12 baus, `sa00z.mobile.json`, HUD BR); '
       'M09 portrait → rotate overlay + restaura desktop (SET UA, nao clear — `clearUserAgentOverride` nao propaga no headless). '
       'Pitfalls descobertos com diag: CDP descarta `undefined` em `returnByValue` (KeyError); BR mobile `startMatch` ~32s estoura timeout CDP 30s (`TimeoutError` de mensagem VAZIA) → helper `_t5_eval_slow` 90s '
       '| PV1.6/PV2.6 (E2E formal) | docs/PIVOT_MOBILE.md §Tier 5 |')
p = open(PRJ, encoding='utf-8', newline='').read()
a47 = ' | PV3 (perf) | docs/PIVOT_MOBILE.md §PV3 |'
assert p.count(a47) == 1, f'ancora 47: {p.count(a47)}'
p = p.replace(a47, a47 + '\r\n' + F48, 1)
open(PRJ, 'w', encoding='utf-8', newline='').write(p)
print('[ok] PROJECT.md #48')

t = open(TRD, encoding='utf-8', newline='').read()
t += '''

### Tier 5 E2E — PV1.6/PV2.6 formal (validado 2026-10-22)
- `tools/test_e2e_suite.py` agora cobre **Tiers 1-5 = 47 testes** (23+5+4+6+9), bateria
  47/47 + verify 0 erros (decima verde). Tier 5 = emulacao iPhone 844x390 + toque REAL
  via `Input.dispatchTouchEvent` (pointerdown/up com pointerType touch).
- Fluxo do tier: M01 boot mobile (UA override **verificado antes de navegar** — o
  override pode chegar atrasado ao processo e bootar com o UA antigo; race medida no
  PV3.2) → M02 arena `.mobile.json` → M03 3v3 → M04-M07 touch → M08 BR → M09 portrait
  + **restaura desktop** (a proxima bateria anexa na mesma aba).
- **Pitfalls CDP** (custaram a rodada, todos com diag reproduzivel):
  1. `returnByValue` **descarta valores `undefined`** — ler campo inexistente
     (`__matchState.mode`) vira KeyError no Python. Chaves reais do `__matchState`:
     `time/br/overtime/suddenDeath/blue/red`; discriminador de modo DM = `br === null`.
  2. `startMatch('br_vila')` em MOBILE leva **~32s** (desktop 8.6s) — estoura o timeout
     CDP de 30s e o `TimeoutError` do asyncio tem **mensagem vazia** (FAIL -> branco).
     Helper `_t5_eval_slow(timeout=90)`.
  3. `Emulation.clearUserAgentOverride` **nao propaga no headless** — restaurar via
     `setUserAgentOverride` com UA desktop + `setDeviceMetricsOverride` 1280x720.
  4. Servidor :8080 caindo no meio da bateria deixa a suite booting numa pagina morta
     ("Failed to start 5v5 match") — conferir `curl :8080` antes de rodar.
- Novos `.bak`: test_e2e_suite.py.bak_pv1_6 / .bak_pv1_6fix.
'''
open(TRD, 'w', encoding='utf-8', newline='').write(t)
print('[ok] TEST_READY: secao Tier 5')
