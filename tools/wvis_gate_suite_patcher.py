# -*- coding: utf-8 -*-
"""W-VIS-GATE-SUITE: mesma classe do fix do verify — o hitstun do W-HS bloqueia
casts forcados dos testes numa partida viva (T3_P01, T4_S03, T4_S04, T4_S05).
Fix: zero hitstun do caster no setup de cada teste afetado (lição §6.14 da skill).
Idempotente, dry-run valida contagem na janela da funcao antes de gravar.
Rollback: tools/test_e2e_suite.py.bak_wvis
"""
import io, shutil, sys

P = 'tools/test_e2e_suite.py'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

FIXES = [
    ('test_p01_wasd_while_casting_jutsu',
     'p.chakra = 100; p.cds.q = 0;',
     'p.hitstun = 0; p.chakra = 100; p.cds.q = 0;'),
    ('test_s03_combat_combo_ability_cycling',
     'p.chakra = 100;\n                p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };',
     'p.hitstun = 0; p.chakra = 100;\n                p.cds = { atk: 0, q: 0, w: 0, e: 0, r: 0 };'),
    ('test_s04_kill_and_respawn_cycle_scenario',
     'enemy.hp = 5;\n                player.cds.atk = 0;',
     'enemy.hp = 5;\n                player.hitstun = 0; player.cds.atk = 0;'),
    ('test_s05_awakening_and_ultimate_clash',
     'p.chakra = 100;\n                p.cds.r = 0;',
     'p.hitstun = 0; p.chakra = 100;\n                p.cds.r = 0;'),
]

if 'p.hitstun = 0;' in src:
    print('W-VIS-GATE-SUITE ja aplicado — nada a fazer'); sys.exit(0)

fails = []
for name, old, new in FIXES:
    i = src.index('def ' + name)
    janela = src[i:i + 2000]
    n = janela.count(old)
    if n != 1:
        fails.append(f'  {name}: count={n} (esperado 1)')
if fails:
    print('DRY-RUN ABORTADO:'); print('\n'.join(fails)); sys.exit(1)
print('dry-run OK: 4 testes ancorados')

out = src
for name, old, new in FIXES:
    i = out.index('def ' + name)
    janela = out[i:i + 2000]
    novo = janela.replace(old, new, 1)
    out = out[:i] + novo + out[i + 2000:]
assert out.count('p.hitstun = 0;') == 3 and out.count('player.hitstun = 0;') == 1

shutil.copyfile(P, P + '.bak_wvis')
data = out.replace('\n', eol).encode('utf-8') if eol == '\r\n' else out.encode('utf-8')
io.open(P, 'wb').write(data)
print('W-VIS-GATE-SUITE APLICADO: T3_P01 + T4_S03/S04/S05 zeram hitstun do caster')
