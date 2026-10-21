# -*- coding: utf-8 -*-
"""W1.2.3: flag de readiness NO lugar certo — initLobbyNav() (anexa listeners de
nav) roda na linha ~5521, MUITO depois da funcao de boot (~1504) onde a flag
estava. Move a flag para logo apos a chamada initLobbyNav(); = TODOS os
listeners (nav + ajustes) attached. Rollback: *.bak_w123"""
import io, sys, shutil

def apply(path, patches):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    s = src.replace('\r\n', '\n')
    for name, old, new in patches:
        c = s.count(old)
        if c != 1:
            print(f'ANCHOR FAIL [{name}]: {c} occ'); return False
        s = s.replace(old, new, 1)
        print(f'  [OK] {name}')
    shutil.copyfile(path, path + '.bak_w123')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = apply('public/game.js', [
    ('remove flag prematura (fim da funcao boot)',
     '  initAjustes(); // W1.2: wire da página de Ajustes\n  window.__ajustesReady = true; // W1.2.2: boot COMPLETO — todos os listeners attached (sinal E2E)\n}',
     '  initAjustes(); // W1.2: wire da página de Ajustes\n}'),
    ('flag apos initLobbyNav (o ultimo listener attach do lobby)',
     '  initLobbyNav();',
     '  initLobbyNav();\n  window.__ajustesReady = true; // W1.2.3: TODOS os listeners do lobby attached — sinal E2E determinístico'),
])
print('W1.2.3:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
