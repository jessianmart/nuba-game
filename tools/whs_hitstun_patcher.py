# -*- coding: utf-8 -*-
"""HITSTUN do APK Storm -> NUBA (W-HS).
Engine decodificado do APK (tools/hitstun_measure.py): levar hit prende a
vitima na reacao (dmg0f FACE_DAMAGE_NORMAL, media real 21f = 0.35s; hit
pesado = hsta0 36f = 0.60s); hit novo REINICIA (juggle); kawarimi e a unica
saida (custa chakra). Aplicacao:
  1) dealDamage: alvo VIVO recebe u.hitstun = 0.35 (normal) / 0.60 (dano>=180)
  2) executeSkill: hitstun bloqueia casts (kawarimi/liberado — slot e, type
     'kawarimi', fiel ao Storm)
  3) tick: decaimento em dt REAL (tempo de parede, como cds/spawnShield)
  4) spawn: hitstun: 0 no objeto novo (2+ spawns, replace_all)
  5) telemetria window.__HITSTUN para E2E
Patcher idempotente (aborta se ja aplicado). Rollback: *.bak_whs
"""
import io, shutil, sys

P = 'public/game.js'
raw = io.open(P, 'rb').read()
eol = '\r\n' if b'\r\n' in raw else '\n'
src = raw.decode('utf-8').replace('\r\n', '\n')

ANCHORS = [
    # (nome, ancora, insercao, pos)  pos: 'after' insere depois da ancora
    ('dealDamage-hitstun',
     "  target.x = clampPush(target.x + (dx / len) * 1.4);\n"
     "  target.z = clampPush(target.z + (dz / len) * 1.4);\n",
     "\n"
     "  // APK HITSTUN (engine de dano do Storm, medido do APK: dmg0f FACE_DAMAGE_NORMAL\n"
     "  // 21f = 0.35s hit normal / hsta0 hit-stagger 36f = 0.60s hit pesado): alvo VIVO\n"
     "  // fica preso na reacao — hit novo reinicia (juggle de combo); kawarimi escapa.\n"
     "  if (target.hp > 0) {\n"
     "    target.hitstun = dmg >= 180 ? 0.60 : 0.35;\n"
     "  }\n",
     'after'),
    ('executeSkill-guard',
     "  if (unit.chakra < sk.cost) return;\n"
     "\n"
     "  unit.chakra -= sk.cost;\n",
     "  if (unit.hitstun > 0 && sk.type !== 'kawarimi') return; // APK: preso na reacao de dano; kawarimi = escape autentico\n"
     "\n",
     'between'),
    ('tick-decay',
     "    if (u.spawnShield > 0) u.spawnShield = Math.max(0, u.spawnShield - dt); // SPAWN GUARD\n",
     "    if (u.hitstun > 0) u.hitstun = Math.max(0, u.hitstun - dt); // APK HITSTUN (dt real — tempo de parede)\n",
     'after'),
    ('telemetry',
     "Object.defineProperty(window, 'rosterMeta', { get: () => rosterMeta });\n",
     "window.__HITSTUN = { normal: 0.35, heavy: 0.60, source: 'APK storm: dmg0f media 21f, hsta0 36f' }; // telemetria E2E (W-HS)\n",
     'before'),
]

SPAWN_ANCHOR = "comboStep: 0, comboResetTimer: 0, awakenedTimer: 0, deadTimer: 0, spawnShield: 3.0,"
SPAWN_NEW = "comboStep: 0, comboResetTimer: 0, awakenedTimer: 0, deadTimer: 0, spawnShield: 3.0, hitstun: 0,"

# --- dry-run: valida TODAS as ancoras antes de gravar qualquer byte ---
if 'APK HITSTUN' in src or '__HITSTUN' in src:
    print('ja aplicado — nada a fazer'); sys.exit(0)

fails = []
for name, anc, ins, pos in ANCHORS:
    n = src.count(anc)
    if n != 1:
        fails.append(f'  ancora "{name}" count={n} (esperado 1)')
ns = src.count(SPAWN_ANCHOR)
if ns < 1:
    fails.append(f'  ancora "spawn" count={ns} (esperado >=1)')
if fails:
    print('DRY-RUN ABORTADO:'); print('\n'.join(fails)); sys.exit(1)
print(f'dry-run OK: 4 ancoras unicas + spawn x{ns} (replace_all)')

# --- aplica ---
out = src
for name, anc, ins, pos in ANCHORS:
    if pos == 'after':
        out = out.replace(anc, anc + ins)
    elif pos == 'between':
        out = out.replace(anc, anc.replace('\n  unit.chakra -= sk.cost;\n', ins + '  unit.chakra -= sk.cost;\n'))
    elif pos == 'before':
        out = out.replace(anc, ins + anc)
out = out.replace(SPAWN_ANCHOR, SPAWN_NEW)
assert out != src and out.count('hitstun') >= src.count('hitstun') + 5

shutil.copyfile(P, P + '.bak_whs')
data = out.replace('\n', eol).encode('utf-8') if eol == '\r\n' else out.encode('utf-8')
io.open(P, 'wb').write(data)
print('W-HS APLICADO: hitstun do APK (0.35s/0.60s, kawarimi livre, juggle por reset)')
