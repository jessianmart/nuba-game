# -*- coding: utf-8 -*-
"""BOOT HARDENING (auditoria estatica): P0 roster fetch .catch + init com rastro,
P0 partida zumbi (try/catch no spawn), P1 guard do preview de lobby, P2 arg guards.
Rollback: *.bak_hard. Cache-bust coberto pelo T5 (v31)."""
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
    shutil.copyfile(path, path + '.bak_hard')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = apply('public/game.js', [
    ('P0: roster fetch com .catch (unico sem catch dos 5)',
     "    fetch('assets/data/roster_meta.json?v=8').then(r => r.json()),",
     "    fetch('assets/data/roster_meta.json?v=8').then(r => r.json()).catch(() => ({})), // P0 hardening"),
    ('P0: assignment tolera metaRes vazio',
     '  rosterMeta = metaRes.roster;',
     '  rosterMeta = (metaRes && metaRes.roster) || []; // P0: boot nunca morre por roster falho'),
    ('P0: init() com rastro de falha em vez de morte silenciosa',
     "{ get: () => arenaGroup });\n\ninit();",
     "{ get: () => arenaGroup });\n\ninit().catch(err => { console.error('[NUBA] BOOT FALHOU:', err); }); // P0 hardening"),
    ('P0: spawn protegido — sem partida zumbi',
     "  await Promise.all([\n    spawnTeam(blueRoster, 'blue', blueBase.x, blueBase.z),\n    spawnTeam(redRoster, 'red', redBase.x, redBase.z)\n  ]);",
     "  try {\n    await Promise.all([\n      spawnTeam(blueRoster, 'blue', blueBase.x, blueBase.z),\n      spawnTeam(redRoster, 'red', redBase.x, redBase.z)\n    ]);\n  } catch (err) {\n    console.error('[NUBA] FALHA AO SPAWNAR HEROIS:', err); // P0: sem partida zumbi\n    matchActive = false;\n    showBanner('FALHA AO CARREGAR HEROIS — TENTE NOVAMENTE', 2600);\n    return;\n  }"),
    ('P1: guard do preview de lobby (cold-load)',
     "function updateLobbyTeamsPreview(playerHeroId) {\n  const others = rosterMeta.filter(h => h.id !== playerHeroId);\n  const blueHeroes = [rosterMeta.find(h => h.id === playerHeroId), ...others.slice(0, 4)];",
     "function updateLobbyTeamsPreview(playerHeroId) {\n  if (!Array.isArray(rosterMeta) || !rosterMeta.length) return; // P1 hardening: cold-load\n  const others = rosterMeta.filter(h => h.id !== playerHeroId);\n  const blueHeroes = [rosterMeta.find(h => h.id === playerHeroId) || rosterMeta[0], ...others.slice(0, 4)];"),
    ('P2: arg guard do executeSkill',
     "function executeSkill(unit, slot) {\n  activeSkillVfxModel = ((SKILL_VFX_MAP[unit.heroId] || {})[slot]) || null; // M7: identidade por skill",
     "function executeSkill(unit, slot) {\n  if (!unit || !unit.kit || !unit.heroId) return; // P2 hardening: robustez de API\n  activeSkillVfxModel = ((SKILL_VFX_MAP[unit.heroId] || {})[slot]) || null; // M7: identidade por skill"),
    ('P2: arg guard do dealDamage',
     "function dealDamage(attacker, target, amount, skillName) {\n  if (target.deadTimer > 0) return;",
     "function dealDamage(attacker, target, amount, skillName) {\n  if (!target || !attacker || !Number.isFinite(amount)) return; // P2 hardening: robustez de API\n  if (target.deadTimer > 0) return;"),
])
print('BOOT HARDENING:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
