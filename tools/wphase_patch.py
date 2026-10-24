# -*- coding: utf-8 -*-
"""W-VFX-SEQ: patcheia o game.js com SKILL_VFX_PHASES (emissores reais por fase
do cast) + motor de agendamento no relogio do animTimer (pausa no hitstop)."""
import io

GAME = 'public/game.js'
s = io.open(GAME, encoding='utf-8').read()

PHASES = """// W-VFX-SEQ: emissores REAIS por fase do cast (at = fracao da duracao; o relogio e
// o animTimer, que PAUSA no hitstop como no Storm). s = extent alvo em unidades de mundo;
// fd = offset a frente do caster; dx = offset lateral; y = altura; c = tinta; g = grupo do modelo.
const SKILL_VFX_PHASES = {
  '1nrt': {
    q: [{ m: '1nrveff1_sonic01_air02', at: 0.55, s: 4.5, y: 1.4, fd: 2.6, c: 0x00d4ff }],
    w: [{ m: '1nrveff1_ptc01', at: 0.10, s: 2.6, y: 1.6, c: 0xffffff },
        { m: '1nrveff1_smk01', at: 0.30, s: 3.2, y: 1.2, dx: 1.7, c: 0xe2e8f0 },
        { m: '1nrveff1_smk01', at: 0.30, s: 3.2, y: 1.2, dx: -1.7, c: 0xe2e8f0 }],
    e: [{ m: '1nrveff1_smk02', at: 0.05, s: 3.0, y: 1.2, c: 0xe2e8f0 }],
    r: [{ m: '1nrveff1_chakra03', at: 0.15, s: 5.5, y: 2.2, c: 0xff3b00 },
        { m: '1nrveff1_ring01', at: 0.80, s: 6.0, y: 0.6, c: 0xffedd5 }]
  },
  '1ssk': {
    q: [{ m: '1ssveff1_shock01', at: 0.45, s: 3.2, y: 1.8, fd: 1.6, c: 0x60a5fa }],
    w: [{ m: '1ssveff1_smk01', at: 0.35, s: 2.8, y: 1.6, fd: -1.6, c: 0x94a3b8 }],
    e: [{ m: '1ssveff1_smk02', at: 0.05, s: 3.0, y: 1.2, c: 0xe2e8f0 }],
    r: [{ m: '1ssveff1_smk02', at: 0.55, s: 4.5, y: 1.0, c: 0x93c5fd }]
  },
  '1skr': {
    q: [{ m: '1skneff_leg01', at: 0.40, s: 5.0, y: 1.6, fd: 1.8, c: 0xf43f5e }],
    e: [{ m: 'shatter', at: 0.05, s: 2.6, y: 1.0, c: 0xe2e8f0 }],
    r: [{ g: 'common', m: '1efc_brk01_02', at: 0.60, s: 8.0, y: 0.4, c: 0xff5c8a }]
  },
  '1kks': {
    q: [{ m: 'raikiri_spark', at: 0.50, s: 2.8, y: 1.8, fd: 1.4, c: 0x38bdf8 }],
    w: [{ g: 'common', m: '1efc_wtr03', at: 0.35, s: 3.5, y: 1.2, fd: 3.0, c: 0x0ea5e9 }]
  },
  '1roc': {
    q: [{ m: 'leaf_flurry', at: 0.35, s: 3.5, y: 1.4, c: 0x4ade80 }],
    w: [{ m: 'leaf_flurry', at: 0.50, s: 4.2, y: 1.6, c: 0x4ade80 }]
  },
  '1itc': {
    q: [{ m: 'amaterasu_flame', at: 0.50, s: 3.2, y: 1.4, fd: 2.0, c: 0x450a0a }]
  },
  '1gar': {
    q: [{ m: '1gareff1_snd15', at: 0.40, s: 5.0, y: 1.2, c: 0xd97706 }],
    w: [{ m: '1gareff1_snd03', at: 0.50, s: 4.0, y: 1.0, fd: 2.2, c: 0xd97706 }]
  },
  '1nej': {
    q: [{ m: 'air_palm', at: 0.35, s: 3.0, y: 1.4, fd: 2.0, c: 0x60a5fa }]
  },
  '1jry': {
    q: [{ m: '1jryeff03', at: 0.50, s: 3.2, y: 1.8, fd: 2.4, c: 0x94a3b8 }]
  },
  '1tnd': {
    r: [{ g: 'common', m: '1efc_brk01_02', at: 0.50, s: 7.0, y: 0.4, c: 0xfbbf24 }]
  },
  '1orc': {
    q: [{ m: '1orceff1_02', at: 0.40, s: 3.6, y: 1.4, fd: 2.4, c: 0xa3e635 }],
    w: [{ g: 'common', m: '1efc_slash01', at: 0.50, s: 3.5, y: 1.6, fd: 2.0, c: 0xc7d2fe }]
  }
};
"""

# 1) inserir o mapa antes do bloco HERO_STATS
anchor1 = "// ==================== P2: STATS POR HEROI (identidade de combate) ===================="
assert s.count(anchor1) == 1
s = s.replace(anchor1, PHASES + "\n" + anchor1)

# 2) agendar phases no executeSkill (logo apos unit.cds[slot] = sk.cd)
anchor2 = """  unit.chakra -= sk.cost;
  unit.cds[slot] = sk.cd;"""
assert s.count(anchor2) == 1
s = s.replace(anchor2, anchor2 + """
  const _ph = (SKILL_VFX_PHASES[unit.heroId] || {})[slot];
  if (_ph && _ph.length) unit.pendingVfxPhases = _ph.map(p => Object.assign({}, p, { done: false }));
  else unit.pendingVfxPhases = null;""")

# 3) motor no tick (logo apos o decremento do animTimer)
anchor3 = """    if (u.animTimer > 0) {
      u.animTimer -= simDt; // P1 JUICE: THE hitstop — action animations freeze
    }"""
assert s.count(anchor3) == 1
s = s.replace(anchor3, anchor3 + """

    if (u.pendingVfxPhases && u.pendingVfxPhases.length) {
      if (u.animDuration > 0 && u.animTimer > 0) {
        const frac = 1 - (u.animTimer / u.animDuration);
        for (const p of u.pendingVfxPhases) {
          if (!p.done && frac >= p.at) {
            p.done = true;
            const grp = buildExtractedVfxMeshGroup(p.g || u.heroId, p.c || 0xffffff, (p.s || 3) * 0.004, p.m);
            if (grp) {
              const fx = Math.sin(u.rotY), fz = Math.cos(u.rotY);
              const fd = p.fd || 0, dx = p.dx || 0;
              grp.position.set(u.x + fx * fd + fz * dx, p.y || 1.2, u.z + fz * fd - fx * dx);
              grp.rotation.y = u.rotY;
              grp.userData.rotSpeed = new THREE.Vector3(0, 4, 0);
              arenaGroup.add(grp);
              vfxList.push({ mesh: grp, age: 0, duration: p.dur || 0.7, style: 'compound', directional: true, bindUnit: u });
            }
          }
        }
        if (u.pendingVfxPhases.every(q => q.done)) u.pendingVfxPhases = null;
      } else if (u.animTimer <= 0) {
        u.pendingVfxPhases = null;
      }
    }""")

io.open(GAME, 'w', encoding='utf-8', newline='\n').write(s)
print('W-VFX-SEQ patched: mapa + agendamento + motor')
