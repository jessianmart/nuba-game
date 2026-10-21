# -*- coding: utf-8 -*-
"""Docs T5 MATCH PACE: TEST_READY.md §12 + PROJECT.md feature 33. Rodar apos validacao verde."""
import io, sys

def apply(path, patches, append=None):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        if s.count(old) != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {s.count(old)} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {path}: {name}')
    if append:
        s = s.rstrip('\n') + '\n' + append
        print(f'  [OK] {path}: append')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = True

ok &= apply('TEST_READY.md', [], append="""

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

**Verdict: T5 DONE — partida respira nos 5 minutos pedidos, empate tem prorrogação dramática, e o time-to-kill ficou mais longo.**""")

ok &= apply('PROJECT.md', [
    ('feature 33',
     'smoke de race 3/3 cold-starts dentro da janela; cache-bust v30 | Stability | TEST_READY.md §11 |',
     'smoke de race 3/3 cold-starts dentro da janela; cache-bust v30 | Stability | TEST_READY.md §11 |\n'
     '| 33 | T5 Match Pace: TTK longo + prorrogação | `HERO_HP_SCALE` 1.5 + `HERO_DMG_SCALE` 0.9 (TTK ×1.67, identidades P2 intactas); aos 5:00 empatados → prorrogação 60s (timer laranja) → ainda empatado → morte súbita (próximo abate vence, timer vermelho pulsante); antes empate dava vitória silenciosa ao azul; `window.__matchState` para debug | Game Balance | TEST_READY.md §12 |'),
])

print('DOCS T5:', 'OK' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
