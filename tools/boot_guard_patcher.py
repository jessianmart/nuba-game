# -*- coding: utf-8 -*-
"""SPAWN-GUARD de boot: start5v5Match espera o roster carregar (cold-load race).
Rollback: *.bak_bootguard"""
import io, sys, shutil

def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{path}:{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {name}')
    shutil.copyfile(path, path + '.bak_bootguard')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = True
ok &= apply('public/index.html', [('cache-bust v30', 'game.js?v=29', 'game.js?v=30')])
ok &= apply('public/game.js', [
    ('guard de roster no start5v5Match',
     'async function start5v5Match() {\n  sfx.init();',
     'async function start5v5Match() {\n'
     '  // BOOT-GUARD (cold-load race): window.start5v5Match e exposto antes do fetch do boot\n'
     '  // popular rosterMeta — sem esperar: TypeError reading \'id\' + spawn incompleto (flake P2)\n'
     '  for (let _bg = 0; _bg < 100 && (!Array.isArray(rosterMeta) || rosterMeta.length === 0); _bg++) {\n'
     '    await new Promise(r => setTimeout(r, 100));\n'
     '  }\n'
     '  if (!Array.isArray(rosterMeta) || rosterMeta.length === 0) {\n'
     '    console.warn(\'[NUBA] roster nao carregou — start5v5Match abortado\');\n'
     '    return;\n'
     '  }\n'
     '  sfx.init();'),
])
print('BOOT-GUARD:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
