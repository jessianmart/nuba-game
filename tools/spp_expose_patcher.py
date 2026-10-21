# -*- coding: utf-8 -*-
"""Expoe SKILL_VFX_ANIM + __shadowClones para validacao E2E (padrao M7). Rollback: *.bak_sppexp"""
import io, sys, shutil

path = 'public/game.js'
src = io.open(path, 'r', encoding='utf-8', newline='').read()
eol = '\r\n' if '\r\n' in src else '\n'
s = src.replace('\r\n', '\n')
old = 'window.SKILL_VFX_MAP = SKILL_VFX_MAP; // M7 (inspecao)'
new = old + '\nwindow.SKILL_VFX_ANIM = SKILL_VFX_ANIM; // SPP (inspecao)\nwindow.__shadowClones = () => shadowClones; // SPP (validacao E2E)'
c = s.count(old)
if c != 1:
    print(f'ANCHOR FAIL: {c} occ'); sys.exit(1)
s = s.replace(old, new, 1)
shutil.copyfile(path, path + '.bak_sppexp')
io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
print('[OK] exposes SPP')
sys.exit(0)
