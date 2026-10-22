"""PV4.2-race v3 — delta MINIMO sobre o estado commitado (34823bd + d345337).
O agente paralelo endureceu suite/verify (hitstun/deadTimer em ~7 pontos) mas
S05 e o r-eval do verify ficaram expostos ao par confirmado COM DADOS nas
baterias 1-2: player MORTO bloqueia o cast (cds.r fica 0 / r_state congela em
'dash') + awakening STALE (L4921 kill-extension +8s) mascara o isAwakened.
Fix: + deadTimer/awakenedTimer = 0. Anchors de LINHA UNICA (imunes a CRLF).
Run: python tools/pv4_2_race_fix3.py   (cwd = repo root)
"""
import py_compile
import shutil

SUITE = 'tools/test_e2e_suite.py'
VER = 'tools/verify_browser_runtime.py'
shutil.copy2(SUITE, SUITE + '.bak_pv42race3')
shutil.copy2(VER, VER + '.bak_pv42race3')

s = open(SUITE, encoding='utf-8', newline='').read()
a = "p.hitstun = 0; p.chakra = 100;\r\n                p.cds.r = 0;"
n = ("p.hitstun = 0; p.chakra = 100;\r\n                p.cds.r = 0;"
     "\r\n                p.deadTimer = 0; p.awakenedTimer = 0; // PV4.2-race: player morto bloqueia cast; awakening stale mascara")
cnt = s.count(a)
if cnt == 0:
    a = a.replace('\r\n', '\n')
    n = n.replace('\r\n', '\n')
    cnt = s.count(a)
assert cnt == 1, f'S05: {cnt}'
s = s.replace(a, n, 1)
open(SUITE, 'w', encoding='utf-8', newline='').write(s)
print('[ok] S05: deadTimer/awakenedTimer zerados')

v = open(VER, encoding='utf-8', newline='').read()
a2 = "p.hitstun = 0; p.cds.r = 0; p.chakra = 100;"
n2 = "p.hitstun = 0; p.cds.r = 0; p.chakra = 100; p.deadTimer = 0; p.awakenedTimer = 0; // PV4.2-race"
assert v.count(a2) == 1, f'verify r-eval: {v.count(a2)}'
v = v.replace(a2, n2, 1)
open(VER, 'w', encoding='utf-8', newline='').write(v)
print('[ok] verify r-eval: caster vivo/limpo')

# autoverificacao pos-escrita
s2 = open(SUITE, encoding='utf-8', newline='').read()
v2 = open(VER, encoding='utf-8', newline='').read()
assert s2.count('PV4.2-race') >= 1 and v2.count('PV4.2-race') >= 1, 'marcador ausente pos-write'
print(f"[SELF-CHECK] marcadores: suite={s2.count('PV4.2-race')} verify={v2.count('PV4.2-race')}")
py_compile.compile(SUITE, doraise=True)
py_compile.compile(VER, doraise=True)
print('PV4.2 RACE FIX v3 DONE (delta minimo, verificado)')
