# -*- coding: utf-8 -*-
"""W1.2.1: sinal deterministico de boot — window.__ajustesReady so vira true
no fim de initAjustes (prova que listeners estao attached). Rollback: *.bak_w121"""
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
    shutil.copyfile(path, path + '.bak_w121')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = apply('public/game.js', [
    ('flag __ajustesReady no fim de initAjustes',
     "  for (const k of Object.keys(pills)) if (pills[k]) pills[k].addEventListener('click', () => { applyQuality(k); persistPatch({ quality: k }); });\n}",
     "  for (const k of Object.keys(pills)) if (pills[k]) pills[k].addEventListener('click', () => { applyQuality(k); persistPatch({ quality: k }); });\n}\nwindow.__ajustesReady = true; // W1.2.1: sinal determinístico de boot p/ E2E (listeners attached)"),
])
print('W1.2.1:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
