# -*- coding: utf-8 -*-
"""PV1c2: remove a MINHA initTouchControls redundante (L27-88) — a IIFE dos agentes
(L5911+) e' completa e melhor (auto-aim com rotacao + vibrate + chakra hold +
.pressed). Preserva window.__cameraMode (leitura E2E). Rollback: *.bak_pv1c2"""
import io, sys, shutil

def cut_lines(path, start_marker, end_marker, keep_start, name):
    src = io.open(path, 'r', encoding='utf-8', newline='').read()
    eol = '\r\n' if '\r\n' in src else '\n'
    lines = src.replace('\r\n', '\n').split('\n')
    si = next(i for i, l in enumerate(lines) if start_marker in l)
    ei = next(i for i in range(si + 1, len(lines)) if end_marker in lines[i])
    del lines[si + (1 if keep_start else 0):ei]
    shutil.copyfile(path, path + '.bak_pv1c2')
    io.open(path, 'w', encoding='utf-8', newline='').write(eol.join(lines) if eol == '\r\n' else '\n'.join(lines))
    print(f'  [OK] {path}:{name} (linhas {si}..{ei})')
    return True

ok = cut_lines('public/game.js',
    'function initTouchControls() {',
    '// CHARACTER SKILL KITS (Authentic',
    False, 'remover implementacao redundante (IIFE dos agentes prevalece)')
print('PV1c2:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
