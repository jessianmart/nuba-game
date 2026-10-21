# -*- coding: utf-8 -*-
"""SPP (Skill Presentation Pass) v1: CLONES DAS SOMBRAS 3D (Kage Bunshin real),
anim procedural por skill (spin/pulse/thrust/rise) e facing (VFX encara o caster).
Aditivo por design: nenhum dano existente muda — suite-safe. Rollback: *.bak_spp"""
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
    shutil.copyfile(path, path + '.bak_spp')
    io.open(path, 'w', encoding='utf-8', newline='').write(s if eol == '\n' else s.replace('\n', '\r\n'))
    return True

ok = apply('public/game.js', [
    ('vars + SKILL_VFX_ANIM (dados SPP)',
     'let activeSkillVfxModel = null; // M7: modelo extraido do cast atual (spawnVFX le daqui)',
     'let activeSkillVfxModel = null; // M7: modelo extraido do cast atual (spawnVFX le daqui)\n'
     'let activeSkillVfxAnim = null; // SPP: anim procedural do cast atual\n'
     'let activeSkillVfxFaceY = null; // SPP: rotY do caster no cast (facing do VFX)\n'
     'let shadowClones = []; // SPP: clones 3D vivos\n'
     '// SPP: anim do VFX extraido por skill — spin=gira (rasengan/chidori/kaiten),\n'
     '// thrust=avanca (projeteis), pulse=pulsa (selos/areia), rise=sobe (fumacas)\n'
     'const SKILL_VFX_ANIM = {\n'
     "  '1nrt': { q: 'spin',  w: 'rise',   e: 'rise',   r: 'spin' },\n"
     "  '1ssk': { q: 'spin',  w: 'thrust', e: 'pulse', r: 'pulse' },\n"
     "  '1skr': { q: 'pulse', w: 'pulse',  e: 'rise',  r: 'pulse' },\n"
     "  '1kks': { q: 'spin',  w: 'thrust', e: 'spin',  r: 'pulse' },\n"
     "  '1roc': { q: 'spin',  w: 'rise',   e: 'thrust', r: 'rise' },\n"
     "  '1itc': { q: 'pulse', w: 'rise',   e: 'rise',  r: 'pulse' },\n"
     "  '1gar': { q: 'pulse', w: 'pulse',  e: 'pulse', r: 'pulse' },\n"
     "  '1hnt': { q: 'spin',  w: 'spin',   e: 'spin',  r: 'spin' },\n"
     "  '1nej': { q: 'spin',  w: 'thrust', e: 'spin',  r: 'spin' },\n"
     "  '1jry': { q: 'thrust', w: 'pulse', e: 'rise',  r: 'spin' }\n"
     '};'),
    ('reset dos clones em nova partida',
     '  vfxList = [];',
     '  vfxList = [];\n'
     '  for (const c of shadowClones) { try { arenaGroup.remove(c.mesh); } catch (e) {} } // SPP\n'
     '  shadowClones = [];'),
    ('executeSkill seta anim + facing',
     '  activeSkillVfxModel = ((SKILL_VFX_MAP[unit.heroId] || {})[slot]) || null; // M7: identidade por skill',
     '  activeSkillVfxModel = ((SKILL_VFX_MAP[unit.heroId] || {})[slot]) || null; // M7: identidade por skill\n'
     '  activeSkillVfxAnim = ((SKILL_VFX_ANIM[unit.heroId] || {})[slot]) || null; // SPP: anim por skill\n'
     '  activeSkillVfxFaceY = unit.rotY; // SPP: VFX encara a direcao do caster'),
    ('spawnVFX aplica facing + anim no extGrp',
     "      vfxList.push({ mesh: extGrp, age: 0, duration: duration * 1.15, style: 'extracted' });",
     "      if (activeSkillVfxFaceY !== null) extGrp.rotation.y = activeSkillVfxFaceY; // SPP: direcao do cast\n"
     "      vfxList.push({ mesh: extGrp, age: 0, duration: duration * 1.15, style: 'extracted', anim: activeSkillVfxAnim, faceDir: activeSkillVfxFaceY !== null ? { x: Math.sin(activeSkillVfxFaceY), z: Math.cos(activeSkillVfxFaceY) } : null }); // SPP"),
    ('engine de anim no update do vfxList',
     '        if (v.bindOffset) v.mesh.position.add(v.bindOffset);\n      }\n    }',
     '        if (v.bindOffset) v.mesh.position.add(v.bindOffset);\n      }\n    }\n'
     '    // SPP: anim procedural por skill (spin/pulse/thrust/rise)\n'
     '    if (v.anim && v.mesh) {\n'
     '      if (!v.mesh.userData.baseScale) v.mesh.userData.baseScale = v.mesh.scale.x || 1;\n'
     '      const bs = v.mesh.userData.baseScale;\n'
     "      if (v.anim === 'spin') { v.mesh.rotation.y += dt * 9.0; }\n"
     "      else if (v.anim === 'pulse') { const p = 1.0 + 0.18 * Math.sin(v.age * 14.0); v.mesh.scale.set(bs * p, bs * p, bs * p); }\n"
     "      else if (v.anim === 'thrust' && v.faceDir) { const mv = 14.0 * Math.max(0, 1.0 - t); v.mesh.position.x += v.faceDir.x * mv * dt; v.mesh.position.z += v.faceDir.z * mv * dt; }\n"
     "      else if (v.anim === 'rise') { v.mesh.position.y += dt * 2.2; }\n"
     '    }'),
    ('CLONES: spawnShadowClones + update (antes do findNearestEnemy)',
     'function findNearestEnemy(unit, maxDist = 45) {',
     '// ==================== SPP: CLONES DAS SOMBRAS 3D (Kage Bunshin) ====================\n'
     'function spawnShadowClones(caster, count, contactDmg) {\n'
     '  for (let i = 0; i < count; i++) {\n'
     '    let mesh = null;\n'
     '    try { mesh = cloneCharacterModel(modelCache.get(caster.heroId), caster.heroId); } catch (e) { mesh = null; }\n'
     '    if (!mesh) break;\n'
     '    const ang = caster.rotY + (i === 0 ? 0 : (i % 2 ? 0.7 : -0.7) * Math.ceil(i / 2));\n'
     '    const cx = caster.x + Math.sin(ang) * 2.2;\n'
     '    const cz = caster.z + Math.cos(ang) * 2.2;\n'
     '    mesh.position.set(cx, 0, cz);\n'
     '    mesh.rotation.y = ang;\n'
     '    mesh.traverse(cn => { if (cn.material) { cn.material = cn.material.clone(); cn.material.transparent = true; cn.material.opacity = 0.85; } });\n'
     '    arenaGroup.add(mesh);\n'
     '    spawnVFX(cx, 1.4, cz, 0xd9d9e3, 2.6, 0.35, \'sphere\', caster.heroId); // poof de invocacao\n'
     '    shadowClones.push({ mesh, x: cx, z: cz, rotY: ang, team: caster.team, heroId: caster.heroId, owner: caster, dmg: contactDmg, ttl: 4.5 });\n'
     '  }\n'
     '}\n'
     'function updateShadowClones(dt) {\n'
     '  for (let i = shadowClones.length - 1; i >= 0; i--) {\n'
     '    const c = shadowClones[i];\n'
     '    c.ttl -= dt;\n'
     '    let target = null, bd = 45;\n'
     '    for (const e of units) { if (e.team !== c.team && e.deadTimer <= 0) { const d = Math.hypot(e.x - c.x, e.z - c.z); if (d < bd) { bd = d; target = e; } } }\n'
     '    if (target) {\n'
     '      const dx = target.x - c.x, dz = target.z - c.z, L = Math.hypot(dx, dz) || 1;\n'
     '      c.rotY = Math.atan2(dx, dz);\n'
     '      const spd = 14 * dt;\n'
     '      c.x += (dx / L) * spd; c.z += (dz / L) * spd;\n'
     '      if (L < 2.4) {\n'
     "        dealDamage(c.owner, target, c.dmg, 'Kage Bunshin no Jutsu');\n"
     '        spawnVFX(c.x, 1.6, c.z, 0xff9900, 2.2, 0.3, \'sphere\', c.heroId);\n'
     '        c.ttl = -1;\n'
     '      }\n'
     '    }\n'
     '    if (c.ttl <= 0) {\n'
     '      spawnVFX(c.x, 1.4, c.z, 0xd9d9e3, 2.6, 0.35, \'sphere\', c.heroId); // poof final\n'
     '      arenaGroup.remove(c.mesh);\n'
     '      shadowClones.splice(i, 1);\n'
     '      continue;\n'
     '    }\n'
     '    c.mesh.position.set(c.x, 0, c.z);\n'
     '    c.mesh.rotation.y = c.rotY;\n'
     "    animateCharacterRig(c.mesh, 'run', performance.now() / 1000, 0, 0.42); // SPP: corrida real\n"
     '  }\n'
     '}\n'
     '\n'
     'function findNearestEnemy(unit, maxDist = 45) {'),
    ('updateMatch roda os clones',
     '  // Update VFX',
     '  updateShadowClones(simDt); // SPP: clones 3D (congelam com o mundo no juice)\n'
     '  // Update VFX'),
    ('Kage Bunshin invoca clones 3D reais (aditivo)',
     "    spawnVFX(tx, 2.2, tz, sk.color, 9.0, 0.55, 'ring', unit.heroId);",
     "    spawnVFX(tx, 2.2, tz, sk.color, 9.0, 0.55, 'ring', unit.heroId);\n"
     "    if (sk.type === 'clone_burst') spawnShadowClones(unit, 3, Math.round(sk.dmg * 0.6)); // SPP: clones 3D de verdade"),
])
print('SPP v1:', 'APLICADO' if ok else 'ABORTADO')
sys.exit(0 if ok else 1)
