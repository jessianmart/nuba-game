"""PV2-B fix — 3 bugs do probe PV2:
1. intro: [roster.slice(1)] (array de array) -> portrait undefined -> 404 /undefined
2. BR nao forçava a arena do config (rodava na arena default do lobby)
3. banner "META: null ABATES" no intro do BR
Run: python tools/pv2b_br_fix.py   (cwd = repo root)
"""
import shutil

GJ = 'public/game.js'
shutil.copy2(GJ, GJ + '.bak_pv2b')
g = open(GJ, 'r', encoding='utf-8', newline='').read()


def rep(text, old, new, what, n=1):
    k = text.count(old)
    assert k == n, f'{what}: esperava {n}, achei {k}'
    return text.replace(old, new)


# F1 — intro: array plano de heroes (nao aninhado)
g = rep(g,
        "  playMatchIntro([playerHero], [roster.slice(1)]); // PV2: intro 1 vs todos — banner custom via activeMatchCfg",
        "  playMatchIntro([playerHero], roster.slice(1)); // PV2: intro 1 vs todos (arrays planos de heroes)",
        'F1 intro array')

# F2 — BR força a arena do config (vila) antes do spawn
g = rep(g,
        "  if (CFG.mode === 'br') { await startBRMatch(CFG, playerHero, others); return; } // PV2: branch total — spawn solo na vila",
        "  if (CFG.mode === 'br') { if (CFG.arena) { await applyArena(CFG.arena); } await startBRMatch(CFG, playerHero, others); return; } // PV2: branch total — forca a arena do config e spawna solo na vila",
        'F2 arena do config')

# F3 — banner de inicio BR (2 ocorrencias: intro normal + fallback sem elementos)
OLD_BANNER = "showBanner(`${activeMatchCfg.label} EM ${ARENA.label.toUpperCase()} INICIADO! META: ${activeMatchCfg.killTarget} ABATES`);"
NEW_BANNER = "showBanner(activeMatchCfg.mode === 'br' ? 'REALEZA NA VILA INICIADO! SOBREVIVA — ÚLTIMO DE PÉ VENCE' : `${activeMatchCfg.label} EM ${ARENA.label.toUpperCase()} INICIADO! META: ${activeMatchCfg.killTarget} ABATES`);"
assert g.count(OLD_BANNER) == 2, f'banner: {g.count(OLD_BANNER)} ocorrencias'
g = g.replace(OLD_BANNER, NEW_BANNER)

open(GJ, 'w', encoding='utf-8', newline='').write(g)
import subprocess  # noqa: E402
r = subprocess.run(['node', '--check', GJ], capture_output=True, text=True)
assert r.returncode == 0, f'node --check FALHOU:\n{r.stdout}\n{r.stderr}'
print('[ok] F1 intro array plano · F2 arena do config · F3 banner BR · node --check limpo')
print('PV2B FIX DONE')
