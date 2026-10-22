"""PV4.2-race v2 — blindar testes contra corridas de estado de meio de partida.
(v1 falhou SILENCIOSAMENTE: anchors do texto ERRADO -> assert matou o script
ANTES do write; a bateria rodou com testes originais. v2: anchors lidos do
arquivo REAL + autoverificacao pos-escrita.)

Falhas explicadas com dados (baterias 1-2, console errors 0):
  - verify ult eval: r_state "dash" congelado + awakened true STALE -> player
    MORTO no momento do cast (deadTimer nao zerado); awakening vinha de cast
    anterior estendido por kills (L4921 Math.max +8s).
  - suite S05: mesma coisa — "Ultimate cooldown was not set" com isAwakened
    true = cast bloqueado (player morto) + awakening stale mascarando.
  - suite S04: vitima com spawnShield/deadTimer do combate anterior OU outro
    inimigo mais perto no melee (findNearestEnemy 7.5u) -> golpe nao mata a
    vitima posicionada.
  - suite S03: q/w bloqueados com e passado — unica guard que diferencia e
    (kawarimi) da resto e o hitstun; re-zero entre casts neutraliza qualquer
    sujeira in-block do combo de atk.

Fix: setup deterministico nos TESTES (assertions intactas, precedent skill
6.10). Toda leitura/cast de skill zera deadTimer/hitstun/awakenedTimer.
Run: python tools/pv4_2_race_fix2.py   (cwd = repo root)
"""
import py_compile
import shutil

SUITE = 'tools/test_e2e_suite.py'
VER = 'tools/verify_browser_runtime.py'
shutil.copy2(SUITE, SUITE + '.bak_pv42race2')
shutil.copy2(VER, VER + '.bak_pv42race2')

MARK = 'PV4.2-race'

def L(*lines):
    """Une linhas com CRLF — o test_e2e_suite.py usa \r\n nessas regioes."""
    return '\r\n'.join(lines)


# ---------- suite: S03 — re-zero entre casts ----------
s = open(SUITE, encoding='utf-8', newline='').read()

a_q = L("                // 2. Primary Jutsu Q",
        "                window.executeSkill(p, 'q');")
n_q = L("                // 2. Primary Jutsu Q",
        "                p.hitstun = 0; p.deadTimer = 0; // PV4.2-race: combo de atk pode sujar o caster (kawarimi e exempt)",
        "                window.executeSkill(p, 'q');")
assert s.count(a_q) == 1, f'S03 q: {s.count(a_q)}'
s = s.replace(a_q, n_q, 1)

a_w = L("                // 3. Secondary Jutsu E (slot w)",
        "                window.executeSkill(p, 'w');")
n_w = L("                // 3. Secondary Jutsu E (slot w)",
        "                p.hitstun = 0; p.deadTimer = 0; // PV4.2-race",
        "                window.executeSkill(p, 'w');")
assert s.count(a_w) == 1, f'S03 w: {s.count(a_w)}'
s = s.replace(a_w, n_w, 1)

a_e = L("                // 4. Kawarimi Space (slot e)",
        "                window.executeSkill(p, 'e');")
n_e = L("                // 4. Kawarimi Space (slot e)",
        "                p.hitstun = 0; p.deadTimer = 0; // PV4.2-race",
        "                window.executeSkill(p, 'e');")
assert s.count(a_e) == 1, f'S03 e: {s.count(a_e)}'
s = s.replace(a_e, n_e, 1)
print('[ok] S03: re-zero hitstun/deadTimer entre casts')

# ---------- suite: S04 — vitima deterministica + sem outro alvo no melee ----------
a_s04 = L("                enemy.x = player.x + 1.5;",
          "                enemy.z = player.z;",
          "                enemy.hp = 5;",
          "                player.cds.atk = 0;")
n_s04 = L("                enemy.x = player.x + 1.5;",
          "                enemy.z = player.z;",
          "                enemy.hp = 5;",
          "                player.cds.atk = 0;",
          "                // PV4.2-race: vitima viva/sem escudo, caster livre, sem outro alvo no melee (7.5u)",
          "                enemy.deadTimer = 0;",
          "                enemy.spawnShield = 0;",
          "                player.deadTimer = 0;",
          "                player.hitstun = 0;",
          "                player.awakenedTimer = 0;",
          "                for (const o of window.units) {",
          "                    if (o !== enemy && o.team !== player.team) { o.x += 30; }",
          "                }")
assert s.count(a_s04) == 1, f'S04: {s.count(a_s04)}'
s = s.replace(a_s04, n_s04, 1)
print('[ok] S04: vitima viva/sem escudo + outros inimigos afastados')

# ---------- suite: S05 — caster vivo, mede ESTE cast ----------
a_s05 = L("                const p = window.units.find(u => u.isPlayer);",
          "                p.hitstun = 0; p.chakra = 100;",
          "                p.cds.r = 0;")
n_s05 = L("                const p = window.units.find(u => u.isPlayer);",
          "                p.hitstun = 0; p.chakra = 100;",
          "                p.cds.r = 0;",
          "                p.deadTimer = 0; p.awakenedTimer = 0; // PV4.2-race: player morto bloqueia cast; awakening stale mascara")
assert s.count(a_s05) == 1, f'S05: {s.count(a_s05)}'
s = s.replace(a_s05, n_s05, 1)
print('[ok] S05: deadTimer/awakenedTimer zerados')

open(SUITE, 'w', encoding='utf-8', newline='').write(s)

# ---------- verify: os 4 evals de skill (q/w/e/r) precisam do caster VIVO ----------
v = open(VER, encoding='utf-8', newline='').read()
nfix = 0
for slot in ['q', 'w', 'e', 'r']:
    a = f'            p.hitstun = 0; p.cds.{slot} = 0; p.chakra = 100;'
    n = f'            p.hitstun = 0; p.cds.{slot} = 0; p.chakra = 100; p.deadTimer = 0; p.awakenedTimer = 0; // {MARK}'
    assert v.count(a) == 1, f'verify {slot}: {v.count(a)}'
    v = v.replace(a, n, 1)
    nfix += 1
open(VER, 'w', encoding='utf-8', newline='').write(v)
print(f'[ok] verify: {nfix} evals de skill com caster vivo/limpo')

# ---------- autoverificacao pos-escrita ----------
s2 = open(SUITE, encoding='utf-8', newline='').read()
v2 = open(VER, encoding='utf-8', newline='').read()
n_s = s2.count(MARK)
n_v = v2.count(MARK)
assert n_s >= 5, f'suite: so {n_s} marcadores'
assert n_v >= 4, f'verify: so {n_v} marcadores'
print(f'[SELF-CHECK] marcadores no disco: suite={n_s} verify={n_v}')

py_compile.compile(SUITE, doraise=True)
py_compile.compile(VER, doraise=True)
print('[ok] py_compile limpo')
print('PV4.2 RACE FIX v2 DONE (verificado no disco)')
