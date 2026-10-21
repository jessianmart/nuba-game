"""PV2-C — blindagem de killTarget null no BR.
BUG CRÍTICO: `scoreBlue >= activeMatchCfg.killTarget` com killTarget = null
coerce null -> 0: `0 >= 0` = true -> endMatch('木ノ葉') dispara no 1o kill do BR
antes do last-standing. Guard: killTarget != null.
Run: python tools/pv2c_killtarget_guard.py   (cwd = repo root)
"""
import shutil
import subprocess

GJ = 'public/game.js'
shutil.copy2(GJ, GJ + '.bak_pv2c')
g = open(GJ, 'r', encoding='utf-8', newline='').read()


def rep(text, old, new, what, n=1):
    k = text.count(old)
    assert k == n, f'{what}: esperava {n}, achei {k}'
    return text.replace(old, new)


OLD_COND = "} else if (scoreBlue >= activeMatchCfg.killTarget || scoreRed >= activeMatchCfg.killTarget) {"
NEW_COND = "} else if (activeMatchCfg.killTarget != null && (scoreBlue >= activeMatchCfg.killTarget || scoreRed >= activeMatchCfg.killTarget)) { // PV2: blindagem vs null (BR decide por last-standing)"
g = rep(g, OLD_COND, NEW_COND, 'win cond DM')

g = rep(g,
        "  if (_goalEl) _goalEl.textContent = `META: ${CFG.killTarget} ABATES`;",
        "  if (_goalEl) _goalEl.textContent = CFG.killTarget != null ? `META: ${CFG.killTarget} ABATES` : 'SOBREVIVA · ÚLTIMO DE PÉ'; // PV2: BR nao tem meta de abates",
        'goal text')

open(GJ, 'w', encoding='utf-8', newline='').write(g)
r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] win-cond blindada vs killTarget null + goal text BR · node --check limpo')
print('PV2C GUARD DONE')
